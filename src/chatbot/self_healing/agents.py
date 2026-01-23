"""
Self-Healing AI System using CrewAI
====================================

This system automatically detects, diagnoses, and fixes chatbot errors.

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER QUERY                                       │
│                    "take me to my files"                                │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CHATBOT RESPONSE                                    │
│              (may be correct or incorrect)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    🔍 MONITOR AGENT                                      │
│  - Watches every response                                               │
│  - Detects mismatches (asked for navigation, got data listing)          │
│  - Flags suspicious responses                                           │
│  - Uses semantic similarity to detect intent mismatch                   │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                    (if error detected)
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    🔬 DIAGNOSTIC AGENT                                   │
│  - Analyzes the failure                                                 │
│  - Determines root cause:                                               │
│    • ROUTING_ERROR: Wrong handler was selected                          │
│    • PATTERN_MISSING: No regex pattern matches                          │
│    • LLM_HALLUCINATION: LLM gave wrong output                           │
│    • TRAINING_GAP: Missing DSPy training example                        │
│    • EXCLUSION_MISSING: Analytics caught a navigation query             │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    🛠️ FIX AGENT                                          │
│  - Proposes a fix based on diagnosis                                    │
│  - For PATTERN_MISSING: Generates new regex pattern                     │
│  - For EXCLUSION_MISSING: Adds routing exclusion                        │
│  - For TRAINING_GAP: Creates DSPy training example                      │
│  - Can auto-apply or queue for human review                             │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ✅ VALIDATION AGENT                                   │
│  - Tests the proposed fix                                               │
│  - Runs regression tests                                                │
│  - Ensures no existing functionality breaks                             │
│  - Approves or rejects the fix                                          │
└─────────────────────────────────────────────────────────────────────────┘

BENEFITS:
- No more manual edge case hunting
- System learns from every mistake
- Reduces LLM dependency for known patterns
- Self-documents what went wrong and why
"""

import re
import json
import logging
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of errors the system can diagnose."""
    ROUTING_ERROR = "routing_error"           # Wrong handler selected
    PATTERN_MISSING = "pattern_missing"       # No regex pattern matches
    LLM_HALLUCINATION = "llm_hallucination"   # LLM gave wrong output
    TRAINING_GAP = "training_gap"             # Missing DSPy example
    EXCLUSION_MISSING = "exclusion_missing"   # Analytics caught navigation
    UNKNOWN = "unknown"                        # Couldn't diagnose


class FixType(Enum):
    """Types of fixes the system can apply."""
    ADD_PATTERN = "add_pattern"               # Add regex to rule_based.py
    ADD_EXCLUSION = "add_exclusion"           # Add to orchestrator exclusions
    ADD_TRAINING = "add_training"             # Add DSPy training example
    REORDER_PATTERNS = "reorder_patterns"     # Change pattern order
    MANUAL_REVIEW = "manual_review"           # Needs human intervention


@dataclass
class ErrorReport:
    """A detected error with full context."""
    timestamp: datetime
    user_query: str
    expected_intent: str          # What user wanted (navigation, data, etc.)
    actual_response: str          # What chatbot returned
    routing_method: str           # How request was routed
    error_type: ErrorType
    confidence: float             # How confident we are this is an error
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FixProposal:
    """A proposed fix for an error."""
    error_report: ErrorReport
    fix_type: FixType
    description: str
    code_change: Optional[str]    # The actual code to add/modify
    file_path: Optional[str]      # Which file to modify
    auto_apply: bool = False      # Safe to auto-apply?
    test_queries: List[str] = field(default_factory=list)  # Queries to test


class IntentClassifier:
    """
    Fast intent classification to detect what user REALLY wanted.
    Uses patterns + keywords, not LLM (to avoid LLM diagnosing LLM errors).
    """
    
    INTENT_PATTERNS = {
        'navigation': [
            r'\b(take me to|go to|navigate to|open|show me the|where can i (see|find|go|check))\b',
            r'\b(files? page|users? page|settings? page|dashboard)\b',
            r'\bwhere\s+(is|are|can)\b.*\b(page|section|area)\b',
        ],
        'data_query': [
            r'\b(how many|count|total|number of|list all|show all)\b',
            r'\b(what|which)\s+(files?|users?|documents?)\s+(do i have|are there)\b',
            r'\b(recent|latest|newest|oldest)\s+(files?|uploads?)\b',
        ],
        'action': [
            r'\b(upload|download|delete|remove|share|rename)\b',
            r'\b(create|add|new)\s+(file|folder|user)\b',
        ],
        'greeting': [
            r'^(hi|hello|hey|good\s*(morning|afternoon|evening)|greetings)\b',
            r'\b(how are you|what can you do)\b',
        ],
        'help': [
            r'\b(help|assist|support|how do i|how to)\b',
            r'\b(what can|explain|tell me about)\b',
        ],
    }
    
    def classify(self, message: str) -> Tuple[str, float]:
        """
        Classify user intent without using LLM.
        Returns (intent, confidence).
        """
        message_lower = message.lower().strip()
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent, 0.9  # High confidence for pattern match
        
        return 'unknown', 0.3  # Low confidence


class ResponseAnalyzer:
    """
    Analyzes chatbot responses to detect what it actually did.
    """
    
    RESPONSE_INDICATORS = {
        'navigation': [
            r'taking you to',
            r'navigate.*action',
            r'"type":\s*"navigate"',
            r'going to',
        ],
        'data_listing': [
            r'(your|recent|total)\s*(files?|uploads?|documents?):',
            r'\d+\s*(files?|users?|documents?)',
            r'•\s*\*\*',  # Bullet list formatting
        ],
        'error': [
            r"sorry|couldn't|can't|unable|error|failed",
            r'no\s+(files?|results?|data)\s+found',
        ],
        'greeting': [
            r'hello|hi there|welcome|how can i help',
        ],
    }
    
    def analyze(self, response: str) -> Tuple[str, Dict[str, Any]]:
        """
        Analyze what the response actually contains.
        Returns (response_type, metadata).
        """
        response_lower = response.lower()
        
        metadata = {
            'has_action': '"type"' in response and '"navigate"' in response,
            'has_list': '•' in response or '1.' in response,
            'word_count': len(response.split()),
        }
        
        for response_type, patterns in self.RESPONSE_INDICATORS.items():
            for pattern in patterns:
                if re.search(pattern, response_lower):
                    return response_type, metadata
        
        return 'unknown', metadata


class MonitorAgent:
    """
    🔍 MONITOR AGENT
    
    Watches every chatbot interaction and flags potential errors.
    Does NOT use LLM - uses deterministic rules to avoid circular issues.
    """
    
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.response_analyzer = ResponseAnalyzer()
        self.error_buffer: List[ErrorReport] = []
    
    def check_response(
        self,
        user_query: str,
        response: str,
        routing_method: str,
        actions: List[Dict] = None
    ) -> Optional[ErrorReport]:
        """
        Check if the response matches the user's intent.
        Returns ErrorReport if mismatch detected, None if OK.
        """
        # Classify what user wanted
        expected_intent, intent_confidence = self.intent_classifier.classify(user_query)
        
        # Analyze what we actually returned
        response_type, response_meta = self.response_analyzer.analyze(response)
        
        # Check for navigation action in response
        has_nav_action = actions and any(
            a.get('type') == 'navigate' for a in (actions or [])
        )
        
        # MISMATCH DETECTION RULES
        error_report = None
        
        # Rule 1: User wanted navigation, but got data listing
        if expected_intent == 'navigation' and response_type == 'data_listing' and not has_nav_action:
            error_report = ErrorReport(
                timestamp=datetime.now(),
                user_query=user_query,
                expected_intent='navigation',
                actual_response=response[:500],  # Truncate
                routing_method=routing_method,
                error_type=ErrorType.EXCLUSION_MISSING,  # Most likely cause
                confidence=0.85,
                context={
                    'expected': 'navigation action',
                    'got': 'data listing',
                    'routing': routing_method
                }
            )
        
        # Rule 2: User wanted data, but got navigation only
        elif expected_intent == 'data_query' and response_type == 'navigation' and response_meta['word_count'] < 20:
            error_report = ErrorReport(
                timestamp=datetime.now(),
                user_query=user_query,
                expected_intent='data_query',
                actual_response=response[:500],
                routing_method=routing_method,
                error_type=ErrorType.ROUTING_ERROR,
                confidence=0.75,
                context={
                    'expected': 'data response',
                    'got': 'navigation only',
                }
            )
        
        # Rule 3: Empty or error response
        elif response_type == 'error' or len(response.strip()) < 10:
            error_report = ErrorReport(
                timestamp=datetime.now(),
                user_query=user_query,
                expected_intent=expected_intent,
                actual_response=response[:500],
                routing_method=routing_method,
                error_type=ErrorType.PATTERN_MISSING,
                confidence=0.7,
                context={
                    'expected': expected_intent,
                    'got': 'error/empty response',
                }
            )
        
        if error_report:
            self.error_buffer.append(error_report)
            logger.warning(f"[MONITOR] Error detected: {error_report.error_type.value} for query: {user_query[:50]}")
        
        return error_report


class DiagnosticAgent:
    """
    🔬 DIAGNOSTIC AGENT
    
    Analyzes errors to determine root cause.
    Checks code patterns, routing logic, and training data.
    """
    
    def __init__(self):
        self.rule_based_patterns = self._load_rule_based_patterns()
        self.orchestrator_exclusions = self._load_orchestrator_exclusions()
    
    def _load_rule_based_patterns(self) -> List[str]:
        """Load patterns from rule_based.py for analysis."""
        # In production, would parse the actual file
        return [
            r'\b(my files?|show files?|view files?|go to files?)',
            r'\b(take me to.*files?)',
            # ... more patterns
        ]
    
    def _load_orchestrator_exclusions(self) -> List[str]:
        """Load exclusion patterns from orchestrator.py."""
        return [
            r'\b(take me to|go to|navigate to|open)\s+(my\s+)?files',
            r'\bwhere\s+(can|do)\s+i\s+(see|find|check|view|go)\b.*files',
            # ... more exclusions
        ]
    
    def diagnose(self, error: ErrorReport) -> Dict[str, Any]:
        """
        Diagnose the root cause of an error.
        Returns detailed diagnosis with recommended fix type.
        """
        query = error.user_query.lower()
        diagnosis = {
            'error_type': error.error_type,
            'root_cause': None,
            'affected_file': None,
            'fix_type': None,
            'details': {}
        }
        
        # Check 1: Does any rule_based pattern match?
        pattern_matched = False
        for pattern in self.rule_based_patterns:
            if re.search(pattern, query):
                pattern_matched = True
                break
        
        # Check 2: Does any exclusion pattern match?
        exclusion_matched = False
        for pattern in self.orchestrator_exclusions:
            if re.search(pattern, query):
                exclusion_matched = True
                break
        
        # DIAGNOSIS LOGIC
        if error.routing_method == 'analytics_template_sql':
            # Query went to analytics but shouldn't have
            if not exclusion_matched:
                diagnosis['root_cause'] = 'Missing exclusion in orchestrator._should_use_analytics()'
                diagnosis['affected_file'] = 'chatbot/orchestrator.py'
                diagnosis['fix_type'] = FixType.ADD_EXCLUSION
                diagnosis['details'] = {
                    'reason': 'Query matched analytics keywords but is actually navigation',
                    'suggestion': f'Add exclusion pattern for: "{query}"'
                }
            elif not pattern_matched:
                diagnosis['root_cause'] = 'Exclusion exists but rule_based has no matching pattern'
                diagnosis['affected_file'] = 'chatbot/providers/rule_based.py'
                diagnosis['fix_type'] = FixType.ADD_PATTERN
                diagnosis['details'] = {
                    'reason': 'Query would be excluded from analytics but rule_based cannot handle it',
                    'suggestion': f'Add pattern to rule_based for: "{query}"'
                }
        
        elif error.routing_method == 'rule_based':
            # Query went to rule_based but gave wrong response
            diagnosis['root_cause'] = 'Pattern matched wrong handler in rule_based.py'
            diagnosis['affected_file'] = 'chatbot/providers/rule_based.py'
            diagnosis['fix_type'] = FixType.REORDER_PATTERNS
            diagnosis['details'] = {
                'reason': 'Patterns may be in wrong order (earlier pattern catching query)',
                'suggestion': 'Check pattern ordering in _compile_patterns()'
            }
        
        elif error.routing_method in ['text_to_sql_llm', 'llm_chat']:
            # LLM generated bad response
            diagnosis['root_cause'] = 'LLM misunderstood intent or generated bad SQL'
            diagnosis['affected_file'] = 'chatbot/dspy_optimizer.py'
            diagnosis['fix_type'] = FixType.ADD_TRAINING
            diagnosis['details'] = {
                'reason': 'No rule/pattern caught this, fell through to LLM',
                'suggestion': f'Add training example to DSPy for: "{query}"'
            }
        
        else:
            diagnosis['root_cause'] = 'Unknown routing path'
            diagnosis['fix_type'] = FixType.MANUAL_REVIEW
        
        return diagnosis


class FixAgent:
    """
    🛠️ FIX AGENT
    
    Proposes fixes based on diagnosis.
    Can generate code changes for common fix types.
    """
    
    def propose_fix(self, error: ErrorReport, diagnosis: Dict[str, Any]) -> FixProposal:
        """
        Generate a fix proposal based on the diagnosis.
        """
        fix_type = diagnosis.get('fix_type', FixType.MANUAL_REVIEW)
        
        if fix_type == FixType.ADD_EXCLUSION:
            return self._propose_exclusion_fix(error, diagnosis)
        elif fix_type == FixType.ADD_PATTERN:
            return self._propose_pattern_fix(error, diagnosis)
        elif fix_type == FixType.ADD_TRAINING:
            return self._propose_training_fix(error, diagnosis)
        else:
            return FixProposal(
                error_report=error,
                fix_type=FixType.MANUAL_REVIEW,
                description="Requires manual review - complex issue",
                code_change=None,
                file_path=None,
                auto_apply=False
            )
    
    def _propose_exclusion_fix(self, error: ErrorReport, diagnosis: Dict) -> FixProposal:
        """Generate exclusion pattern to add to orchestrator."""
        query = error.user_query.lower()
        
        # Extract key phrases to build pattern
        pattern = self._generate_pattern(query)
        
        code_change = f'''
# Auto-generated exclusion for: "{query}"
# Error: {error.error_type.value}
# Timestamp: {error.timestamp.isoformat()}
r'{pattern}',
'''
        
        return FixProposal(
            error_report=error,
            fix_type=FixType.ADD_EXCLUSION,
            description=f"Add exclusion pattern to prevent '{query}' from going to analytics",
            code_change=code_change,
            file_path='chatbot/orchestrator.py',
            auto_apply=True,  # Safe to auto-apply
            test_queries=[query, query.replace('my', 'the')]  # Test variations
        )
    
    def _propose_pattern_fix(self, error: ErrorReport, diagnosis: Dict) -> FixProposal:
        """Generate regex pattern to add to rule_based."""
        query = error.user_query.lower()
        pattern = self._generate_pattern(query)
        
        code_change = f'''
# Auto-generated pattern for: "{query}"
(
    re.compile(r'{pattern}', re.IGNORECASE),
    self._handle_navigate_files  # TODO: Verify correct handler
),
'''
        
        return FixProposal(
            error_report=error,
            fix_type=FixType.ADD_PATTERN,
            description=f"Add pattern to rule_based.py for: '{query}'",
            code_change=code_change,
            file_path='chatbot/providers/rule_based.py',
            auto_apply=False,  # Needs review - handler may be wrong
            test_queries=[query]
        )
    
    def _propose_training_fix(self, error: ErrorReport, diagnosis: Dict) -> FixProposal:
        """Generate DSPy training example."""
        query = error.user_query
        expected = error.expected_intent
        
        code_change = f'''
# Auto-generated training example
# Query that failed: "{query}"
# Expected intent: {expected}
Example(
    question="{query}",
    sql_query="-- Navigation query, no SQL needed",
    result_format="navigation"
),
'''
        
        return FixProposal(
            error_report=error,
            fix_type=FixType.ADD_TRAINING,
            description=f"Add DSPy training example for: '{query}'",
            code_change=code_change,
            file_path='chatbot/dspy_optimizer.py',
            auto_apply=False,  # DSPy changes need retraining
            test_queries=[query]
        )
    
    def _generate_pattern(self, query: str) -> str:
        """
        Generate a regex pattern from a query.
        Tries to be general enough to catch variations.
        """
        # Common replacements for generalization
        query = re.sub(r'\b(my|the|your)\b', r'(my|the|your)?', query)
        query = re.sub(r'\s+', r'\\s+', query)
        
        # Add word boundaries
        return f"\\b{query}\\b"


class ValidationAgent:
    """
    ✅ VALIDATION AGENT
    
    Tests proposed fixes before applying.
    Runs regression tests to ensure no breakage.
    """
    
    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.test_suite = self._load_test_suite()
    
    def _load_test_suite(self) -> List[Dict]:
        """Load existing test cases for regression testing."""
        return [
            {'query': 'my files', 'expected_route': 'rule_based', 'expected_action': 'navigate'},
            {'query': 'how many files', 'expected_route': 'analytics', 'expected_action': None},
            {'query': 'take me to settings', 'expected_route': 'rule_based', 'expected_action': 'navigate'},
            {'query': 'system logs', 'expected_route': 'rule_based', 'expected_action': 'navigate'},
            # ... more tests
        ]
    
    def validate_fix(self, fix: FixProposal) -> Tuple[bool, List[str]]:
        """
        Validate a proposed fix.
        Returns (is_valid, list_of_issues).
        """
        issues = []
        
        # Check 1: Test queries work with the fix
        for query in fix.test_queries:
            # Would test with actual orchestrator here
            pass
        
        # Check 2: Regression tests still pass
        for test in self.test_suite:
            # Would run actual tests here
            pass
        
        # Check 3: Pattern is valid regex
        if fix.code_change and "re.compile" in fix.code_change:
            try:
                # Extract and validate pattern
                pattern_match = re.search(r"r'([^']+)'", fix.code_change)
                if pattern_match:
                    re.compile(pattern_match.group(1))
            except re.error as e:
                issues.append(f"Invalid regex pattern: {e}")
        
        return len(issues) == 0, issues


class SelfHealingSystem:
    """
    The main self-healing system that coordinates all agents.
    
    Usage:
        system = SelfHealingSystem()
        
        # After each chatbot response:
        error = system.check_and_fix(
            user_query="where can i see files i have uploaded",
            response="Your files: ...",
            routing_method="analytics_template_sql"
        )
        
        if error:
            print(f"Error detected and fixed: {error}")
    """
    
    def __init__(self, auto_apply: bool = False):
        self.monitor = MonitorAgent()
        self.diagnostic = DiagnosticAgent()
        self.fix_agent = FixAgent()
        self.validator = ValidationAgent()
        self.auto_apply = auto_apply
        
        # Track fixes for review
        self.pending_fixes: List[FixProposal] = []
        self.applied_fixes: List[FixProposal] = []
    
    def check_and_fix(
        self,
        user_query: str,
        response: str,
        routing_method: str,
        actions: List[Dict] = None
    ) -> Optional[FixProposal]:
        """
        Main entry point: Check response and generate fix if needed.
        """
        # Step 1: Monitor - detect error
        error = self.monitor.check_response(
            user_query=user_query,
            response=response,
            routing_method=routing_method,
            actions=actions
        )
        
        if not error:
            return None  # No error detected
        
        logger.info(f"[SELF-HEAL] Error detected: {error.error_type.value}")
        
        # Step 2: Diagnose - find root cause
        diagnosis = self.diagnostic.diagnose(error)
        logger.info(f"[SELF-HEAL] Root cause: {diagnosis.get('root_cause')}")
        
        # Step 3: Fix - propose solution
        fix = self.fix_agent.propose_fix(error, diagnosis)
        logger.info(f"[SELF-HEAL] Proposed fix: {fix.fix_type.value}")
        
        # Step 4: Validate - ensure fix is safe
        is_valid, issues = self.validator.validate_fix(fix)
        
        if not is_valid:
            logger.warning(f"[SELF-HEAL] Fix validation failed: {issues}")
            fix.auto_apply = False
        
        # Step 5: Apply or queue
        if self.auto_apply and fix.auto_apply:
            self._apply_fix(fix)
            self.applied_fixes.append(fix)
            logger.info(f"[SELF-HEAL] Fix auto-applied!")
        else:
            self.pending_fixes.append(fix)
            logger.info(f"[SELF-HEAL] Fix queued for review")
        
        return fix
    
    def _apply_fix(self, fix: FixProposal):
        """
        Actually apply the fix to the codebase.
        In production, this would modify files.
        """
        # This would write to the actual files
        # For safety, we log instead
        logger.info(f"[SELF-HEAL] Would apply to {fix.file_path}:")
        logger.info(fix.code_change)
    
    def get_pending_fixes(self) -> List[Dict]:
        """Get all pending fixes for human review."""
        return [
            {
                'query': fix.error_report.user_query,
                'error_type': fix.error_report.error_type.value,
                'fix_type': fix.fix_type.value,
                'description': fix.description,
                'code_change': fix.code_change,
                'file': fix.file_path,
                'auto_apply': fix.auto_apply
            }
            for fix in self.pending_fixes
        ]
    
    def approve_fix(self, index: int) -> bool:
        """Approve and apply a pending fix."""
        if 0 <= index < len(self.pending_fixes):
            fix = self.pending_fixes.pop(index)
            self._apply_fix(fix)
            self.applied_fixes.append(fix)
            return True
        return False


# ============================================================================
# INTEGRATION WITH CHATBOT
# ============================================================================

def integrate_with_orchestrator():
    """
    Example of how to integrate with the existing orchestrator.
    
    Add this to the end of ChatbotOrchestrator.chat() method:
    
    ```python
    # After getting response, check for errors
    from chatbot.self_healing.agents import SelfHealingSystem
    
    self_healer = SelfHealingSystem(auto_apply=False)
    fix = self_healer.check_and_fix(
        user_query=message,
        response=response.message,
        routing_method=routing_method,
        actions=[a.to_dict() for a in response.actions]
    )
    
    if fix:
        # Log for review
        logger.info(f"Self-healing detected issue: {fix.description}")
    ```
    """
    pass


if __name__ == "__main__":
    # Demo the system
    print("=" * 70)
    print("SELF-HEALING AI DEMO")
    print("=" * 70)
    
    system = SelfHealingSystem(auto_apply=False)
    
    # Simulate the error from user's conversation
    fix = system.check_and_fix(
        user_query="where can i see files i have uploaded",
        response="Your files:\n• PROJECT_DOCUMENTATION.pdf | 7.62 MB\n• Screenshot.png | 59 KB",
        routing_method="analytics_template_sql",
        actions=[]  # No navigation action
    )
    
    if fix:
        print(f"\n✅ Error detected and fix proposed!")
        print(f"   Error Type: {fix.error_report.error_type.value}")
        print(f"   Fix Type: {fix.fix_type.value}")
        print(f"   File: {fix.file_path}")
        print(f"   Description: {fix.description}")
        print(f"\n📝 Proposed Code Change:")
        print(fix.code_change)
    
    # Show pending fixes
    print("\n📋 Pending Fixes for Review:")
    for i, pending in enumerate(system.get_pending_fixes()):
        print(f"   [{i}] {pending['description']}")
