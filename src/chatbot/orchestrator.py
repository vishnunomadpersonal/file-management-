"""
Chatbot Orchestrator - Session management and conversation coordination
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import asyncio
import logging
import re
from dataclasses import dataclass, field
from collections import defaultdict

from .providers.base import (
    LLMProvider, ChatMessage, ChatResponse, UserContext, MessageRole
)
from .providers.factory import get_provider, get_provider_health
from .providers.rule_based import RuleBasedProvider
from .config import chatbot_config

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
    
    Uses a hybrid approach:
    - Rule-based provider for navigation and common commands (reliable actions)
    - LLM provider for complex/open-ended queries
    """
    
    # Patterns that should use rule-based provider for reliable action handling
    NAVIGATION_PATTERNS = [
        # General navigation commands
        re.compile(r'\b(go to|take me to|navigate|show me|open)\b.*\b(files?|dashboard|settings|users?|organizations?|approvals?|analytics?|quarantine|security|logs?|team|infrastructure|database|api.?keys?|api.?gateway|platform.?admin)\b', re.IGNORECASE),
        re.compile(r'\b(my files?|show files?|view files?|all files?)\b', re.IGNORECASE),
        re.compile(r'\b(upload|download|share|delete)\b.*\bfile', re.IGNORECASE),
        re.compile(r'\b(list|show|view)\b.*\b(users?|organizations?|team|logs?)\b', re.IGNORECASE),
        re.compile(r'\b(hi|hello|hey|greetings)\b', re.IGNORECASE),
        re.compile(r'\b(help|what can you do|how to)\b', re.IGNORECASE),
        re.compile(r'\b(my role|permissions|who am i)\b', re.IGNORECASE),
        # Specific page keywords
        re.compile(r'\b(analytics?|reports?|statistics?|metrics?)\b', re.IGNORECASE),
        re.compile(r'\b(quarantine|quarantined|infected|virus|malware)\b', re.IGNORECASE),
        re.compile(r'\b(security|access control|rbac)\b', re.IGNORECASE),
        re.compile(r'\b(system logs?|audit|history)\b', re.IGNORECASE),
        re.compile(r'\b(team|members?|colleagues?|staff)\b', re.IGNORECASE),
        re.compile(r'\b(infrastructure|infra|servers?)\b', re.IGNORECASE),
        re.compile(r'\b(database|db|mysql|storage)\b', re.IGNORECASE),
        re.compile(r'\b(api.?keys?|tokens?)\b', re.IGNORECASE),
        re.compile(r'\b(api.?gateway|gateway|kong)\b', re.IGNORECASE),
        re.compile(r'\b(platform.?admin|admin panel)\b', re.IGNORECASE),
    ]
    
    def __init__(self):
        self.session_manager = SessionManager()
        self._provider: Optional[LLMProvider] = None
        self._rule_based: Optional[RuleBasedProvider] = None
    
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
    def is_enabled(self) -> bool:
        """Check if chatbot is enabled."""
        return chatbot_config.enabled
    
    def _should_use_rule_based(self, message: str) -> bool:
        """Check if message should be handled by rule-based provider."""
        for pattern in self.NAVIGATION_PATTERNS:
            if pattern.search(message):
                return True
        return False
    
    async def chat(
        self,
        message: str,
        user_context: UserContext,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message.
        
        Uses hybrid approach:
        - Rule-based for navigation/commands (reliable actions)
        - LLM for complex queries
        
        Args:
            message: User's message
            user_context: User's context with role and permissions
            session_id: Optional existing session ID
            
        Returns:
            Dict with response, session_id, and metadata
        """
        if not self.is_enabled:
            return {
                "error": "Chatbot is disabled",
                "code": "CHATBOT_DISABLED"
            }
        
        # Get or create session
        session = self.session_manager.get_or_create_session(session_id, user_context)
        
        # Add user message to history
        session.add_message(MessageRole.USER, message)
        
        # Hybrid approach: use rule-based for navigation, LLM for complex queries
        if self._should_use_rule_based(message):
            logger.debug(f"Using rule-based provider for message: {message[:50]}...")
            response = await self.rule_based.chat(
                message=message,
                history=session.history[:-1],
                user_context=user_context,
                system_prompt=chatbot_config.system_prompt
            )
        else:
            logger.debug(f"Using LLM provider for message: {message[:50]}...")
            response = await self.provider.chat(
                message=message,
                history=session.history[:-1],  # Exclude current message
                user_context=user_context,
                system_prompt=chatbot_config.system_prompt
            )
        
        # Add assistant response to history
        session.add_message(MessageRole.ASSISTANT, response.message)
        
        return {
            "session_id": session.session_id,
            "response": response.to_dict(),
            "message_count": len(session.history)
        }
    
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
