"""
CrewAI-Powered Self-Healing System
===================================

This version uses CrewAI to create intelligent agents that can:
1. Understand complex error patterns
2. Reason about root causes
3. Generate better fixes

WHEN TO USE CREWAI vs RULE-BASED:
- Rule-based (agents.py): Fast, deterministic, for known error patterns
- CrewAI (this file): For complex/unknown errors that need reasoning

CREW ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────┐
│                      CHATBOT ERROR CREW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   ANALYST    │───▶│  DEVELOPER   │───▶│   TESTER     │      │
│  │    Agent     │    │    Agent     │    │    Agent     │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│        │                    │                   │               │
│        ▼                    ▼                   ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Analyze     │    │  Generate    │    │  Validate    │      │
│  │  Error       │    │  Fix Code    │    │  Fix Works   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

INSTALLATION:
    pip install crewai crewai-tools langchain-nvidia-ai-endpoints
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Check if CrewAI is installed
try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import BaseTool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    logger.warning("CrewAI not installed. Run: pip install crewai")


@dataclass
class ErrorContext:
    """Full context about an error for crew analysis."""
    user_query: str
    response: str
    routing_method: str
    expected_behavior: str
    actual_behavior: str
    relevant_code_snippets: Dict[str, str]


class CodeSearchTool(BaseTool if CREWAI_AVAILABLE else object):
    """Tool for agents to search codebase for relevant patterns."""
    
    name: str = "code_search"
    description: str = "Search the codebase for patterns, functions, or classes. Input should be a search term."
    
    def _run(self, search_term: str) -> str:
        """Search for code patterns."""
        # In production, would use grep or AST parsing
        results = []
        
        # Simulated search results
        if "pattern" in search_term.lower() or "regex" in search_term.lower():
            results.append("Found in rule_based.py: Navigation patterns at line 488-520")
        if "analytics" in search_term.lower() or "exclusion" in search_term.lower():
            results.append("Found in orchestrator.py: navigation_exclusions at line 765-780")
        if "routing" in search_term.lower():
            results.append("Found in orchestrator.py: _should_use_analytics() at line 754")
        
        return "\n".join(results) if results else "No matches found"


class PatternTestTool(BaseTool if CREWAI_AVAILABLE else object):
    """Tool for agents to test regex patterns."""
    
    name: str = "pattern_test"
    description: str = "Test if a regex pattern matches a query. Input format: 'PATTERN|||QUERY'"
    
    def _run(self, input_str: str) -> str:
        """Test a pattern against a query."""
        import re
        try:
            pattern, query = input_str.split("|||")
            match = re.search(pattern.strip(), query.strip(), re.IGNORECASE)
            return f"Match: {bool(match)}" + (f" - Matched: '{match.group()}'" if match else "")
        except Exception as e:
            return f"Error: {e}"


def create_error_analysis_crew(error_context: ErrorContext, llm_config: Dict = None):
    """
    Create a CrewAI crew to analyze and fix chatbot errors.
    
    Args:
        error_context: Full context about the error
        llm_config: Optional LLM configuration (uses NVIDIA by default)
    
    Returns:
        Crew ready to execute
    """
    if not CREWAI_AVAILABLE:
        raise ImportError("CrewAI not installed. Run: pip install crewai")
    
    # Default to NVIDIA LLM
    llm = llm_config or {
        "provider": "nvidia",
        "model": "nvidia/llama-3.1-nemotron-70b-instruct",
        "api_key": os.getenv("NVIDIA_API_KEY")
    }
    
    # =========================================================================
    # AGENT DEFINITIONS
    # =========================================================================
    
    analyst_agent = Agent(
        role="Error Analyst",
        goal="Analyze chatbot errors to determine the exact root cause",
        backstory="""You are an expert at debugging AI chatbots. You understand:
        - Pattern matching and regex
        - Intent classification
        - Routing logic
        - The difference between LLM errors and code errors
        
        You can quickly identify whether an error is caused by:
        1. Missing regex patterns (code issue)
        2. Wrong routing order (code issue)
        3. LLM hallucination (model issue)
        4. Missing training data (data issue)
        """,
        tools=[CodeSearchTool(), PatternTestTool()],
        verbose=True,
        llm=llm
    )
    
    developer_agent = Agent(
        role="Fix Developer",
        goal="Generate precise code fixes for chatbot errors",
        backstory="""You are an expert Python developer who specializes in:
        - Writing regex patterns
        - Understanding chatbot routing logic
        - Writing clean, maintainable code
        
        You generate fixes that are:
        1. Minimal - only change what's needed
        2. General - work for variations of the query
        3. Safe - don't break existing functionality
        """,
        tools=[CodeSearchTool(), PatternTestTool()],
        verbose=True,
        llm=llm
    )
    
    tester_agent = Agent(
        role="Fix Tester",
        goal="Validate that proposed fixes work correctly and don't break anything",
        backstory="""You are a QA expert who:
        - Tests regex patterns against multiple inputs
        - Checks for edge cases
        - Ensures backward compatibility
        - Validates code syntax
        """,
        tools=[PatternTestTool()],
        verbose=True,
        llm=llm
    )
    
    # =========================================================================
    # TASK DEFINITIONS
    # =========================================================================
    
    analysis_task = Task(
        description=f"""Analyze this chatbot error:

USER QUERY: {error_context.user_query}
EXPECTED: {error_context.expected_behavior}
ACTUAL: {error_context.actual_behavior}
ROUTING: {error_context.routing_method}

RESPONSE RECEIVED:
{error_context.response[:500]}

Determine:
1. What type of error this is (routing, pattern, LLM, training)
2. Which file needs to be fixed
3. What exactly went wrong
4. Why the current code didn't handle this correctly

Use the code_search tool to find relevant code sections.
""",
        agent=analyst_agent,
        expected_output="""A JSON object with:
{
    "error_type": "routing_error|pattern_missing|llm_error|training_gap",
    "root_cause": "detailed explanation",
    "affected_file": "path/to/file.py",
    "affected_function": "function_name",
    "why_current_code_failed": "explanation"
}"""
    )
    
    fix_task = Task(
        description="""Based on the analysis, generate the exact code fix needed.

Requirements:
1. Generate the minimal code change
2. Include 3-5 lines of context before and after
3. Make the pattern general enough to catch variations
4. Follow existing code style

Use the pattern_test tool to verify your patterns work.
""",
        agent=developer_agent,
        expected_output="""A JSON object with:
{
    "file_path": "path/to/file.py",
    "fix_type": "add_pattern|add_exclusion|reorder|add_training",
    "old_code": "the code section to find (with context)",
    "new_code": "the replacement code",
    "explanation": "why this fix works"
}""",
        context=[analysis_task]
    )
    
    validation_task = Task(
        description=f"""Validate the proposed fix:

1. Test the new pattern against the original query: "{error_context.user_query}"
2. Test against variations (different words, typos)
3. Ensure it doesn't match queries it shouldn't
4. Verify the code syntax is valid

Use the pattern_test tool to check matches.
""",
        agent=tester_agent,
        expected_output="""A JSON object with:
{
    "is_valid": true|false,
    "test_results": [
        {"query": "test query", "should_match": true, "did_match": true}
    ],
    "issues": ["list of any issues found"],
    "approved": true|false
}""",
        context=[fix_task]
    )
    
    # =========================================================================
    # CREATE CREW
    # =========================================================================
    
    crew = Crew(
        agents=[analyst_agent, developer_agent, tester_agent],
        tasks=[analysis_task, fix_task, validation_task],
        process=Process.sequential,  # Tasks run in order
        verbose=True
    )
    
    return crew


class CrewAISelfHealer:
    """
    Self-healing system powered by CrewAI.
    
    Use this for complex errors that the rule-based system can't handle.
    
    Usage:
        healer = CrewAISelfHealer()
        
        # Analyze and fix an error
        result = healer.analyze_and_fix(
            user_query="where can i see files i have uploaded",
            response="Your files: ...",
            routing_method="analytics_template_sql",
            expected="navigation to files page",
            actual="listed files instead of navigating"
        )
        
        print(result['fix'])
    """
    
    def __init__(self, auto_apply: bool = False):
        self.auto_apply = auto_apply
        self.fix_history: List[Dict] = []
        
        if not CREWAI_AVAILABLE:
            logger.warning("CrewAI not available. Using rule-based fallback.")
    
    def analyze_and_fix(
        self,
        user_query: str,
        response: str,
        routing_method: str,
        expected: str,
        actual: str
    ) -> Dict[str, Any]:
        """
        Use CrewAI to analyze error and generate fix.
        
        Returns dict with analysis, fix, and validation results.
        """
        if not CREWAI_AVAILABLE:
            return self._fallback_analysis(user_query, response, routing_method)
        
        # Build context
        context = ErrorContext(
            user_query=user_query,
            response=response,
            routing_method=routing_method,
            expected_behavior=expected,
            actual_behavior=actual,
            relevant_code_snippets={}
        )
        
        # Create and run crew
        try:
            crew = create_error_analysis_crew(context)
            result = crew.kickoff()
            
            # Parse results
            parsed = self._parse_crew_output(result)
            
            # Store in history
            self.fix_history.append({
                'query': user_query,
                'result': parsed,
                'applied': False
            })
            
            return parsed
            
        except Exception as e:
            logger.error(f"CrewAI analysis failed: {e}")
            return self._fallback_analysis(user_query, response, routing_method)
    
    def _parse_crew_output(self, crew_result) -> Dict[str, Any]:
        """Parse the structured output from crew tasks."""
        # CrewAI returns task outputs
        # Parse JSON from each agent's response
        try:
            return {
                'analysis': json.loads(crew_result.tasks_output[0].raw),
                'fix': json.loads(crew_result.tasks_output[1].raw),
                'validation': json.loads(crew_result.tasks_output[2].raw)
            }
        except (json.JSONDecodeError, IndexError, AttributeError):
            # Return raw if can't parse
            return {
                'raw_output': str(crew_result),
                'parse_error': True
            }
    
    def _fallback_analysis(self, query: str, response: str, routing: str) -> Dict:
        """Rule-based fallback when CrewAI is unavailable."""
        from .agents import SelfHealingSystem
        
        system = SelfHealingSystem()
        fix = system.check_and_fix(query, response, routing, [])
        
        if fix:
            return {
                'analysis': {
                    'error_type': fix.error_report.error_type.value,
                    'root_cause': 'Detected by rule-based system'
                },
                'fix': {
                    'file_path': fix.file_path,
                    'fix_type': fix.fix_type.value,
                    'new_code': fix.code_change
                },
                'validation': {
                    'is_valid': True,
                    'approved': fix.auto_apply
                }
            }
        return {'error': 'No fix generated'}


# ============================================================================
# INTEGRATION EXAMPLE
# ============================================================================

def integrate_crewai_healing():
    """
    How to integrate CrewAI self-healing into the chatbot.
    
    Add to orchestrator.py:
    
    ```python
    from chatbot.self_healing.crewai_agents import CrewAISelfHealer
    
    # Initialize once
    self.healer = CrewAISelfHealer(auto_apply=False)
    
    # In chat() method, after response:
    if user_reported_error or response_seems_wrong:
        fix_result = self.healer.analyze_and_fix(
            user_query=message,
            response=response.message,
            routing_method=routing_method,
            expected="what user wanted",
            actual="what they got"
        )
        
        # Log for review
        logger.info(f"CrewAI fix: {fix_result}")
    ```
    """
    pass


# ============================================================================
# ADMIN ENDPOINTS FOR FIX MANAGEMENT
# ============================================================================

def get_pending_fixes_endpoint():
    """
    FastAPI endpoint example for managing fixes.
    
    Add to routes/chatbot.py:
    
    ```python
    @router.get("/self-heal/pending")
    async def get_pending_fixes(
        user: AuthenticatedUser = Depends(require_super_admin)
    ):
        healer = get_self_healer()  # Singleton
        return {
            "pending_fixes": healer.get_pending_fixes(),
            "applied_count": len(healer.applied_fixes)
        }
    
    @router.post("/self-heal/approve/{fix_id}")
    async def approve_fix(
        fix_id: int,
        user: AuthenticatedUser = Depends(require_super_admin)
    ):
        healer = get_self_healer()
        success = healer.approve_fix(fix_id)
        return {"approved": success}
    ```
    """
    pass


if __name__ == "__main__":
    print("=" * 70)
    print("CREWAI SELF-HEALING DEMO")
    print("=" * 70)
    
    if CREWAI_AVAILABLE:
        print("✅ CrewAI is available")
        
        healer = CrewAISelfHealer()
        result = healer.analyze_and_fix(
            user_query="where can i see files i have uploaded",
            response="Your files:\n• PROJECT_DOCUMENTATION.pdf | 7.62 MB",
            routing_method="analytics_template_sql",
            expected="Navigate to files page with navigation action",
            actual="Listed files without navigation button"
        )
        
        print("\n📊 Analysis Result:")
        print(json.dumps(result, indent=2))
    else:
        print("❌ CrewAI not installed")
        print("   Run: pip install crewai crewai-tools")
        print("\n   Using rule-based fallback instead...")
        
        from .agents import SelfHealingSystem
        system = SelfHealingSystem()
        fix = system.check_and_fix(
            user_query="where can i see files i have uploaded",
            response="Your files:\n• PROJECT_DOCUMENTATION.pdf | 7.62 MB",
            routing_method="analytics_template_sql",
            actions=[]
        )
        
        if fix:
            print(f"\n✅ Fix proposed: {fix.description}")
