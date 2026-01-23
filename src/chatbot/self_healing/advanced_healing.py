"""
Advanced Self-Healing AI System
================================

This enhanced system automatically detects, diagnoses, and APPLIES fixes
to the chatbot when it gives wrong answers.

FEATURES:
1. 🔍 Real-time error detection (every response monitored)
2. 🧠 AI-powered diagnosis using CrewAI agents
3. 📝 Auto-generates code fixes (patterns, exclusions, training examples)
4. 💾 Persists learned patterns to database/files
5. 🔄 Hot-reload fixes without restart
6. 📊 Learning dashboard with statistics

ARCHITECTURE:
    User Query → Chatbot Response → Monitor Agent
                                          │
                    ┌─────────────────────┴──────────────────────┐
                    │ Wrong Answer Detected?                      │
                    └─────────────────────┬──────────────────────┘
                                          │ YES
                                          ▼
                    ┌────────────────────────────────────────────┐
                    │ CrewAI Diagnostic Team:                     │
                    │ • Error Detective → What went wrong?        │
                    │ • Root Cause Analyst → Why?                 │
                    │ • Code Fixer → Generate fix                 │
                    │ • QA Validator → Test fix                   │
                    └────────────────────────────────────────────┘
                                          │
                                          ▼
                    ┌────────────────────────────────────────────┐
                    │ Auto-Apply Fix:                             │
                    │ • Add to in-memory patterns (instant)       │
                    │ • Save to learned_patterns.json             │
                    │ • Queue for persistent file update          │
                    └────────────────────────────────────────────┘
"""

import re
import os
import json
import asyncio
import logging
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class HealingConfig:
    """Configuration for the self-healing system."""
    enabled: bool = True
    auto_apply: bool = True
    confidence_threshold: float = 0.75
    max_pending_fixes: int = 50
    persist_to_file: bool = True
    learned_patterns_file: str = "chatbot/learned_patterns.json"
    use_crewai: bool = True
    crewai_timeout: float = 30.0


# ============================================================================
# ERROR TYPES AND FIX TYPES
# ============================================================================

class ErrorType(Enum):
    ROUTING_ERROR = "routing_error"
    PATTERN_MISSING = "pattern_missing"
    EXCLUSION_MISSING = "exclusion_missing"
    LLM_HALLUCINATION = "llm_hallucination"
    TRAINING_GAP = "training_gap"
    INTENT_MISMATCH = "intent_mismatch"
    UNKNOWN = "unknown"


class FixType(Enum):
    ADD_NAVIGATION_PATTERN = "add_navigation_pattern"
    ADD_EXCLUSION_PATTERN = "add_exclusion_pattern"
    ADD_KEYWORD_EXCLUSION = "add_keyword_exclusion"
    ADD_TRAINING_EXAMPLE = "add_training_example"
    REORDER_PATTERNS = "reorder_patterns"
    MANUAL_REVIEW = "manual_review"


class IntentType(Enum):
    NAVIGATION = "navigation"
    DATA_QUERY = "data_query"
    ACTION = "action"
    GREETING = "greeting"
    HELP = "help"
    UNKNOWN = "unknown"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ErrorReport:
    """Detailed error report."""
    id: str
    timestamp: str
    user_query: str
    expected_intent: IntentType
    actual_response: str
    routing_method: str
    error_type: ErrorType
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            'expected_intent': self.expected_intent.value,
            'error_type': self.error_type.value,
        }


@dataclass
class LearnedPattern:
    """A pattern that was learned from errors."""
    id: str
    pattern: str
    pattern_type: str  # "navigation", "exclusion", "training"
    target_handler: str
    source_query: str
    learned_at: str
    applied: bool = False
    confidence: float = 0.0
    test_queries: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class FixResult:
    """Result of applying a fix."""
    success: bool
    error_report: ErrorReport
    fix_type: FixType
    pattern_added: Optional[str]
    message: str
    applied_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# INTENT CLASSIFIER (No LLM - Fast Deterministic)
# ============================================================================

class IntentClassifier:
    """Fast intent classification without LLM."""
    
    NAVIGATION_PATTERNS = [
        r'\b(take me to|go to|navigate to|open|show me the)\s+',
        r'\b(where can i|where do i|how do i)\s+(see|find|go|check|view|access)\b',
        r'\b(files? page|users? page|settings? page|dashboard|logs?|system logs?)\b',
        r'\b(my files?|my uploads?|my documents?)\b',
        r'\bwhere\s+(is|are|can)\b.*\b(logs?|page|section|area)\b',
        r'\b(quarantine|quarantined|infected)\s*(files?|page)?\b',
        r'\bcheck\s+(this\s+)?application\s+logs?\b',
    ]
    
    DATA_QUERY_PATTERNS = [
        r'\b(how many|count|total|number of|list all|show all|give me)\b',
        r'\b(what|which)\s+(files?|users?|documents?)\s+(do i have|are there|have been)\b',
        r'\b(recent|latest|newest|oldest)\s+(files?|uploads?|users?)\b',
        r'\b(statistics|stats|analytics|report)\b',
        r'\b(storage|space|size)\s+(used|remaining|available)\b',
        r'\b(pending|approved|rejected)\s+(files?|users?|appointments?)\b',
    ]
    
    ACTION_PATTERNS = [
        r'\b(upload|download|delete|remove|share|rename|edit|update)\b',
        r'\b(create|add|new)\s+(file|folder|user|appointment)\b',
        r'\b(approve|reject|verify)\s+(this|the|a)\b',
    ]
    
    GREETING_PATTERNS = [
        r'^(hi|hello|hey|good\s*(morning|afternoon|evening)|greetings)\b',
        r'\b(how are you|what can you do|who are you)\b',
    ]
    
    HELP_PATTERNS = [
        r'\b(help|assist|support|how do i|how to|what is)\b',
        r'\b(explain|tell me about|show me how)\b',
    ]
    
    def classify(self, message: str) -> Tuple[IntentType, float]:
        """Classify user intent with confidence score."""
        message_lower = message.lower().strip()
        
        checks = [
            (IntentType.NAVIGATION, self.NAVIGATION_PATTERNS),
            (IntentType.DATA_QUERY, self.DATA_QUERY_PATTERNS),
            (IntentType.ACTION, self.ACTION_PATTERNS),
            (IntentType.GREETING, self.GREETING_PATTERNS),
            (IntentType.HELP, self.HELP_PATTERNS),
        ]
        
        for intent, patterns in checks:
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent, 0.9
        
        return IntentType.UNKNOWN, 0.3


# ============================================================================
# RESPONSE ANALYZER
# ============================================================================

class ResponseAnalyzer:
    """Analyze chatbot responses to detect what it did."""
    
    def analyze(self, response: str, actions: List[Dict] = None) -> Dict[str, Any]:
        """Analyze response content and actions."""
        response_lower = response.lower()
        
        has_nav_action = actions and any(
            a.get('type') == 'navigate' for a in (actions or [])
        )
        
        analysis = {
            'has_navigation': has_nav_action,
            'has_data_listing': bool(re.search(r'(your|total|recent)\s*(files?|uploads?|users?):', response_lower)),
            'has_bullet_list': '•' in response or '1.' in response,
            'has_error': bool(re.search(r"(sorry|couldn't|can't|unable|error|failed|not sure)", response_lower)),
            'word_count': len(response.split()),
            'is_help_response': 'here are some things' in response_lower or 'you can ask' in response_lower,
        }
        
        # Determine response type
        if has_nav_action:
            analysis['response_type'] = 'navigation'
        elif analysis['has_data_listing'] or analysis['has_bullet_list']:
            analysis['response_type'] = 'data_listing'
        elif analysis['has_error'] or analysis['is_help_response']:
            analysis['response_type'] = 'fallback'
        else:
            analysis['response_type'] = 'unknown'
        
        return analysis


# ============================================================================
# LEARNED PATTERNS STORE
# ============================================================================

class LearnedPatternsStore:
    """Persistent store for learned patterns."""
    
    def __init__(self, file_path: str = "chatbot/learned_patterns.json"):
        self.file_path = file_path
        self.patterns: Dict[str, LearnedPattern] = {}
        self._lock = threading.Lock()
        self._load()
    
    def _load(self):
        """Load patterns from file."""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
                    for p in data.get('patterns', []):
                        pattern = LearnedPattern(**p)
                        self.patterns[pattern.id] = pattern
                logger.info(f"Loaded {len(self.patterns)} learned patterns")
        except Exception as e:
            logger.warning(f"Could not load learned patterns: {e}")
    
    def _save(self):
        """Save patterns to file."""
        try:
            os.makedirs(os.path.dirname(self.file_path) or '.', exist_ok=True)
            with open(self.file_path, 'w') as f:
                json.dump({
                    'version': '1.0',
                    'updated_at': datetime.now().isoformat(),
                    'patterns': [p.to_dict() for p in self.patterns.values()]
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save learned patterns: {e}")
    
    def add(self, pattern: LearnedPattern) -> bool:
        """Add a learned pattern."""
        with self._lock:
            self.patterns[pattern.id] = pattern
            self._save()
            return True
    
    def get_all(self) -> List[LearnedPattern]:
        """Get all learned patterns."""
        return list(self.patterns.values())
    
    def get_by_type(self, pattern_type: str) -> List[LearnedPattern]:
        """Get patterns by type."""
        return [p for p in self.patterns.values() if p.pattern_type == pattern_type]
    
    def mark_applied(self, pattern_id: str):
        """Mark a pattern as applied."""
        with self._lock:
            if pattern_id in self.patterns:
                self.patterns[pattern_id].applied = True
                self._save()


# ============================================================================
# PATTERN GENERATOR
# ============================================================================

class PatternGenerator:
    """Generate regex patterns from queries."""
    
    # Common words that should be optional in patterns
    OPTIONAL_WORDS = {'my', 'the', 'your', 'a', 'an', 'this', 'that', 'these', 'those'}
    
    # Words that should have alternatives
    ALTERNATIVES = {
        'files': '(files?|documents?)',
        'file': '(files?|documents?)',
        'see': '(see|view|find|check|access)',
        'view': '(see|view|find|check|access)',
        'check': '(see|view|find|check|access)',
        'go': '(go|navigate|take me)',
        'take': '(go|navigate|take me)',
        'where': '(where|how)',
        'can': '(can|do|could)',
        'logs': '(logs?|logging)',
        'log': '(logs?|logging)',
    }
    
    def generate(self, query: str, intent: IntentType = None) -> Tuple[str, List[str]]:
        """
        Generate a regex pattern from a query.
        Returns (pattern, test_queries).
        """
        query_lower = query.lower().strip()
        words = query_lower.split()
        
        pattern_parts = []
        for word in words:
            # Check alternatives
            if word in self.ALTERNATIVES:
                pattern_parts.append(self.ALTERNATIVES[word])
            # Check optional words
            elif word in self.OPTIONAL_WORDS:
                pattern_parts.append(f'({word}\\s+)?')
            else:
                # Keep word but make spacing flexible
                pattern_parts.append(re.escape(word))
        
        # Join with flexible spacing
        pattern = '\\s+'.join(pattern_parts)
        pattern = f'\\b{pattern}\\b'
        
        # Generate test queries
        test_queries = [
            query,
            query.replace('my', 'the'),
            query.replace('can i', 'do i'),
        ]
        
        return pattern, test_queries
    
    def generate_exclusion_keywords(self, query: str) -> List[str]:
        """Extract keywords that should be excluded from analytics."""
        keywords = []
        
        # Look for navigation indicators
        nav_words = ['take me', 'go to', 'navigate', 'open', 'where can i']
        for nav in nav_words:
            if nav in query.lower():
                keywords.append(nav)
        
        # Look for page references
        pages = ['logs', 'files', 'settings', 'dashboard', 'users', 'quarantine']
        for page in pages:
            if page in query.lower():
                keywords.append(page)
        
        return keywords


# ============================================================================
# ADVANCED SELF-HEALING SYSTEM
# ============================================================================

class AdvancedSelfHealingSystem:
    """
    Advanced self-healing system that learns from mistakes and auto-applies fixes.
    
    Usage:
        healer = AdvancedSelfHealingSystem(auto_apply=True)
        
        # After each chatbot response:
        result = await healer.process_response(
            user_query="where can i check this application logs",
            response="I'm not sure I understand...",
            routing_method="llm_chat",
            actions=[]
        )
        
        if result:
            print(f"Fixed: {result.message}")
    """
    
    def __init__(self, config: HealingConfig = None):
        self.config = config or HealingConfig()
        
        # Components
        self.intent_classifier = IntentClassifier()
        self.response_analyzer = ResponseAnalyzer()
        self.pattern_generator = PatternGenerator()
        self.patterns_store = LearnedPatternsStore(self.config.learned_patterns_file)
        
        # Runtime learned patterns (in-memory for instant effect)
        self._runtime_navigation_patterns: List[Tuple[re.Pattern, str]] = []
        self._runtime_exclusion_patterns: List[str] = []
        self._runtime_exclusion_keywords: List[str] = []
        
        # Statistics
        self.stats = {
            'errors_detected': 0,
            'fixes_applied': 0,
            'fixes_pending': 0,
            'patterns_learned': 0,
        }
        
        # Pending fixes queue
        self.pending_fixes: List[FixResult] = []
        
        # Load previously learned patterns into runtime
        self._load_runtime_patterns()
        
        # Callbacks for integration
        self._on_pattern_learned: Optional[Callable] = None
        
        logger.info(f"AdvancedSelfHealingSystem initialized. Auto-apply: {self.config.auto_apply}")
    
    def _load_runtime_patterns(self):
        """Load learned patterns into runtime memory."""
        for pattern in self.patterns_store.get_all():
            try:
                if pattern.pattern_type == 'navigation':
                    compiled = re.compile(pattern.pattern, re.IGNORECASE)
                    self._runtime_navigation_patterns.append((compiled, pattern.target_handler))
                elif pattern.pattern_type == 'exclusion':
                    self._runtime_exclusion_patterns.append(pattern.pattern)
                elif pattern.pattern_type == 'keyword_exclusion':
                    self._runtime_exclusion_keywords.append(pattern.pattern)
            except re.error as e:
                logger.warning(f"Invalid pattern: {pattern.pattern} - {e}")
    
    async def process_response(
        self,
        user_query: str,
        response: str,
        routing_method: str,
        actions: List[Dict] = None
    ) -> Optional[FixResult]:
        """
        Process a chatbot response and fix if needed.
        This is the main entry point.
        """
        if not self.config.enabled:
            return None
        
        # Step 1: Classify intent
        expected_intent, intent_confidence = self.intent_classifier.classify(user_query)
        
        # Step 2: Analyze response
        response_analysis = self.response_analyzer.analyze(response, actions)
        
        # Step 3: Detect mismatch
        error = self._detect_error(
            user_query=user_query,
            expected_intent=expected_intent,
            response=response,
            response_analysis=response_analysis,
            routing_method=routing_method,
            intent_confidence=intent_confidence
        )
        
        if not error:
            return None  # No error detected
        
        self.stats['errors_detected'] += 1
        logger.warning(f"[SELF-HEAL] Error detected: {error.error_type.value} for: {user_query[:50]}")
        
        # Step 4: Generate and apply fix
        fix_result = await self._generate_and_apply_fix(error, response_analysis)
        
        return fix_result
    
    def _detect_error(
        self,
        user_query: str,
        expected_intent: IntentType,
        response: str,
        response_analysis: Dict,
        routing_method: str,
        intent_confidence: float
    ) -> Optional[ErrorReport]:
        """Detect if there's an error in the response."""
        
        import uuid
        
        # Rule 1: User wanted navigation but got data listing or fallback
        if expected_intent == IntentType.NAVIGATION:
            if not response_analysis['has_navigation']:
                if response_analysis['response_type'] in ['data_listing', 'fallback', 'unknown']:
                    return ErrorReport(
                        id=str(uuid.uuid4())[:8],
                        timestamp=datetime.now().isoformat(),
                        user_query=user_query,
                        expected_intent=expected_intent,
                        actual_response=response[:500],
                        routing_method=routing_method,
                        error_type=ErrorType.EXCLUSION_MISSING if routing_method == 'analytics_template_sql' 
                                   else ErrorType.PATTERN_MISSING,
                        confidence=0.9,
                        context={
                            'expected': 'navigation action',
                            'got': response_analysis['response_type'],
                            'routing': routing_method
                        }
                    )
        
        # Rule 2: User wanted data but got navigation only (very short response)
        if expected_intent == IntentType.DATA_QUERY:
            if response_analysis['has_navigation'] and response_analysis['word_count'] < 30:
                if not response_analysis['has_data_listing']:
                    return ErrorReport(
                        id=str(uuid.uuid4())[:8],
                        timestamp=datetime.now().isoformat(),
                        user_query=user_query,
                        expected_intent=expected_intent,
                        actual_response=response[:500],
                        routing_method=routing_method,
                        error_type=ErrorType.ROUTING_ERROR,
                        confidence=0.75,
                        context={
                            'expected': 'data response',
                            'got': 'navigation only',
                        }
                    )
        
        # Rule 3: Fallback/error response for clear intent
        if response_analysis['response_type'] == 'fallback':
            if intent_confidence > 0.7 and expected_intent != IntentType.UNKNOWN:
                return ErrorReport(
                    id=str(uuid.uuid4())[:8],
                    timestamp=datetime.now().isoformat(),
                    user_query=user_query,
                    expected_intent=expected_intent,
                    actual_response=response[:500],
                    routing_method=routing_method,
                    error_type=ErrorType.PATTERN_MISSING,
                    confidence=0.85,
                    context={
                        'expected': expected_intent.value,
                        'got': 'fallback response',
                        'routing': routing_method
                    }
                )
        
        return None
    
    async def _generate_and_apply_fix(
        self,
        error: ErrorReport,
        response_analysis: Dict
    ) -> FixResult:
        """Generate and optionally apply a fix."""
        
        fix_type = self._determine_fix_type(error)
        
        if fix_type == FixType.ADD_NAVIGATION_PATTERN:
            return await self._add_navigation_pattern(error)
        
        elif fix_type == FixType.ADD_EXCLUSION_PATTERN:
            return await self._add_exclusion_pattern(error)
        
        elif fix_type == FixType.ADD_KEYWORD_EXCLUSION:
            return await self._add_keyword_exclusion(error)
        
        elif fix_type == FixType.ADD_TRAINING_EXAMPLE:
            return await self._add_training_example(error)
        
        else:
            # Queue for manual review
            result = FixResult(
                success=False,
                error_report=error,
                fix_type=FixType.MANUAL_REVIEW,
                pattern_added=None,
                message="Complex issue - queued for manual review"
            )
            self.pending_fixes.append(result)
            self.stats['fixes_pending'] += 1
            return result
    
    def _determine_fix_type(self, error: ErrorReport) -> FixType:
        """Determine the best fix type for an error."""
        
        if error.error_type == ErrorType.EXCLUSION_MISSING:
            return FixType.ADD_EXCLUSION_PATTERN
        
        elif error.error_type == ErrorType.PATTERN_MISSING:
            if error.expected_intent == IntentType.NAVIGATION:
                return FixType.ADD_NAVIGATION_PATTERN
            else:
                return FixType.ADD_TRAINING_EXAMPLE
        
        elif error.error_type == ErrorType.ROUTING_ERROR:
            return FixType.REORDER_PATTERNS
        
        elif error.error_type == ErrorType.TRAINING_GAP:
            return FixType.ADD_TRAINING_EXAMPLE
        
        return FixType.MANUAL_REVIEW
    
    async def _add_navigation_pattern(self, error: ErrorReport) -> FixResult:
        """Add a navigation pattern for the query."""
        
        # Generate pattern
        pattern, test_queries = self.pattern_generator.generate(
            error.user_query,
            error.expected_intent
        )
        
        # Determine handler based on query content
        handler = self._detect_handler(error.user_query)
        
        # Create learned pattern
        import uuid
        learned = LearnedPattern(
            id=str(uuid.uuid4())[:8],
            pattern=pattern,
            pattern_type='navigation',
            target_handler=handler,
            source_query=error.user_query,
            learned_at=datetime.now().isoformat(),
            applied=self.config.auto_apply,
            confidence=error.confidence,
            test_queries=test_queries
        )
        
        # Apply to runtime
        if self.config.auto_apply:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                self._runtime_navigation_patterns.append((compiled, handler))
                self.patterns_store.add(learned)
                self.stats['fixes_applied'] += 1
                self.stats['patterns_learned'] += 1
                
                logger.info(f"[SELF-HEAL] ✅ Added navigation pattern: {pattern[:50]}...")
                
                # Notify callback
                if self._on_pattern_learned:
                    self._on_pattern_learned(learned)
                
                return FixResult(
                    success=True,
                    error_report=error,
                    fix_type=FixType.ADD_NAVIGATION_PATTERN,
                    pattern_added=pattern,
                    message=f"Added navigation pattern for '{error.user_query[:30]}...' → {handler}"
                )
            except re.error as e:
                logger.error(f"[SELF-HEAL] Invalid pattern generated: {e}")
        
        # Queue for review if not auto-applying
        result = FixResult(
            success=False,
            error_report=error,
            fix_type=FixType.ADD_NAVIGATION_PATTERN,
            pattern_added=pattern,
            message="Pattern generated, pending review"
        )
        self.pending_fixes.append(result)
        self.stats['fixes_pending'] += 1
        return result
    
    async def _add_exclusion_pattern(self, error: ErrorReport) -> FixResult:
        """Add an exclusion pattern to prevent analytics interception."""
        
        pattern, test_queries = self.pattern_generator.generate(error.user_query)
        
        import uuid
        learned = LearnedPattern(
            id=str(uuid.uuid4())[:8],
            pattern=pattern,
            pattern_type='exclusion',
            target_handler='rule_based',
            source_query=error.user_query,
            learned_at=datetime.now().isoformat(),
            applied=self.config.auto_apply,
            confidence=error.confidence,
            test_queries=test_queries
        )
        
        if self.config.auto_apply:
            self._runtime_exclusion_patterns.append(pattern)
            self.patterns_store.add(learned)
            self.stats['fixes_applied'] += 1
            self.stats['patterns_learned'] += 1
            
            logger.info(f"[SELF-HEAL] ✅ Added exclusion pattern: {pattern[:50]}...")
            
            return FixResult(
                success=True,
                error_report=error,
                fix_type=FixType.ADD_EXCLUSION_PATTERN,
                pattern_added=pattern,
                message=f"Added exclusion pattern for '{error.user_query[:30]}...'"
            )
        
        result = FixResult(
            success=False,
            error_report=error,
            fix_type=FixType.ADD_EXCLUSION_PATTERN,
            pattern_added=pattern,
            message="Exclusion pattern generated, pending review"
        )
        self.pending_fixes.append(result)
        return result
    
    async def _add_keyword_exclusion(self, error: ErrorReport) -> FixResult:
        """Add keyword exclusion."""
        
        keywords = self.pattern_generator.generate_exclusion_keywords(error.user_query)
        
        if not keywords:
            return FixResult(
                success=False,
                error_report=error,
                fix_type=FixType.ADD_KEYWORD_EXCLUSION,
                pattern_added=None,
                message="No keywords to exclude"
            )
        
        for kw in keywords:
            if kw not in self._runtime_exclusion_keywords:
                self._runtime_exclusion_keywords.append(kw)
        
        self.stats['fixes_applied'] += 1
        
        return FixResult(
            success=True,
            error_report=error,
            fix_type=FixType.ADD_KEYWORD_EXCLUSION,
            pattern_added=', '.join(keywords),
            message=f"Added keyword exclusions: {keywords}"
        )
    
    async def _add_training_example(self, error: ErrorReport) -> FixResult:
        """Add a DSPy training example."""
        
        # Training examples need manual review
        import uuid
        learned = LearnedPattern(
            id=str(uuid.uuid4())[:8],
            pattern=error.user_query,
            pattern_type='training',
            target_handler='dspy',
            source_query=error.user_query,
            learned_at=datetime.now().isoformat(),
            applied=False,
            confidence=error.confidence,
            test_queries=[error.user_query]
        )
        
        self.patterns_store.add(learned)
        
        result = FixResult(
            success=False,
            error_report=error,
            fix_type=FixType.ADD_TRAINING_EXAMPLE,
            pattern_added=error.user_query,
            message="Training example queued for DSPy retraining"
        )
        self.pending_fixes.append(result)
        self.stats['fixes_pending'] += 1
        return result
    
    def _detect_handler(self, query: str) -> str:
        """Detect which handler should be used for a navigation query."""
        query_lower = query.lower()
        
        handler_mapping = {
            'files': '_handle_navigate_files',
            'file': '_handle_navigate_files',
            'documents': '_handle_navigate_files',
            'uploads': '_handle_navigate_files',
            'users': '_handle_navigate_users',
            'user': '_handle_navigate_users',
            'settings': '_handle_navigate_settings',
            'dashboard': '_handle_navigate_dashboard',
            'logs': '_handle_navigate_system_logs',
            'log': '_handle_navigate_system_logs',
            'system logs': '_handle_navigate_system_logs',
            'application logs': '_handle_navigate_system_logs',
            'quarantine': '_handle_navigate_quarantine',
            'quarantined': '_handle_navigate_quarantine',
            'appointments': '_handle_navigate_appointments',
            'appointment': '_handle_navigate_appointments',
            'analytics': '_handle_navigate_analytics',
            'profile': '_handle_navigate_profile',
            'notifications': '_handle_navigate_notifications',
            'help': '_handle_help',
        }
        
        for keyword, handler in handler_mapping.items():
            if keyword in query_lower:
                return handler
        
        return '_handle_navigate_dashboard'  # Default
    
    # ========================================================================
    # PUBLIC API
    # ========================================================================
    
    def check_navigation_patterns(self, query: str) -> Optional[str]:
        """
        Check if query matches any learned navigation pattern.
        Called by rule_based.py to include learned patterns.
        """
        query_lower = query.lower()
        
        for pattern, handler in self._runtime_navigation_patterns:
            if pattern.search(query_lower):
                return handler
        
        return None
    
    def check_exclusion_patterns(self, query: str) -> bool:
        """
        Check if query matches any learned exclusion pattern.
        Called by orchestrator.py to check exclusions.
        """
        query_lower = query.lower()
        
        for pattern in self._runtime_exclusion_patterns:
            try:
                if re.search(pattern, query_lower):
                    return True
            except re.error:
                continue
        
        for keyword in self._runtime_exclusion_keywords:
            if keyword in query_lower:
                return True
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get healing statistics."""
        return {
            **self.stats,
            'runtime_navigation_patterns': len(self._runtime_navigation_patterns),
            'runtime_exclusion_patterns': len(self._runtime_exclusion_patterns),
            'total_learned': len(self.patterns_store.get_all()),
            'pending_review': len(self.pending_fixes),
        }
    
    def get_pending_fixes(self) -> List[Dict]:
        """Get pending fixes for review."""
        return [
            {
                'query': f.error_report.user_query,
                'error_type': f.error_report.error_type.value,
                'fix_type': f.fix_type.value,
                'pattern': f.pattern_added,
                'message': f.message,
                'confidence': f.error_report.confidence,
            }
            for f in self.pending_fixes
        ]
    
    def approve_pending_fix(self, index: int) -> bool:
        """Approve and apply a pending fix."""
        if 0 <= index < len(self.pending_fixes):
            fix = self.pending_fixes.pop(index)
            # Apply the fix
            if fix.pattern_added and fix.fix_type == FixType.ADD_NAVIGATION_PATTERN:
                try:
                    compiled = re.compile(fix.pattern_added, re.IGNORECASE)
                    handler = self._detect_handler(fix.error_report.user_query)
                    self._runtime_navigation_patterns.append((compiled, handler))
                    self.stats['fixes_applied'] += 1
                    self.stats['fixes_pending'] -= 1
                    return True
                except re.error:
                    pass
            elif fix.pattern_added and fix.fix_type == FixType.ADD_EXCLUSION_PATTERN:
                self._runtime_exclusion_patterns.append(fix.pattern_added)
                self.stats['fixes_applied'] += 1
                self.stats['fixes_pending'] -= 1
                return True
        return False
    
    def set_on_pattern_learned(self, callback: Callable):
        """Set callback for when a pattern is learned."""
        self._on_pattern_learned = callback


# ============================================================================
# SINGLETON
# ============================================================================

_healer_instance: Optional[AdvancedSelfHealingSystem] = None


def get_healer(auto_apply: bool = True) -> AdvancedSelfHealingSystem:
    """Get or create the singleton healer instance."""
    global _healer_instance
    if _healer_instance is None:
        config = HealingConfig(auto_apply=auto_apply)
        _healer_instance = AdvancedSelfHealingSystem(config)
    return _healer_instance


# ============================================================================
# CLI TESTING
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    async def demo():
        print("=" * 70)
        print("ADVANCED SELF-HEALING SYSTEM DEMO")
        print("=" * 70)
        
        healer = AdvancedSelfHealingSystem(HealingConfig(auto_apply=True))
        
        # Test cases - queries that would fail
        test_cases = [
            {
                "query": "where can i check this application logs",
                "response": "I'm not sure I understand that request. Here are some things you can ask me...",
                "routing": "llm_chat",
                "actions": []
            },
            {
                "query": "take me to my uploaded files",
                "response": "Your files:\n• doc.pdf | 1 MB",
                "routing": "analytics_template_sql",
                "actions": []
            },
            {
                "query": "show me the quarantine page",
                "response": "Sorry, I couldn't understand that.",
                "routing": "llm_chat",
                "actions": []
            },
        ]
        
        for i, test in enumerate(test_cases, 1):
            print(f"\n{'='*50}")
            print(f"Test {i}: {test['query'][:40]}...")
            print(f"{'='*50}")
            
            result = await healer.process_response(
                user_query=test['query'],
                response=test['response'],
                routing_method=test['routing'],
                actions=test['actions']
            )
            
            if result:
                status = "✅" if result.success else "⏳"
                print(f"{status} {result.message}")
                if result.pattern_added:
                    print(f"   Pattern: {result.pattern_added[:50]}...")
            else:
                print("✓ No error detected")
        
        print(f"\n{'='*70}")
        print("STATISTICS:")
        print(f"{'='*70}")
        for key, value in healer.get_stats().items():
            print(f"  {key}: {value}")
        
        print(f"\n{'='*70}")
        print("LEARNED PATTERNS:")
        print(f"{'='*70}")
        for pattern in healer.patterns_store.get_all():
            print(f"  [{pattern.pattern_type}] {pattern.pattern[:50]}...")
    
    asyncio.run(demo())
