"""
Chatbot Orchestrator - Session management and conversation coordination

PRODUCTION ARCHITECTURE:
========================
1. Greetings/Navigation → Rule-based (instant, ~1ms)
2. Data Queries → Analytics Engine with Template SQL (~50-100ms)
3. Complex/Unknown → LangChain Text-to-SQL LLM fallback (~30s)

This gives us 80% of queries in <100ms, 20% fallback to LLM.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from collections import defaultdict

from .providers.base import (
    LLMProvider, ChatMessage, ChatResponse, UserContext, MessageRole
)
from .providers.factory import get_provider, get_provider_health
from .providers.rule_based import RuleBasedProvider
from .config import chatbot_config

# PRODUCTION: Intent Classification + Template SQL (FAST ~50ms)
from .intent_classifier import get_intent_classifier, ClassifiedIntent
from .analytics_engine import get_analytics_engine, UserContext as AnalyticsUserContext

# HYBRID: Embedding-based classification (fallback for pattern matching)
# Uses all-MiniLM-L6-v2 - 22MB model, ~50ms inference
from .embedding_classifier import classify_with_embeddings, hybrid_classify, preload_model as preload_embeddings

# LLM FALLBACK: Text-to-SQL for complex queries (~30s)
from .text_to_sql_langchain import get_sql_agent, LangChainSQLAgent

logger = logging.getLogger(__name__)


@dataclass
class ChatSession:
    """A conversation session with a user."""
    session_id: str
    user_id: str
    user_context: UserContext
    history: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: MessageRole, content: str) -> ChatMessage:
        """Add a message to the session history."""
        message = ChatMessage(role=role, content=content)
        self.history.append(message)
        self.last_activity = datetime.utcnow()
        
        # Trim history if too long
        max_history = chatbot_config.max_history_length
        if len(self.history) > max_history:
            self.history = self.history[-max_history:]
        
        return message
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if the session has expired."""
        return datetime.utcnow() - self.last_activity > timedelta(minutes=timeout_minutes)
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "message_count": len(self.history),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }


class SessionManager:
    """Manages chat sessions for all users."""
    
    def __init__(self, session_timeout_minutes: int = 30):
        self._sessions: Dict[str, ChatSession] = {}
        self._user_sessions: Dict[str, List[str]] = defaultdict(list)
        self._session_timeout = session_timeout_minutes
        self._cleanup_lock = asyncio.Lock()
    
    def create_session(self, user_context: UserContext) -> ChatSession:
        """Create a new chat session for a user."""
        session_id = str(uuid.uuid4())
        session = ChatSession(
            session_id=session_id,
            user_id=user_context.user_id,
            user_context=user_context
        )
        
        self._sessions[session_id] = session
        self._user_sessions[user_context.user_id].append(session_id)
        
        logger.info(f"Created chat session {session_id} for user {user_context.email}")
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID."""
        session = self._sessions.get(session_id)
        if session and session.is_expired(self._session_timeout):
            self._remove_session(session_id)
            return None
        return session
    
    def get_or_create_session(self, session_id: Optional[str], user_context: UserContext) -> ChatSession:
        """Get existing session or create a new one."""
        if session_id:
            session = self.get_session(session_id)
            if session and session.user_id == user_context.user_id:
                # Update user context in case it changed
                session.user_context = user_context
                return session
        
        return self.create_session(user_context)
    
    def get_user_sessions(self, user_id: str) -> List[ChatSession]:
        """Get all active sessions for a user."""
        sessions = []
        for session_id in self._user_sessions.get(user_id, []):
            session = self.get_session(session_id)
            if session:
                sessions.append(session)
        return sessions
    
    def end_session(self, session_id: str) -> bool:
        """End a chat session."""
        return self._remove_session(session_id)
    
    def _remove_session(self, session_id: str) -> bool:
        """Remove a session from storage."""
        session = self._sessions.pop(session_id, None)
        if session:
            user_sessions = self._user_sessions.get(session.user_id, [])
            if session_id in user_sessions:
                user_sessions.remove(session_id)
            logger.info(f"Removed session {session_id}")
            return True
        return False
    
    async def cleanup_expired_sessions(self):
        """Remove all expired sessions."""
        async with self._cleanup_lock:
            expired = [
                sid for sid, session in self._sessions.items()
                if session.is_expired(self._session_timeout)
            ]
            for session_id in expired:
                self._remove_session(session_id)
            if expired:
                logger.info(f"Cleaned up {len(expired)} expired sessions")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics."""
        return {
            "total_sessions": len(self._sessions),
            "unique_users": len(self._user_sessions),
            "session_timeout_minutes": self._session_timeout
        }


class ChatbotOrchestrator:
    """
    Main chatbot orchestrator.
    
    Coordinates between:
    - LLM providers (OpenAI, Ollama, Rule-based)
    - Session management
    - User context and RBAC
    
    Uses a SMART hybrid approach:
    - Rule-based: ONLY for explicit navigation commands & greetings (instant)
    - LLM: Everything else including ambiguous queries (understands intent)
    
    This ensures:
    - "go to files" → Rule-based (instant navigation)
    - "what are files" → LLM (explains, doesn't navigate)
    - "my permissions" → LLM (explains, doesn't navigate)
    """
    
    # EXPLICIT navigation patterns - must have action verb + target
    # These are CERTAIN to be navigation requests
    EXPLICIT_NAVIGATION_PATTERNS = [
        # Direct navigation commands with action verbs
        re.compile(r'\b(go to|take me to|navigate to|open|switch to)\s+(the\s+)?(my\s+)?(files?|dashboard|settings|users?|organizations?|approvals?|analytics?|quarantine|security|logs?|team|infrastructure|database|api.?keys?|api.?gateway|platform.?admin|home)\b', re.IGNORECASE),
        re.compile(r'\b(go|take me|navigate)\s+(to\s+)?(the\s+)?(my\s+)?files?\b', re.IGNORECASE),
        re.compile(r'\b(show|open)\s+(me\s+)?(the\s+)?(my\s+)?(files?|dashboard|settings)\s*(page)?\b', re.IGNORECASE),
    ]
    
    # DATA QUERY patterns - instant data lookups (rule-based handles with real API calls)
    DATA_QUERY_PATTERNS = [
        # File queries
        re.compile(r'\b(recent files?|latest files?|last (uploaded|added)|my recent|new files?)\b', re.IGNORECASE),
        re.compile(r'\b(how many files?|file count|number of files?|total files?)\b', re.IGNORECASE),
        re.compile(r'\b(search|find|look for)\s+(files?|documents?)\b', re.IGNORECASE),
        re.compile(r'\b(storage|space|quota|disk|how much space)\b', re.IGNORECASE),
        re.compile(r'\b(quarantined|infected|virus|threats?)\s*(files?)?\b', re.IGNORECASE),
        re.compile(r'\b(files?\s+by\s+type|file\s+types?|extension\s+breakdown)\b', re.IGNORECASE),
        # Folder queries
        re.compile(r'\b(folder(s)?\s*(stats?|count|info|structure)|how many folders?|my folders?)\b', re.IGNORECASE),
        re.compile(r'\b(folder\s*tree|folder\s*structure|folder\s*hierarchy|directory\s*tree)\b', re.IGNORECASE),
        re.compile(r'\b(folder\s*contents?|what\'?s?\s*in\s*(folder|directory)|inside\s*folder|contents?\s*of)\b', re.IGNORECASE),
        # Organization queries
        re.compile(r'\b(org(anization)?\s*(stats?|info|summary)|how many org|orgs? joined|recent org|new org)\b', re.IGNORECASE),
        re.compile(r'\b(all\s*org(anization)?s?|list\s*(all)?\s*org(anization)?s?)\b', re.IGNORECASE),
        re.compile(r'\b(org\s*quota|organization\s*quota|quota\s*info|storage\s*quota)\b', re.IGNORECASE),
        # User queries
        re.compile(r'\b(user stats?|how many users?|user count|recent users?|new users?|who joined)\b', re.IGNORECASE),
        # Pipeline/ML queries
        re.compile(r'\b(pipeline\s*(stats?|status|info)|ml\s*(stats?|status)|model\s*(stats?|info)|deltas?|training)\b', re.IGNORECASE),
        re.compile(r'\b(pipeline\s*deltas?|data\s*deltas?|pending\s*deltas?)\b', re.IGNORECASE),
        re.compile(r'\b(cost\s*savings?|ml\s*cost|savings?\s*report|optimization\s*cost)\b', re.IGNORECASE),
        re.compile(r'\b(model\s*versions?|version\s*history|ml\s*versions?)\b', re.IGNORECASE),
        re.compile(r'\b(feedback\s*(stats?|status|loop)|training\s*feedback)\b', re.IGNORECASE),
        # Task/Job queries
        re.compile(r'\b(task(s)?\s*(stats?|status)|job(s)?\s*(stats?|status)|background|celery|pending tasks?)\b', re.IGNORECASE),
        # Appointment queries
        re.compile(r'\b(appointment(s)?|meeting(s)?|schedule|upcoming)\b', re.IGNORECASE),
        # System queries
        re.compile(r'\b(system\s*(overview|status|health)|platform\s*(stats?|overview)|full stats?)\b', re.IGNORECASE),
        # Security/virus queries
        re.compile(r'\b(virus\s*(scan|stats?)|security\s*(stats?|status)|scan\s*(stats?|results?))\b', re.IGNORECASE),
        # Activity/summary
        re.compile(r'\b(activity|uploads? (this|today|week)|my (info|summary|stats?|overview))\b', re.IGNORECASE),
        # Session/Keycloak queries
        re.compile(r'\b(user\s*sessions?|active\s*sessions?|login\s*sessions?|session\s*info)\b', re.IGNORECASE),
        re.compile(r'\b(available\s*roles?|list\s*roles?|role\s*list|all\s*roles?)\b', re.IGNORECASE),
        re.compile(r'\b(user\s*roles?|roles?\s*for\s+\S+@\S+)\b', re.IGNORECASE),
        re.compile(r'\b(token\s*info|my\s*token|current\s*session)\b', re.IGNORECASE),
        # ADMIN-ONLY patterns (role check happens in handler)
        re.compile(r'\b(list\s*(all)?\s*users?|all users?|show\s*(all)?\s*users?|user list)\b', re.IGNORECASE),
        re.compile(r'\b(find|lookup|search|get|show)\s+user\s+\S+\b', re.IGNORECASE),
        re.compile(r'\b(find|lookup|search|get|show)\s+org\s+\S+\b', re.IGNORECASE),
        re.compile(r'\b(locked|inactive|disabled|suspended)\s*users?\b', re.IGNORECASE),
        re.compile(r'\b(failed|error|broken)\s*tasks?\b', re.IGNORECASE),
        re.compile(r'\b(audit|audit log|activity log|audit summary|admin summary)\b', re.IGNORECASE),
        # USER ACTIONS (all users)
        re.compile(r'\b(upload|upload file|add file|new file|can i upload|how.*(do i |to )?upload|want to upload|upload.*(via|through|in|here|chat))\b', re.IGNORECASE),
        # API status/health
        re.compile(r'\b(api.*(status|down|active|health)|system.*(status|health|down)|anything down|services?.*(down|active|status))\b', re.IGNORECASE),
        # API status/health
        re.compile(r'\b(api.*(status|down|active|health)|system.*(status|health|down)|anything down|services?.*(down|active|status))\b', re.IGNORECASE),
        re.compile(r'\b(create|new|make)\s+(a\s*)?(folder|directory)\b', re.IGNORECASE),
        re.compile(r'\b(share\s+(file|document)\s+\w+\s+(with|to)\s+\S+@\S+)\b', re.IGNORECASE),
        re.compile(r'\b(download\s*link|get\s*link|generate\s*link)\b', re.IGNORECASE),
        re.compile(r'\b(move\s*folder|rename\s*folder)\b', re.IGNORECASE),
        re.compile(r'\b(create|new|schedule)\s*(appointment|meeting)\b', re.IGNORECASE),
        re.compile(r'\b(submit\s*feedback|send\s*feedback)\b', re.IGNORECASE),
        # ADMIN ACTIONS (role check happens in handler)
        re.compile(r'\b(reset password|password reset)\s+(for\s+)?\S+@\S+\b', re.IGNORECASE),
        re.compile(r'\b(lock|suspend|disable)\s+(user\s+)?\S+@\S+\b', re.IGNORECASE),
        re.compile(r'\b(unlock|unsuspend|enable|activate)\s+(user\s+)?\S+@\S+\b', re.IGNORECASE),
        re.compile(r'\b(create|add|new)\s*user\s+\S+@\S+\b', re.IGNORECASE),
        re.compile(r'\b(delete|remove)\s*user\s+\S+@\S+\b', re.IGNORECASE),
        re.compile(r'\b(assign|set|change)\s*role\b', re.IGNORECASE),
        re.compile(r'\b(create|new)\s*org(anization)?\b', re.IGNORECASE),
        re.compile(r'\b(delete|remove)\s*org(anization)?\b', re.IGNORECASE),
        re.compile(r'\b(update|edit)\s*org(anization)?\b', re.IGNORECASE),
        re.compile(r'\b(trigger|run|start)\s*pipeline\b', re.IGNORECASE),
        re.compile(r'\b(train|retrain)\s*router\b', re.IGNORECASE),
        re.compile(r'\b(rollback)\s*model\b', re.IGNORECASE),
        re.compile(r'\b(force\s*logout|terminate\s*session)\b', re.IGNORECASE),
        re.compile(r'\b(require|enable|enforce)\s*mfa\b', re.IGNORECASE),
        re.compile(r'\b(disable\s*mfa|remove\s*mfa)\b', re.IGNORECASE),
        # API Keys & Audit
        re.compile(r'\b(api\s*keys?|manage\s*api\s*keys?|create\s*api\s*key|revoke\s*api\s*key)\b', re.IGNORECASE),
        re.compile(r'\b(audit\s*logs?|activity\s*logs?|view\s*logs?)\b', re.IGNORECASE),
        # Pipeline Advanced
        re.compile(r'\b(detect\s*changes?|scan\s*changes?)\b', re.IGNORECASE),
        re.compile(r'\b(process\s*delta|run\s*delta)\b', re.IGNORECASE),
        re.compile(r'\b(set\s*strategy|override\s*strategy|use\s*strategy)\b', re.IGNORECASE),
        # Feedback Advanced
        re.compile(r'\b(approve\s*feedback|reject\s*feedback)\b', re.IGNORECASE),
        re.compile(r'\b(export\s*training\s*data|export\s*feedback)\b', re.IGNORECASE),
        # Model Advanced
        re.compile(r'\b(compare\s*versions?|version\s*diff|model\s*diff)\b', re.IGNORECASE),
        re.compile(r'\b(export\s*model|download\s*model)\b', re.IGNORECASE),
        re.compile(r'\b(model\s*metrics|metrics\s*history)\b', re.IGNORECASE),
        # Keycloak Advanced
        re.compile(r'\b(user\s*attributes?)\b', re.IGNORECASE),
        # MCP
        re.compile(r'\b(mcp\s*status|mcp\s*tools?|mcp\s*resources?|call\s*mcp)\b', re.IGNORECASE),
    ]
    
    # Complex data queries that need TEXT-TO-SQL (LLM generates SQL dynamically)
    # These are questions that require joining tables, aggregation, or complex filters
    TEXT_TO_SQL_PATTERNS = [
        # "Who" questions about users/uploaders
        re.compile(r'\bwho\s+(uploaded|created|owns?|has|made)\b', re.IGNORECASE),
        re.compile(r'\bwho(\'?s|\s+is)\s+(the\s+)?(top|most|biggest|largest)\b', re.IGNORECASE),
        # "Which" questions
        re.compile(r'\bwhich\s+(user|org|file|folder)s?\s+(have|has|is|are|uploaded|created)\b', re.IGNORECASE),
        # Rankings/Top N
        re.compile(r'\b(top|bottom)\s+\d+\s+(user|org|file|uploader)s?\b', re.IGNORECASE),
        re.compile(r'\b(most|least)\s+(active|files?|uploads?|storage)\b', re.IGNORECASE),
        # Time-based complex queries
        re.compile(r'\b(last|past|previous)\s+(\d+\s+)?(week|month|day|year)s?\b', re.IGNORECASE),
        re.compile(r'\b(this|current)\s+(week|month|day|year)\b', re.IGNORECASE),
        re.compile(r'\b(since|after|before|between)\s+\d', re.IGNORECASE),
        # Aggregations
        re.compile(r'\b(average|avg|total|sum|count|max|min)\s+(file\s*)?size\b', re.IGNORECASE),
        re.compile(r'\b(breakdown|distribution|group)\s+by\b', re.IGNORECASE),
        # Cross-table queries
        re.compile(r'\bfiles?\s+(per|by|for each)\s+(user|org)\b', re.IGNORECASE),
        re.compile(r'\busers?\s+(in|from|of)\s+org\b', re.IGNORECASE),
        # Specific attribute queries
        re.compile(r'\b(email|name|role|status)s?\s+(of|for)\s+(user|org|file)s?\b', re.IGNORECASE),
        re.compile(r'\blist\s+(out|all)?\s*the\b.*\b(name|email|user|admin|org)\b', re.IGNORECASE),
        # Complex/vague questions that need SQL
        re.compile(r'\b(how\s+much\s+storage|storage\s+used)\s+by\b', re.IGNORECASE),
        re.compile(r'\bcompare\s+(user|org)s?\b', re.IGNORECASE),
        re.compile(r'\btrends?\s+(in|of|for)\b', re.IGNORECASE),
    ]
    
    # Simple greetings - no need to call LLM for these
    # Comprehensive list of real-world greeting patterns for instant response
    GREETING_PATTERNS = [
        # Basic greetings with optional suffixes
        re.compile(r'^(hi|hello|hey|hiya|heya|hola|howdy|yo)[\s\!\.\']*((there|bot|assistant|buddy|friend|all|everyone)?[\s\!\.\']*)*$', re.IGNORECASE),
        # Extended greetings
        re.compile(r'^(greetings|salutations|sup|wassup|whats\s*up|what\'?s\s*up)[\s\!\.\']*$', re.IGNORECASE),
        # Time-based greetings
        re.compile(r'^good\s*(morning|afternoon|evening|day|night)[\s\!\.\']*$', re.IGNORECASE),
        # Thanks/gratitude
        re.compile(r'^(thanks|thank\s*you|thx|ty|cheers|much\s*appreciated|appreciate\s*it|ta)[\s\!\.\']*(so\s*much|very\s*much|a\s*lot|a\s*bunch|a\s*ton)?[\s\!\.\',]*$', re.IGNORECASE),
        re.compile(r'^thank\s*you\s*(so\s*much|very\s*much|a\s*lot|a\s*bunch)[\s\!\.\',]*$', re.IGNORECASE),
        # Farewells
        re.compile(r'^(bye|goodbye|see\s*you|see\s*ya|later|cya|ciao|adios|farewell|peace|peace\s*out)[\s\!\.\']*$', re.IGNORECASE),
        re.compile(r'^(exit|quit|close|end\s*chat|stop|leave)[\s\!\.\']*$', re.IGNORECASE),
        re.compile(r'^(bye\s*bye|good\s*bye|take\s*care|have\s*a\s*(good|nice|great)\s*(day|one))[\s\!\.\']*$', re.IGNORECASE),
        # Acknowledgments
        re.compile(r'^(ok|okay|k|kk|got\s*it|understood|alright|right|sure|cool|nice|great|awesome|perfect)[\s\!\.\']*$', re.IGNORECASE),
        re.compile(r'^(sounds\s*good|works\s*for\s*me|that\s*works|no\s*problem|no\s*worries|np|nw)[\s\!\.\']*$', re.IGNORECASE),
        # Casual check-ins
        re.compile(r'^(how\s*are\s*you|how\'?s\s*it\s*going|how\s*you\s*doing|what\'?s\s*good)[\s\!\?\.\']*$', re.IGNORECASE),
        re.compile(r'^(you\s*there|anyone\s*there|hello\?|hi\?|you\s*around)[\s\!\?\.\']*$', re.IGNORECASE),
        # Start conversation
        re.compile(r'^(start|begin|let\'?s\s*go|let\'?s\s*start|ready)[\s\!\.\']*$', re.IGNORECASE),
    ]
    
    # Patterns that indicate user wants INFORMATION (should go to LLM)
    # These override navigation even if page keywords are present
    INFORMATION_PATTERNS = [
        re.compile(r'\b(what\s+(is|are|does)|explain|tell me about|how\s+(does|do|to)|describe|why)\b', re.IGNORECASE),
        re.compile(r'\b(can\s+i|can\s+you|could\s+you|would\s+you)\b', re.IGNORECASE),
        re.compile(r'\?$'),  # Questions should go to LLM
    ]
    
    # PRODUCTION: Analytics patterns that use fast Template SQL (~50ms)
    # These questions can be answered with pre-built SQL templates
    ANALYTICS_PATTERNS = [
        # User counts and lists
        re.compile(r'\bhow many (users?|members?|people|accounts?)\b', re.IGNORECASE),
        re.compile(r'\b(users?|members?).*(count|number|total)\b', re.IGNORECASE),
        re.compile(r'\busers? (by|per|group) (role|status|type)\b', re.IGNORECASE),
        re.compile(r'\b(top|most|best) uploader', re.IGNORECASE),
        re.compile(r'\b(recent|new|latest) users?\b', re.IGNORECASE),
        
        # File counts and stats
        re.compile(r'\bhow many files?\b', re.IGNORECASE),
        re.compile(r'\b(files?|documents?).*(count|number|total)\b', re.IGNORECASE),
        re.compile(r'\bfiles? (by|per) (type|user|day)\b', re.IGNORECASE),
        re.compile(r'\b(largest|biggest|heaviest) files?\b', re.IGNORECASE),
        re.compile(r'\b(recent|new|latest) (uploads?|files?)\b', re.IGNORECASE),
        re.compile(r'\brecent uploads?\b', re.IGNORECASE),
        
        # Storage
        re.compile(r'\b(total|how much).*storage\b', re.IGNORECASE),
        re.compile(r'\bstorage.*(used|usage|by)\b', re.IGNORECASE),
        re.compile(r'\bhow much (space|disk|storage)\b', re.IGNORECASE),
        
        # Organizations
        re.compile(r'\bhow many (org|organization|compan|tenant)', re.IGNORECASE),
        re.compile(r'\b(org|organization)s?.*(count|list|storage)\b', re.IGNORECASE),
        re.compile(r'\b(most|top) active org', re.IGNORECASE),
        
        # Folders
        re.compile(r'\bhow many folders?\b', re.IGNORECASE),
        re.compile(r'\bfolders?.*(count|list)\b', re.IGNORECASE),
        
        # Security
        re.compile(r'\bvirus (scan|status)\b', re.IGNORECASE),
        re.compile(r'\bquarantin', re.IGNORECASE),
        
        # Trends
        re.compile(r'\buploads? (by|per|trend|daily)\b', re.IGNORECASE),
        re.compile(r'\b(daily|weekly) (uploads?|signups?)\b', re.IGNORECASE),
        
        # My data
        re.compile(r'\bmy (files?|storage|uploads?)\b', re.IGNORECASE),
        
        # Additional patterns for better coverage
        re.compile(r'\b(recent|latest|new) (uploads?|files?)\b', re.IGNORECASE),
        re.compile(r'\b(largest|biggest|heaviest) files?\b', re.IGNORECASE),
        re.compile(r'\b(top|best|most) uploader', re.IGNORECASE),
        re.compile(r'\bwho upload', re.IGNORECASE),
        re.compile(r'\bstorage (by|per) (user|org)', re.IGNORECASE),
        
        # Exact matches for short queries
        re.compile(r'^recent uploads?$', re.IGNORECASE),
        re.compile(r'^latest uploads?$', re.IGNORECASE),
        re.compile(r'^largest files?$', re.IGNORECASE),
        re.compile(r'^biggest files?$', re.IGNORECASE),
        re.compile(r'^my files?$', re.IGNORECASE),
        re.compile(r'^top uploaders?$', re.IGNORECASE),
    ]
    
    def __init__(self):
        self.session_manager = SessionManager()
        self._provider: Optional[LLMProvider] = None
        self._rule_based: Optional[RuleBasedProvider] = None
        self._intent_classifier = None
    
    @property
    def provider(self) -> LLMProvider:
        """Get the configured LLM provider."""
        if self._provider is None:
            self._provider = get_provider()
        return self._provider
    
    @property
    def rule_based(self) -> RuleBasedProvider:
        """Get the rule-based provider for navigation."""
        if self._rule_based is None:
            self._rule_based = RuleBasedProvider()
        return self._rule_based
    
    @property
    def intent_classifier(self):
        """Get the intent classifier for analytics queries."""
        if self._intent_classifier is None:
            self._intent_classifier = get_intent_classifier()
        return self._intent_classifier
    
    @property
    def is_enabled(self) -> bool:
        """Check if chatbot is enabled."""
        return chatbot_config.enabled
    
    def _is_dangerous_command(self, message: str) -> tuple[bool, str]:
        """
        Detect dangerous/destructive commands that should be blocked.
        
        Returns:
            (is_dangerous, response_message)
        """
        message_lower = message.strip().lower()
        
        # Destructive commands - BLOCK these
        dangerous_patterns = [
            (r'\b(delete|remove|erase|destroy|wipe)\s+(all|every|my)?\s*(files?|documents?|data|users?|accounts?|folders?|everything)', 
             "I'm sorry, but I cannot help with deleting or removing data. For file management actions, please use the appropriate interface in FileVault. I'm here to help you find information and answer questions about your data."),
            (r'\b(drop|truncate|alter|modify)\s+(table|database|schema)',
             "I cannot perform database operations. I'm an analytics assistant here to help you query and understand your data."),
            (r'\bformat\s+(disk|drive|storage)',
             "I cannot perform destructive operations. Please use the appropriate system tools for storage management."),
            (r'\b(hack|exploit|inject|bypass|crack)\b',
             "I cannot assist with security exploits or unauthorized access. If you have security concerns, please contact your administrator."),
        ]
        
        for pattern, response in dangerous_patterns:
            if re.search(pattern, message_lower):
                logger.warning(f"Blocked dangerous command: {message[:50]}...")
                return True, response
        
        return False, ""
    
    def _is_complex_query(self, message: str) -> bool:
        """
        Detect complex multi-condition queries that need LLM-generated SQL.
        
        Complex queries have:
        - Multiple conditions (AND/BUT/OR/WHERE)
        - Comparisons (more than, less than, greater, after, before)
        - Multi-entity requirements (users AND files together)
        - Aggregations with conditions (HAVING-like)
        - Time range filters
        - Ranking/sorting requests (top N, sorted by, ranked by)
        
        These should go to text_to_sql_llm, not simple templates.
        """
        message = message.strip().lower()
        
        # Count complexity indicators
        complexity_score = 0
        
        # Multiple conditions (AND/BUT/OR connectors)
        condition_words = [' and ', ' but ', ' or ', ' where ', ' with ', ' that ', ' which have ', ' who have ']
        for word in condition_words:
            if word in message:
                complexity_score += 2
        
        # Comparison operators
        comparisons = [
            'more than', 'less than', 'greater than', 'fewer than',
            'at least', 'at most', 'minimum', 'maximum',
            'over ', 'under ', 'above ', 'below ',
            'between', 'from ', 'after ', 'before ', 'since ',
            '> ', '< ', '>= ', '<= ',
            'larger than', 'smaller than', 'bigger than',  # size comparisons
        ]
        
        # Size threshold patterns - these need WHERE clauses with size comparison
        size_patterns = [
            r'(larger|bigger|greater|more) than \d+\s*(kb|mb|gb|bytes?)',
            r'(smaller|less) than \d+\s*(kb|mb|gb|bytes?)',
            r'(over|under|above|below) \d+\s*(kb|mb|gb|bytes?)',
        ]
        for pattern in size_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                complexity_score += 4  # Size filters need LLM
                break
        
        for comp in comparisons:
            if comp in message:
                complexity_score += 2
        
        # Ranking/sorting queries - these need GROUP BY + ORDER BY
        ranking_patterns = [
            r'top \d+', r'bottom \d+',  # top 5, bottom 10
            r'top (users|user|files|uploaders|organizations)',  # top users, top files
            r'sorted by', r'sort by', r'order by', r'ranked by', r'rank by',
            r'most (storage|files|uploads|documents|space)',  # most storage, most files
            r'least (storage|files|uploads|documents|space)',
            r'highest (storage|size|count)',
            r'lowest (storage|size|count)',
            r'who (has|have) the most', r'who (has|have) the least',
            r'which (user|users|organization|folder).*most',
            r'which (user|users|organization|folder).*least',
            r'largest (file|storage)', r'smallest (file|storage)',
            r'per user', r'per organization', r'by user', r'by organization',
            r'breakdown', r'distribution',
            r'by (file count|upload count|storage)',  # top users by file count
        ]
        
        # Specific entity filter patterns - these need WHERE clauses
        entity_filter_patterns = [
            r'(files?|documents?)\s+(uploaded|by|from|of)\s+[A-Z]',  # files uploaded by Super Admin
            r'(uploaded|created|added)\s+by\s+\w+',  # uploaded by user20
            r'(belongs?|owned?)\s+(to|by)\s+\w+',  # belongs to organization
            r'for\s+(user|organization|org)\s+\w+',  # for user X
            r'\bfrom\s+(user|organization|org)\s+\w+',  # from org X
        ]
        
        # Aggregation patterns - AVG, MIN, SUM, etc.
        aggregation_patterns = [
            r'\b(average|avg|mean)\s+(file|size|storage)',  # average file size
            r'\b(smallest|minimum|min)\s+(file|size)',  # smallest file
            r'\b(sum|total)\s+of\s+',  # sum of sizes
            r'\bmedian\b',  # median
        ]
        for pattern in ranking_patterns:
            if re.search(pattern, message):
                complexity_score += 4  # High score - these MUST go to LLM
                break  # Only count once
        
        # Check entity filter patterns (files by user X)
        for pattern in entity_filter_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                complexity_score += 4  # Specific entity filters need LLM
                break
        
        # Check aggregation patterns (average, min, etc.)
        for pattern in aggregation_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                complexity_score += 4  # Aggregations need LLM
                break
        
        # Multi-entity requirements (mentions multiple tables)
        entity_count = 0
        user_entities = ['user', 'member', 'account', 'people', 'person', 'who ']
        file_entities = ['file', 'document', 'upload', 'item']
        org_entities = ['organization', 'org', 'company', 'tenant']
        folder_entities = ['folder', 'directory']
        
        for e in user_entities:
            if e in message:
                entity_count += 1
                break
        for e in file_entities:
            if e in message:
                entity_count += 1
                break
        for e in org_entities:
            if e in message:
                entity_count += 1
                break
        for e in folder_entities:
            if e in message:
                entity_count += 1
                break
        
        if entity_count >= 2:
            complexity_score += 3  # Multi-table query
        
        # Aggregation with filtering
        aggregations = ['average', 'avg', 'sum', 'total', 'count', 'percentage', 'percent', '%']
        has_aggregation = any(agg in message for agg in aggregations)
        has_filter = any(comp in message for comp in comparisons)
        if has_aggregation and has_filter:
            complexity_score += 2
        
        # Time-based filtering with specific dates
        date_patterns = [
            r'\d{4}',  # Year like 2025
            r'january|february|march|april|may|june|july|august|september|october|november|december',
            r'last \d+ (day|week|month|year)',
            r'past \d+ (day|week|month|year)',
            r'joined after', r'created after', r'uploaded after',
            r'joined before', r'created before', r'uploaded before',
        ]
        for pattern in date_patterns:
            if re.search(pattern, message):
                complexity_score += 1
        
        # Query length (longer queries tend to be more complex)
        word_count = len(message.split())
        if word_count > 15:
            complexity_score += 1
        if word_count > 25:
            complexity_score += 2
        
        # Threshold: 4+ complexity score = too complex for templates
        is_complex = complexity_score >= 4
        
        if is_complex:
            logger.debug(f"Complex query detected (score={complexity_score}): {message[:50]}...")
        
        return is_complex
    
    def _should_use_analytics(self, message: str) -> bool:
        """
        Check if the message should TRY the Analytics Engine.
        
        We're now more liberal here because we have hybrid classification:
        - Pattern matching handles exact queries (~0.1ms)
        - Embedding fallback handles synonyms (~50ms)
        
        If neither is confident, we'll fall through to other handlers.
        """
        message = message.strip().lower()
        
        # First check: Explicit analytics patterns (high confidence)
        for pattern in self.ANALYTICS_PATTERNS:
            if pattern.search(message):
                return True
        
        # Second check: Data-related keywords that MIGHT be analytics
        # Let the hybrid classifier (pattern + embedding) decide
        # EXPANDED for v3.0 - more casual/slang terms
        data_keywords = [
            # Counting/quantifying
            'count', 'how many', 'total', 'number of', 'list', 'amount',
            'show', 'display', 'get', 'what', 'who', 'which', 'gimme', 'give me',
            # User synonyms - EXPANDED
            'user', 'member', 'account', 'people', 'person', 'ppl',
            'folks', 'guys', 'peeps', 'team', 'staff', 'employee', 'headcount',
            # File/storage synonyms
            'file', 'document', 'doc', 'upload', 'storage', 'space', 'disk',
            'folder', 'directory', 'item', 'items', 'record', 'records', 'data',
            # Time-based
            'recent', 'latest', 'new', 'old', 'today', 'week', 'month', 'fresh',
            # Size-based
            'largest', 'biggest', 'smallest', 'heavy', 'huge', 'big', 'large',
            # Ranking
            'top', 'most', 'least', 'active', 'busy', 'leader', 'ranking',
            # Organization
            'organization', 'org', 'company', 'tenant', 'platform', 'system',
            # Security
            'virus', 'scan', 'quarantine', 'security', 'infected',
            # Stats
            'stat', 'analytics', 'report', 'summary', 'overview', 'breakdown',
            # Personal queries
            'my file', 'my upload', 'my storage', 'my doc', 'i upload', 'i have'
        ]
        
        for keyword in data_keywords:
            if keyword in message:
                return True
        
        return False
    
    def _should_use_text_to_sql(self, message: str) -> bool:
        """
        Check if the message should use Text-to-SQL for dynamic query generation.
        
        Text-to-SQL handles complex, vague, or cross-table data questions that
        can't be easily mapped to a single API endpoint.
        """
        message = message.strip()
        
        for pattern in self.TEXT_TO_SQL_PATTERNS:
            if pattern.search(message):
                return True
        return False
    
    def _should_use_rule_based(self, message: str) -> bool:
        """
        Smart hybrid routing:
        1. If it looks like a question/info request → LLM
        2. If it's an explicit navigation command → Rule-based
        3. If it's a greeting → Rule-based
        4. Everything else → LLM (let it understand intent)
        """
        message = message.strip()
        
        # First check: Is this a DATA QUERY or ACTION?
        # These should use rule-based (with real APIs)
        # Check this BEFORE information patterns to catch "can i upload" etc.
        for pattern in self.DATA_QUERY_PATTERNS:
            if pattern.search(message):
                return True  # Use rule-based (with real data)
        
        # Second check: Is this an information/question request?
        # If yes, use LLM for understanding
        for pattern in self.INFORMATION_PATTERNS:
            if pattern.search(message):
                return False  # Use LLM
        
        
        # Third check: Is this an explicit navigation command?
        for pattern in self.EXPLICIT_NAVIGATION_PATTERNS:
            if pattern.search(message):
                return True  # Use rule-based
        
        # Fourth check: Is this a simple greeting?
        for pattern in self.GREETING_PATTERNS:
            if pattern.search(message):
                return True  # Use rule-based
        
        # Default: Use LLM for everything else
        # LLM is better at understanding ambiguous intent
        return False
    
    async def chat(
        self,
        message: str,
        user_context: UserContext,
        session_id: Optional[str] = None,
        db: Any = None
    ) -> Dict[str, Any]:
        """
        Process a chat message.
        
        PRODUCTION ARCHITECTURE (Priority order):
        ==========================================
        1. GREETINGS → Rule-based (~1ms) - instant responses
        2. NAVIGATION → Rule-based (~1ms) - page navigation  
        3. ANALYTICS → Template SQL (~50-100ms) - 80% of data queries
        4. COMPLEX → LangChain Text-to-SQL (~30s) - 20% fallback
        5. OTHER → LLM general chat
        
        Args:
            message: User's message
            user_context: User's context with role and permissions
            session_id: Optional existing session ID
            db: Database session for analytics queries
            
        Returns:
            Dict with response, session_id, and metadata
        """
        if not self.is_enabled:
            return {
                "error": "Chatbot is disabled",
                "code": "CHATBOT_DISABLED"
            }
        
        start_time = time.time()
        
        # =====================================================================
        # PRIORITY -1: SAFETY CHECK - Block dangerous commands
        # =====================================================================
        is_dangerous, danger_response = self._is_dangerous_command(message)
        if is_dangerous:
            return {
                "session_id": session_id or "blocked",
                "response": {
                    "message": danger_response,
                    "confidence": 1.0,
                    "source": "safety_filter"
                },
                "message_count": 0,
                "routing": {
                    "method": "safety_blocked",
                    "elapsed_ms": int((time.time() - start_time) * 1000)
                }
            }
        
        # Get or create session
        session = self.session_manager.get_or_create_session(session_id, user_context)
        
        # Add user message to history
        session.add_message(MessageRole.USER, message)
        
        response = None
        routing_method = None
        
        # =====================================================================
        # PRODUCTION ROUTING (Priority order for speed)
        # =====================================================================
        
        # PRIORITY 0: COMPLEX QUERY DETECTION
        # If query is too complex (multi-condition, comparisons, multi-table),
        # skip templates and go directly to Text-to-SQL LLM
        is_complex = self._is_complex_query(message)
        
        # PRIORITY 1: ANALYTICS - Fast Template SQL (~50-100ms)
        # Check this FIRST because it's the most common and fastest
        # But SKIP if query is complex (needs LLM-generated SQL)
        if not is_complex and db and self._should_use_analytics(message):
            routing_method = "analytics_template_sql"
            logger.info(f"[FAST] Using Analytics Engine for: {message[:50]}...")
            try:
                response = await self._handle_analytics(message, user_context, db)
                if response:
                    elapsed = int((time.time() - start_time) * 1000)
                    logger.info(f"[FAST] Analytics responded in {elapsed}ms")
            except Exception as e:
                logger.warning(f"Analytics failed, will try fallback: {e}")
                response = None  # Fall through to next handler
        
        # PRIORITY 2: RULE-BASED - Navigation & Greetings (~1ms)
        if response is None and not is_complex and self._should_use_rule_based(message):
            routing_method = "rule_based"
            logger.debug(f"Using rule-based provider for: {message[:50]}...")
            response = await self.rule_based.chat(
                message=message,
                history=session.history[:-1],
                user_context=user_context,
                system_prompt=chatbot_config.system_prompt
            )
        
        # PRIORITY 3: TEXT-TO-SQL - Complex queries needing LLM (~30s)
        # Use for complex queries OR queries that REALLY need dynamic SQL generation
        if response is None and (is_complex or self._should_use_text_to_sql(message)):
            routing_method = "text_to_sql_llm"
            logger.info(f"[SLOW] Using Text-to-SQL LLM for complex query: {message[:50]}...")
            try:
                response = await self._handle_text_to_sql(message, user_context)
                elapsed = int((time.time() - start_time) * 1000)
                logger.info(f"[SLOW] Text-to-SQL responded in {elapsed}ms")
            except Exception as e:
                logger.error(f"Text-to-SQL failed: {e}")
                response = None  # Fall through to LLM chat
        
        # PRIORITY 4: LLM CHAT - General conversation
        if response is None:
            routing_method = "llm_chat"
            logger.debug(f"Using LLM provider for: {message[:50]}...")
            response = await self.provider.chat(
                message=message,
                history=session.history[:-1],
                user_context=user_context,
                system_prompt=chatbot_config.system_prompt
            )
        
        # Add assistant response to history
        session.add_message(MessageRole.ASSISTANT, response.message)
        
        elapsed_total = int((time.time() - start_time) * 1000)
        
        return {
            "session_id": session.session_id,
            "response": response.to_dict(),
            "message_count": len(session.history),
            "routing": {
                "method": routing_method,
                "elapsed_ms": elapsed_total
            }
        }
    
    async def _handle_analytics(
        self,
        message: str,
        user_context: UserContext,
        db: Any
    ) -> Optional[ChatResponse]:
        """
        Handle data queries using HYBRID approach:
        
        1. Pattern matching (~0.1ms) - for exact/common queries
        2. Embedding similarity (~50ms) - for varied natural language
        
        This gives us 95%+ accuracy with average <20ms response time.
        """
        try:
            classification_method = "pattern"
            
            # Step 1: Try pattern matching first (FAST ~0.1ms)
            intent = self.intent_classifier.classify(message)
            
            # Step 2: If no pattern match, try embedding similarity (~50ms)
            if not intent or intent.confidence < 0.7:
                logger.debug(f"Pattern match failed/low confidence, trying embeddings for: {message[:50]}")
                
                try:
                    from .embedding_classifier import classify_with_embeddings, EmbeddingMatch
                    embedding_result = classify_with_embeddings(message, threshold=0.55)
                    
                    if embedding_result and embedding_result.confidence >= 0.55:
                        classification_method = "embedding"
                        logger.info(f"[HYBRID] Embedding match: {embedding_result.tool_name} ({embedding_result.confidence:.2f}) in {embedding_result.inference_time_ms:.0f}ms")
                        
                        # Create a ClassifiedIntent from embedding result
                        from .intent_classifier import ClassifiedIntent, QueryCategory, Entity
                        intent = ClassifiedIntent(
                            tool_name=embedding_result.tool_name,
                            confidence=embedding_result.confidence,
                            category=QueryCategory.UNKNOWN,
                            entity=Entity.UNKNOWN,
                            params={},
                            original_query=message
                        )
                except ImportError as e:
                    logger.warning(f"Embedding classifier not available: {e}")
                except Exception as e:
                    logger.warning(f"Embedding classification failed: {e}")
            
            if not intent:
                # No match from pattern OR embeddings - let another handler try
                logger.debug(f"No analytics match (pattern + embedding) for: {message[:50]}")
                return None
            
            if intent.confidence < 0.5:
                # Still too low confidence - let LLM handle it
                logger.debug(f"Low confidence ({intent.confidence}) even after embedding for: {message[:50]}")
                return None
            
            # Build user context for analytics engine
            analytics_user = AnalyticsUserContext(
                user_id=user_context.user_id,
                org_id=getattr(user_context, 'organization_id', None) or '',
                role=user_context.role
            )
            
            # Get analytics engine and execute
            from .analytics_engine import get_analytics_engine
            engine = get_analytics_engine(db)
            result = engine.execute(intent, analytics_user)
            
            if result.success:
                return ChatResponse(
                    message=result.message,
                    metadata={
                        "source": "analytics_hybrid",
                        "classification": classification_method,
                        "tool": result.tool_name,
                        "row_count": result.row_count,
                        "query_time_ms": result.query_time_ms,
                        "confidence": intent.confidence
                    }
                )
            else:
                logger.warning(f"Analytics query failed: {result.message}")
                return None
                
        except Exception as e:
            logger.error(f"Analytics error: {e}", exc_info=True)
            return None
    
    async def _handle_text_to_sql(self, message: str, user_context: UserContext) -> ChatResponse:
        """
        Handle complex data queries using LangChain Text-to-SQL Agent.
        
        This is the FALLBACK path (~30s) - only used when Template SQL
        can't handle the query.
        
        The LLM generates a SQL query based on the natural language question,
        then we execute it safely and format the results.
        """
        try:
            # Get the SQL Agent (singleton)
            sql_agent = get_sql_agent()
            
            # Prepare user context for access control
            user_info = {
                "user_id": user_context.user_id,
                "organization_id": getattr(user_context, 'organization_id', None),
                "role": user_context.role,
                "permissions": user_context.permissions
            }
            
            # Ask the question - this generates SQL, executes, and formats response
            result = await sql_agent.ask(
                question=message,
                user_info=user_info
            )
            
            if result.get("success"):
                response_text = result["answer"]
                
                # Add some metadata if available
                if result.get("row_count") is not None:
                    if result["row_count"] == 0:
                        response_text += "\n\n📊 *No matching records found.*"
                    elif result.get("was_truncated"):
                        response_text += f"\n\n📊 *Showing top {result['row_count']} results (limited for performance).*"
                
                return ChatResponse(
                    message=response_text,
                    metadata={
                        "source": "text_to_sql",
                        "row_count": result.get("row_count", 0),
                        "query_generated": True,
                        "sql_query": result.get("query", "")
                    }
                )
            else:
                # Query failed - return error message
                error_msg = result.get("error", "Unable to process your data query.")
                return ChatResponse(
                    message=f"I couldn't find that information. {error_msg}\n\nTry being more specific about what data you're looking for.",
                    metadata={
                        "source": "text_to_sql",
                        "error": True
                    }
                )
                
        except Exception as e:
            logger.error(f"Text-to-SQL error: {e}", exc_info=True)
            raise  # Re-raise to fall back to LLM
    
    async def get_suggestions(self, user_context: UserContext) -> List[str]:
        """Get initial suggestions based on user context."""
        # Role-based suggestions
        suggestions_by_role = {
            "super_admin": [
                "Show system overview",
                "List all organizations",
                "View all files",
                "Manage users"
            ],
            "org_admin": [
                "My organization's files",
                "Manage users",
                "View reports",
                "Settings"
            ],
            "manager": [
                "Team files",
                "Pending approvals",
                "Upload file",
                "Help"
            ],
            "user": [
                "My files",
                "Upload file",
                "Share a file",
                "Help"
            ],
            "viewer": [
                "Shared files",
                "My account",
                "Help"
            ]
        }
        
        return suggestions_by_role.get(user_context.role, ["Help", "My files"])
    
    async def health_check(self) -> Dict[str, Any]:
        """Check chatbot health status."""
        provider_health = await get_provider_health()
        session_stats = self.session_manager.get_stats()
        
        return {
            "enabled": self.is_enabled,
            "provider": provider_health,
            "sessions": session_stats,
            "config": {
                "provider_type": chatbot_config.provider.value,
                "max_history": chatbot_config.max_history_length
            }
        }
    
    def end_session(self, session_id: str, user_id: str) -> bool:
        """End a chat session (with ownership verification)."""
        session = self.session_manager.get_session(session_id)
        if session and session.user_id == user_id:
            return self.session_manager.end_session(session_id)
        return False
    
    def get_session_history(self, session_id: str, user_id: str) -> Optional[List[dict]]:
        """Get session history (with ownership verification)."""
        session = self.session_manager.get_session(session_id)
        if session and session.user_id == user_id:
            return [msg.to_dict() for msg in session.history]
        return None


# Singleton orchestrator instance
_orchestrator: Optional[ChatbotOrchestrator] = None


def get_chatbot() -> ChatbotOrchestrator:
    """Get the chatbot orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ChatbotOrchestrator()
    return _orchestrator
