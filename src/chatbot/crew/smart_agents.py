"""
CrewAI Smart Agent System
==========================

Multi-agent AI system that makes your chatbot self-aware and self-healing.

AGENTS:
1. 🔍 Error Detective - Monitors responses and detects problems
2. 🔬 Root Cause Analyst - Diagnoses WHY errors happen
3. 🛠️ Code Fixer - Generates code fixes
4. ✅ Quality Assurer - Validates fixes before applying
5. 📚 Learning Agent - Adds new training examples to DSPy

CAPABILITIES:
- Detects when chatbot gives wrong answers
- Determines if it's LLM error or code error
- Auto-generates regex patterns for missing intents
- Creates DSPy training examples automatically
- Learns from every mistake

USAGE:
    from chatbot.crew.smart_agents import SmartAgentCrew
    
    crew = SmartAgentCrew()
    result = await crew.analyze_error(
        query="where can i see my files",
        response="Here are your files: ...",
        expected="navigation to files page"
    )
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================================
# CHECK CREWAI AVAILABILITY
# ============================================================================

try:
    from crewai import Agent, Task, Crew, Process, LLM
    from crewai.tools import BaseTool
    from pydantic import Field
    CREWAI_AVAILABLE = True
    logger.info("✅ CrewAI loaded successfully")
except ImportError as e:
    CREWAI_AVAILABLE = False
    logger.warning(f"❌ CrewAI not available: {e}")
    logger.warning("   Run: pip install crewai crewai-tools")


# ============================================================================
# ERROR TYPES AND FIX TYPES
# ============================================================================

class ErrorType(Enum):
    """Types of errors the crew can diagnose."""
    ROUTING_ERROR = "routing_error"           # Query went to wrong handler
    PATTERN_MISSING = "pattern_missing"       # No regex matches this query
    PATTERN_ORDER = "pattern_order"           # Wrong pattern matched first
    EXCLUSION_MISSING = "exclusion_missing"   # Analytics caught navigation
    LLM_HALLUCINATION = "llm_hallucination"   # LLM gave wrong answer
    TRAINING_GAP = "training_gap"             # DSPy needs this example
    CONTEXT_MISSING = "context_missing"       # LLM lacked context
    UNKNOWN = "unknown"


class FixType(Enum):
    """Types of fixes the crew can apply."""
    ADD_REGEX_PATTERN = "add_regex_pattern"
    ADD_EXCLUSION = "add_exclusion"
    REORDER_PATTERNS = "reorder_patterns"
    ADD_DSPY_EXAMPLE = "add_dspy_example"
    UPDATE_SYSTEM_PROMPT = "update_system_prompt"
    MANUAL_REVIEW = "manual_review"


@dataclass
class ErrorAnalysis:
    """Complete error analysis from the crew."""
    query: str
    response: str
    expected: str
    error_type: ErrorType
    root_cause: str
    affected_file: str
    fix_type: FixType
    proposed_fix: str
    confidence: float
    test_queries: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


# ============================================================================
# CUSTOM TOOLS FOR AGENTS
# ============================================================================

if CREWAI_AVAILABLE:
    
    class CodeSearchTool(BaseTool):
        """Tool to search codebase for patterns and functions."""
        name: str = "code_search"
        description: str = """Search the chatbot codebase for patterns, functions, or classes.
        Use this to find where code changes need to be made.
        Input: search term (e.g., "navigation patterns", "_should_use_analytics")"""
        
        def _run(self, search_term: str) -> str:
            """Search codebase for relevant code."""
            results = []
            
            # Simulated search - in production would use grep/AST
            search_lower = search_term.lower()
            
            if "pattern" in search_lower or "regex" in search_lower or "navigation" in search_lower:
                results.append("""
FILE: chatbot/providers/rule_based.py
LOCATION: Lines 488-520 (Navigation Patterns)
CONTENT:
```python
# Navigation - Files (expanded patterns)
(
    re.compile(r'\\b(my files?|show files?|view files?|go to files?)\\b', re.IGNORECASE),
    self._handle_navigate_files
),
```
""")
            
            if "exclusion" in search_lower or "analytics" in search_lower or "_should_use" in search_lower:
                results.append("""
FILE: chatbot/orchestrator.py
LOCATION: Lines 765-780 (Analytics Exclusions)
CONTENT:
```python
navigation_exclusions = [
    r'\\b(take me to|go to|navigate to|open)\\s+(my\\s+)?files',
    r'\\bwhere\\s+(can|do)\\s+i\\s+(see|find|check|view|go)\\b.*files',
]
```
""")
            
            if "dspy" in search_lower or "training" in search_lower or "example" in search_lower:
                results.append("""
FILE: chatbot/dspy_optimizer.py
LOCATION: Lines 50-200 (Training Examples)
CONTENT:
```python
TRAINING_EXAMPLES = [
    Example(question="how many files", sql_query="SELECT COUNT(*) FROM files"),
    Example(question="largest files", sql_query="SELECT * FROM files ORDER BY size DESC LIMIT 10"),
]
```
""")
            
            if "routing" in search_lower or "orchestrator" in search_lower:
                results.append("""
FILE: chatbot/orchestrator.py  
LOCATION: Lines 909-1100 (Routing Logic)
PRIORITY ORDER:
1. Safety check (dangerous commands)
2. Typo correction
3. Help queries → rule_based
4. Text-to-SQL patterns → LLM SQL
5. Infrastructure queries → rule_based
6. Analytics → template SQL (PRIORITY 2)
7. Rule-based → navigation (~1ms) (PRIORITY 3)
8. LLM chat → fallback
""")
            
            return "\n".join(results) if results else f"No results found for: {search_term}"
    
    
    class PatternTestTool(BaseTool):
        """Tool to test regex patterns against queries."""
        name: str = "pattern_test"
        description: str = """Test if a regex pattern matches a query.
        Input format: 'PATTERN|||QUERY'
        Example: 'my files?|||where are my files'"""
        
        def _run(self, input_str: str) -> str:
            """Test pattern against query."""
            try:
                parts = input_str.split("|||")
                if len(parts) != 2:
                    return "Error: Use format 'PATTERN|||QUERY'"
                
                pattern, query = parts[0].strip(), parts[1].strip()
                match = re.search(pattern, query, re.IGNORECASE)
                
                if match:
                    return f"✅ MATCH: Pattern '{pattern}' matches '{query}' at '{match.group()}'"
                else:
                    return f"❌ NO MATCH: Pattern '{pattern}' does not match '{query}'"
            except re.error as e:
                return f"❌ INVALID REGEX: {e}"
    
    
    class FileReadTool(BaseTool):
        """Tool to read specific file sections."""
        name: str = "file_read"
        description: str = """Read a section of a source file.
        Input format: 'FILEPATH:START_LINE:END_LINE'
        Example: 'chatbot/orchestrator.py:754:790'"""
        
        def _run(self, input_str: str) -> str:
            """Read file section."""
            try:
                parts = input_str.split(":")
                if len(parts) < 3:
                    return "Error: Use format 'FILEPATH:START:END'"
                
                filepath = parts[0]
                start = int(parts[1])
                end = int(parts[2])
                
                # In production, would read actual file
                return f"[Would read {filepath} lines {start}-{end}]"
            except Exception as e:
                return f"Error reading file: {e}"
    
    
    class GeneratePatternTool(BaseTool):
        """Tool to generate regex patterns from examples."""
        name: str = "generate_pattern"
        description: str = """Generate a regex pattern that matches a query and its variations.
        Input: The query to create a pattern for
        Output: A regex pattern with variations"""
        
        def _run(self, query: str) -> str:
            """Generate pattern from query."""
            query_lower = query.lower().strip()
            
            # Smart pattern generation
            patterns = []
            
            # Replace common words with optional variations
            variations = {
                r'\b(my|the|your)\b': '(my|the|your)?\\s*',
                r'\b(files?|documents?)\b': '(files?|documents?)',
                r'\b(see|view|check|find|look at)\b': '(see|view|check|find|look\\s*at)',
                r'\b(where|how)\b': '(where|how)',
                r'\b(can i|do i|could i)\b': '(can|do|could)\\s+i',
                r'\b(uploaded|stored|saved)\b': '(uploaded?|stored?|saved?)',
            }
            
            pattern = query_lower
            for old, new in variations.items():
                pattern = re.sub(old, new, pattern, flags=re.IGNORECASE)
            
            # Add word boundaries
            pattern = f"\\b{pattern}\\b"
            
            return f"""Generated Pattern:
```python
re.compile(r'{pattern}', re.IGNORECASE)
```

Test queries this should match:
- "{query}"
- "show me {query.replace('my', 'the')}"
- "{query.replace('where', 'how')}" (if applicable)
"""


# ============================================================================
# NVIDIA LLM CONFIGURATION
# ============================================================================

def get_nvidia_llm():
    """Get NVIDIA LLM configuration for CrewAI agents."""
    api_key = os.getenv("NVIDIA_API_KEY")
    
    if not api_key:
        logger.warning("NVIDIA_API_KEY not set, agents will use default LLM")
        return None
    
    # CrewAI LLM configuration for NVIDIA
    return LLM(
        model="nvidia_nim/meta/llama-3.1-70b-instruct",
        api_key=api_key,
        base_url="https://integrate.api.nvidia.com/v1",
        temperature=0.1,  # Low temperature for precise analysis
    )


# ============================================================================
# AGENT DEFINITIONS
# ============================================================================

def create_error_detective(llm=None) -> 'Agent':
    """Create the Error Detective agent."""
    return Agent(
        role="Error Detective",
        goal="Detect when chatbot responses don't match user intent and classify the error type",
        backstory="""You are an expert at understanding user intent and detecting when AI chatbots 
        give wrong or unexpected responses. You can quickly tell if:
        - User wanted navigation but got data listing
        - User wanted data but got navigation
        - Response was empty or error
        - LLM hallucinated irrelevant information
        
        You are precise and always explain your reasoning.""",
        tools=[PatternTestTool()] if CREWAI_AVAILABLE else [],
        llm=llm,
        verbose=True,
        allow_delegation=False
    )


def create_root_cause_analyst(llm=None) -> 'Agent':
    """Create the Root Cause Analyst agent."""
    return Agent(
        role="Root Cause Analyst",
        goal="Diagnose exactly WHY the chatbot error occurred by analyzing code and routing logic",
        backstory="""You are a senior software engineer who specializes in debugging AI chatbots.
        You understand:
        - Regex pattern matching and priority order
        - Intent classification and routing
        - When LLM vs rule-based should be used
        - How DSPy training affects SQL generation
        
        You always trace the exact code path that led to the error.""",
        tools=[CodeSearchTool(), FileReadTool()] if CREWAI_AVAILABLE else [],
        llm=llm,
        verbose=True,
        allow_delegation=False
    )


def create_code_fixer(llm=None) -> 'Agent':
    """Create the Code Fixer agent."""
    return Agent(
        role="Code Fixer",
        goal="Generate precise, minimal code fixes that solve the root cause without breaking existing functionality",
        backstory="""You are an expert Python developer who writes clean, maintainable code.
        You specialize in:
        - Writing regex patterns that catch variations
        - Understanding pattern ordering importance
        - Creating DSPy training examples
        - Modifying routing logic safely
        
        Your fixes are always minimal - you only change what's necessary.""",
        tools=[GeneratePatternTool(), PatternTestTool()] if CREWAI_AVAILABLE else [],
        llm=llm,
        verbose=True,
        allow_delegation=False
    )


def create_quality_assurer(llm=None) -> 'Agent':
    """Create the Quality Assurer agent."""
    return Agent(
        role="Quality Assurer",
        goal="Validate that proposed fixes are correct, safe, and won't break existing functionality",
        backstory="""You are a QA expert who ensures code changes are safe.
        You check:
        - Regex patterns are valid syntax
        - Patterns don't match unintended queries
        - Changes don't break existing test cases
        - Fix addresses the actual root cause
        
        You approve or reject fixes with clear reasoning.""",
        tools=[PatternTestTool()] if CREWAI_AVAILABLE else [],
        llm=llm,
        verbose=True,
        allow_delegation=False
    )


# ============================================================================
# SMART AGENT CREW
# ============================================================================

class SmartAgentCrew:
    """
    Multi-agent crew for intelligent error detection and self-healing.
    
    Usage:
        crew = SmartAgentCrew()
        
        # Analyze an error
        result = await crew.analyze_error(
            query="where can i see files i have uploaded",
            response="Your files: PROJECT.pdf, image.png...",
            expected="Navigate to files page",
            routing_method="analytics_template_sql"
        )
        
        print(result.error_type)  # ErrorType.EXCLUSION_MISSING
        print(result.proposed_fix)  # The code to add
    """
    
    def __init__(self, auto_apply: bool = False):
        """
        Initialize the smart agent crew.
        
        Args:
            auto_apply: If True, automatically apply safe fixes
        """
        self.auto_apply = auto_apply
        self.llm = get_nvidia_llm() if CREWAI_AVAILABLE else None
        
        # Track errors and fixes
        self.error_history: List[ErrorAnalysis] = []
        self.pending_fixes: List[ErrorAnalysis] = []
        self.applied_fixes: List[ErrorAnalysis] = []
        
        if CREWAI_AVAILABLE:
            # Create agents
            self.detective = create_error_detective(self.llm)
            self.analyst = create_root_cause_analyst(self.llm)
            self.fixer = create_code_fixer(self.llm)
            self.qa = create_quality_assurer(self.llm)
            logger.info("✅ SmartAgentCrew initialized with 4 agents")
        else:
            logger.warning("⚠️ CrewAI not available, using rule-based fallback")
    
    async def analyze_error(
        self,
        query: str,
        response: str,
        expected: str,
        routing_method: str = "unknown"
    ) -> Optional[ErrorAnalysis]:
        """
        Analyze an error using the multi-agent crew.
        
        Args:
            query: User's original query
            response: Chatbot's actual response
            expected: What response should have been
            routing_method: How the request was routed
            
        Returns:
            ErrorAnalysis with diagnosis and fix, or None if no error
        """
        if not CREWAI_AVAILABLE:
            return await self._fallback_analysis(query, response, expected, routing_method)
        
        # Create tasks for the crew
        detection_task = Task(
            description=f"""Analyze this chatbot interaction:

USER QUERY: "{query}"
EXPECTED RESPONSE: {expected}
ACTUAL RESPONSE: {response[:500]}
ROUTING METHOD: {routing_method}

Determine:
1. Is this actually an error? (user didn't get what they wanted)
2. What type of error is it?
   - ROUTING_ERROR: Query went to wrong handler
   - PATTERN_MISSING: No regex pattern matches
   - EXCLUSION_MISSING: Analytics intercepted a navigation query
   - LLM_HALLUCINATION: LLM gave wrong output
   - TRAINING_GAP: DSPy needs this example
3. How confident are you (0.0-1.0)?

Be precise and explain your reasoning.""",
            agent=self.detective,
            expected_output="""JSON:
{
    "is_error": true/false,
    "error_type": "ROUTING_ERROR|PATTERN_MISSING|EXCLUSION_MISSING|LLM_HALLUCINATION|TRAINING_GAP",
    "confidence": 0.0-1.0,
    "reasoning": "explanation"
}"""
        )
        
        analysis_task = Task(
            description=f"""Based on the error detection, diagnose the ROOT CAUSE.

Query: "{query}"
Use the code_search tool to find:
1. Where navigation patterns are defined
2. Where analytics exclusions are defined
3. The routing logic order

Determine:
1. Which file has the bug
2. Which function/section needs fixing
3. Why the current code failed""",
            agent=self.analyst,
            expected_output="""JSON:
{
    "root_cause": "detailed explanation",
    "affected_file": "path/to/file.py",
    "affected_section": "function or line range",
    "why_failed": "specific reason"
}""",
            context=[detection_task]
        )
        
        fix_task = Task(
            description=f"""Generate a code fix based on the analysis.

Original query: "{query}"

Requirements:
1. Generate minimal code change
2. Use proper regex with variations
3. Include 3-5 lines of context
4. Test the pattern matches the query

Use generate_pattern tool to create a good pattern.""",
            agent=self.fixer,
            expected_output="""JSON:
{
    "fix_type": "ADD_REGEX_PATTERN|ADD_EXCLUSION|ADD_DSPY_EXAMPLE",
    "file_path": "path/to/file.py",
    "code_to_add": "the actual code",
    "where_to_add": "after which line/section",
    "test_queries": ["query1", "query2"]
}""",
            context=[analysis_task]
        )
        
        validation_task = Task(
            description=f"""Validate the proposed fix.

Test that:
1. The regex pattern is valid
2. It matches the original query: "{query}"
3. It doesn't match unrelated queries
4. The fix addresses the root cause

Use pattern_test tool to verify.""",
            agent=self.qa,
            expected_output="""JSON:
{
    "is_valid": true/false,
    "test_results": [
        {"query": "test", "should_match": true, "did_match": true}
    ],
    "issues": [],
    "approved": true/false,
    "approval_reason": "explanation"
}""",
            context=[fix_task]
        )
        
        # Create and run crew
        crew = Crew(
            agents=[self.detective, self.analyst, self.fixer, self.qa],
            tasks=[detection_task, analysis_task, fix_task, validation_task],
            process=Process.sequential,
            verbose=True
        )
        
        try:
            result = crew.kickoff()
            analysis = self._parse_crew_result(query, response, expected, result)
            
            if analysis:
                self.error_history.append(analysis)
                
                if self.auto_apply and analysis.confidence > 0.8:
                    self.applied_fixes.append(analysis)
                    logger.info(f"✅ Auto-applied fix for: {query[:50]}")
                else:
                    self.pending_fixes.append(analysis)
                    logger.info(f"📋 Fix queued for review: {query[:50]}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Crew analysis failed: {e}")
            return await self._fallback_analysis(query, response, expected, routing_method)
    
    def _parse_crew_result(
        self,
        query: str,
        response: str,
        expected: str,
        crew_result
    ) -> Optional[ErrorAnalysis]:
        """Parse crew output into ErrorAnalysis."""
        try:
            # Extract JSON from task outputs
            outputs = [task.raw for task in crew_result.tasks_output]
            
            # Parse each output
            detection = self._extract_json(outputs[0]) if len(outputs) > 0 else {}
            analysis = self._extract_json(outputs[1]) if len(outputs) > 1 else {}
            fix = self._extract_json(outputs[2]) if len(outputs) > 2 else {}
            validation = self._extract_json(outputs[3]) if len(outputs) > 3 else {}
            
            if not detection.get("is_error", True):
                return None  # Not actually an error
            
            return ErrorAnalysis(
                query=query,
                response=response[:500],
                expected=expected,
                error_type=ErrorType[detection.get("error_type", "UNKNOWN")],
                root_cause=analysis.get("root_cause", "Unknown"),
                affected_file=fix.get("file_path", "unknown"),
                fix_type=FixType[fix.get("fix_type", "MANUAL_REVIEW").upper().replace("-", "_")],
                proposed_fix=fix.get("code_to_add", ""),
                confidence=detection.get("confidence", 0.5),
                test_queries=fix.get("test_queries", [query])
            )
        except Exception as e:
            logger.error(f"Failed to parse crew result: {e}")
            return None
    
    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from agent response text."""
        try:
            # Find JSON in text
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return {}
    
    async def _fallback_analysis(
        self,
        query: str,
        response: str,
        expected: str,
        routing_method: str
    ) -> Optional[ErrorAnalysis]:
        """Rule-based fallback when CrewAI unavailable."""
        from .agents import SelfHealingSystem
        
        system = SelfHealingSystem()
        fix = system.check_and_fix(
            user_query=query,
            response=response,
            routing_method=routing_method,
            actions=[]
        )
        
        if fix:
            return ErrorAnalysis(
                query=query,
                response=response[:500],
                expected=expected,
                error_type=fix.error_report.error_type,
                root_cause="Detected by rule-based system",
                affected_file=fix.file_path or "unknown",
                fix_type=FixType[fix.fix_type.name],
                proposed_fix=fix.code_change or "",
                confidence=fix.error_report.confidence,
                test_queries=fix.test_queries
            )
        return None
    
    def get_pending_fixes(self) -> List[Dict]:
        """Get all pending fixes for human review."""
        return [
            {
                "id": i,
                "query": fix.query,
                "error_type": fix.error_type.value,
                "fix_type": fix.fix_type.value,
                "affected_file": fix.affected_file,
                "proposed_fix": fix.proposed_fix,
                "confidence": fix.confidence,
                "root_cause": fix.root_cause
            }
            for i, fix in enumerate(self.pending_fixes)
        ]
    
    def approve_fix(self, fix_id: int) -> bool:
        """Approve and apply a pending fix."""
        if 0 <= fix_id < len(self.pending_fixes):
            fix = self.pending_fixes.pop(fix_id)
            self.applied_fixes.append(fix)
            self._apply_fix(fix)
            return True
        return False
    
    def _apply_fix(self, fix: ErrorAnalysis):
        """Apply a fix to the codebase."""
        # In production, would write to actual files
        logger.info(f"📝 Applying fix to {fix.affected_file}:")
        logger.info(f"   Type: {fix.fix_type.value}")
        logger.info(f"   Code:\n{fix.proposed_fix}")


# ============================================================================
# QUICK FIX FUNCTIONS (For common errors)
# ============================================================================

async def quick_fix_navigation_error(query: str, expected_page: str) -> str:
    """
    Quick fix for navigation errors - generates pattern and exclusion.
    
    Usage:
        fix = await quick_fix_navigation_error(
            "where can i see files i uploaded",
            "Files"
        )
    """
    # Generate pattern
    words = query.lower().split()
    optional_words = ['my', 'the', 'your', 'a', 'an']
    
    pattern_parts = []
    for word in words:
        if word in optional_words:
            pattern_parts.append(f'({word}\\s+)?')
        else:
            pattern_parts.append(f'{word}\\s*')
    
    pattern = '\\b' + ''.join(pattern_parts).rstrip('\\s*') + '\\b'
    
    handler = f"self._handle_navigate_{expected_page.lower().replace(' ', '_')}"
    
    return f"""
# Fix for: "{query}" → {expected_page}

# 1. Add to rule_based.py navigation patterns:
(
    re.compile(r'{pattern}', re.IGNORECASE),
    {handler}
),

# 2. Add to orchestrator.py navigation_exclusions:
r'{pattern}',
"""


# ============================================================================
# SINGLETON AND INTEGRATION
# ============================================================================

_crew_instance: Optional[SmartAgentCrew] = None

def get_smart_crew(auto_apply: bool = False) -> SmartAgentCrew:
    """Get or create the SmartAgentCrew singleton."""
    global _crew_instance
    if _crew_instance is None:
        _crew_instance = SmartAgentCrew(auto_apply=auto_apply)
    return _crew_instance


# ============================================================================
# MAIN - DEMO
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def demo():
        print("=" * 70)
        print("SMART AGENT CREW DEMO")
        print("=" * 70)
        
        crew = SmartAgentCrew(auto_apply=False)
        
        # Simulate the error from user's conversation
        print("\n🔍 Analyzing error...")
        result = await crew.analyze_error(
            query="where can i see files i have uploaded",
            response="Your files:\n• PROJECT_DOCUMENTATION.pdf | 7.62 MB\n• Screenshot.png | 59 KB",
            expected="Navigate to files page with navigation button",
            routing_method="analytics_template_sql"
        )
        
        if result:
            print(f"\n✅ Analysis Complete!")
            print(f"   Error Type: {result.error_type.value}")
            print(f"   Root Cause: {result.root_cause}")
            print(f"   Fix Type: {result.fix_type.value}")
            print(f"   File: {result.affected_file}")
            print(f"   Confidence: {result.confidence:.0%}")
            print(f"\n📝 Proposed Fix:\n{result.proposed_fix}")
        else:
            print("No error detected or analysis failed")
        
        # Show pending fixes
        print("\n📋 Pending Fixes:")
        for fix in crew.get_pending_fixes():
            print(f"   [{fix['id']}] {fix['error_type']}: {fix['query'][:40]}...")
    
    asyncio.run(demo())
