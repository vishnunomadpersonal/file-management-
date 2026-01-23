"""
Agentic Orchestrator - GPT-4o as the Intelligent Brain
=======================================================

ARCHITECTURE:
Instead of pattern matching → handler, we have:
    Query → GPT-4o Brain → Tools → Response

The "Brain" (GPT-4o) decides:
1. What tools to call
2. In what order
3. How to combine results
4. When to ask for clarification

TOOLS AVAILABLE TO THE BRAIN:
- sql_query: Run text-to-SQL queries
- navigate: Navigate to pages
- file_operation: Perform file actions
- user_info: Get user information
- reflect: Self-check response quality

This is the FUTURE of chatbot architecture - let the LLM orchestrate.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

@dataclass
class Tool:
    """A tool that the agent can use."""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., Awaitable[Dict[str, Any]]]


@dataclass  
class ToolCall:
    """A tool call made by the agent."""
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class AgentResponse:
    """Complete response from the agent."""
    message: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 1.0
    latency_ms: float = 0.0
    tokens_used: int = 0


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

class AgentTools:
    """
    All tools available to the agentic orchestrator.
    Each tool is a capability the agent can invoke.
    """
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self._sql_agent = None
    
    async def _get_sql_agent(self):
        """Lazy load SQL agent."""
        if self._sql_agent is None:
            try:
                from .text_to_sql_langchain import LangChainSQLAgent
                self._sql_agent = LangChainSQLAgent()
            except Exception as e:
                logger.error(f"Failed to load SQL agent: {e}")
        return self._sql_agent
    
    # ===== SQL QUERY TOOL =====
    async def sql_query(self, question: str, user_role: str = "user") -> Dict[str, Any]:
        """
        Execute a text-to-SQL query.
        
        Args:
            question: Natural language question about data
            user_role: User's role for access control
        
        Returns:
            Query results with formatted answer
        """
        agent = await self._get_sql_agent()
        if not agent:
            return {"error": "SQL agent not available", "success": False}
        
        user_info = {"role": user_role, "organization_id": None, "user_id": "1"}
        result = await agent.ask(question, user_info)
        
        return {
            "success": result.get("success", False),
            "answer": result.get("answer", ""),
            "query": result.get("query", ""),
            "row_count": result.get("row_count", 0)
        }
    
    # ===== NAVIGATION TOOL =====
    async def navigate(self, destination: str) -> Dict[str, Any]:
        """
        Generate navigation action.
        
        Args:
            destination: Where to navigate (files, dashboard, settings, etc.)
        
        Returns:
            Navigation path and confirmation
        """
        NAVIGATION_MAP = {
            "files": "/dashboard/files",
            "documents": "/dashboard/files",
            "my files": "/dashboard/files",
            "dashboard": "/dashboard",
            "home": "/dashboard",
            "settings": "/dashboard/settings",
            "preferences": "/dashboard/settings",
            "quarantine": "/dashboard/quarantine",
            "quarantined": "/dashboard/quarantine",
            "users": "/dashboard/users",
            "user management": "/dashboard/users",
            "organizations": "/dashboard/organizations",
            "profile": "/dashboard/profile",
            "upload": "/dashboard/files/upload",
        }
        
        dest_lower = destination.lower().strip()
        path = NAVIGATION_MAP.get(dest_lower)
        
        if path:
            return {
                "success": True,
                "action": "navigate",
                "path": path,
                "message": f"Taking you to {destination}."
            }
        else:
            return {
                "success": False,
                "error": f"Unknown destination: {destination}",
                "available": list(NAVIGATION_MAP.keys())
            }
    
    # ===== USER INFO TOOL =====
    async def get_user_info(self, query_type: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about users.
        
        Args:
            query_type: Type of info (current_user, user_by_id, permissions)
            user_id: Optional user ID to look up
        
        Returns:
            User information
        """
        # Placeholder - would connect to actual user service
        if query_type == "current_user":
            return {
                "success": True,
                "user": {
                    "id": "1",
                    "name": "Super Admin",
                    "email": "admin@filemanager.com",
                    "role": "super_admin"
                }
            }
        elif query_type == "permissions":
            return {
                "success": True,
                "permissions": ["read", "write", "delete", "admin"]
            }
        else:
            return {"success": False, "error": f"Unknown query type: {query_type}"}
    
    # ===== HELP TOOL =====
    async def get_help(self, topic: Optional[str] = None) -> Dict[str, Any]:
        """
        Get help information.
        
        Args:
            topic: Optional specific topic to get help on
        
        Returns:
            Help text and suggestions
        """
        general_help = """
I can help you with:

📁 **File Management**
- "Show me my files" - Navigate to files
- "How many files do I have" - Count your files
- "Files larger than 1MB" - Find large files

📊 **Analytics**
- "Who uploaded the most files" - User rankings
- "Storage usage per organization" - Storage reports
- "Files uploaded in December 2025" - Time-based queries

👥 **User Management**
- "List all users" - View users
- "Pending approvals" - Users waiting for approval

⚙️ **Navigation**
- "Go to settings" - Navigate to settings
- "Open dashboard" - Go to dashboard

Just ask me anything in natural language!
"""
        
        return {
            "success": True,
            "help_text": general_help,
            "suggestions": [
                "Show me my files",
                "How many files do we have?",
                "Who uploaded the most files?",
                "Go to settings"
            ]
        }
    
    # ===== REFLECT TOOL (Self-check) =====
    async def reflect(self, response: str, query: str) -> Dict[str, Any]:
        """
        Self-reflect on response quality.
        
        Args:
            response: The generated response
            query: The original query
        
        Returns:
            Quality assessment and suggestions
        """
        issues = []
        confidence = 1.0
        
        # Check for common issues
        if "error" in response.lower():
            issues.append("Response contains error message")
            confidence -= 0.2
        
        if len(response) < 20:
            issues.append("Response is very short")
            confidence -= 0.1
        
        if "I don't know" in response or "I'm not sure" in response:
            issues.append("Response indicates uncertainty")
            confidence -= 0.2
        
        return {
            "confidence": max(0.1, confidence),
            "issues": issues,
            "should_retry": len(issues) > 1
        }
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "sql_query",
                    "description": "Execute a text-to-SQL query to get data from the database. Use for questions about counts, lists, aggregations, comparisons, or any data-related questions.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The natural language question to convert to SQL and execute"
                            },
                            "user_role": {
                                "type": "string",
                                "description": "User role for access control",
                                "default": "user"
                            }
                        },
                        "required": ["question"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "navigate",
                    "description": "Navigate to a page in the application. Use when user wants to go somewhere.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "destination": {
                                "type": "string",
                                "description": "Where to navigate: files, dashboard, settings, quarantine, users, organizations, profile, upload"
                            }
                        },
                        "required": ["destination"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_help",
                    "description": "Get help information about what the assistant can do.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "Optional specific topic to get help on"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_user_info",
                    "description": "Get information about the current user or other users.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query_type": {
                                "type": "string",
                                "enum": ["current_user", "permissions", "user_by_id"],
                                "description": "What type of user information to retrieve"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "User ID to look up (only for user_by_id)"
                            }
                        },
                        "required": ["query_type"]
                    }
                }
            }
        ]


# ============================================================================
# AGENTIC ORCHESTRATOR
# ============================================================================

class AgenticOrchestrator:
    """
    GPT-4o powered agentic orchestrator.
    
    Instead of pattern matching, we let GPT-4o decide:
    1. What the user wants
    2. Which tools to call
    3. How to format the response
    
    This is more flexible and handles edge cases better.
    """
    
    SYSTEM_PROMPT = """You are an intelligent assistant for a file management system called FileVault.

## TOOLS AVAILABLE:
1. **sql_query** - For ANY data/analytics questions
2. **navigate** - ONLY for explicit navigation requests  
3. **get_help** - When user asks for help/commands
4. **get_user_info** - To get current user information

## CRITICAL DECISION FRAMEWORK:

### USE sql_query FOR:
- ANY question containing: users, files, count, how many, list, show me, give me, find
- Data requests: "give me users who...", "show me people that...", "find files where..."
- Counts & aggregations: "how many", "total", "average", "sum"
- Rankings: "who uploaded most", "top users", "largest files"
- Filtered lists: "users with less than X files", "approved users", "registered users"
- Organization queries: "which organization", "belong to", "their org"
- Comparisons: "compare", "between", "per user/org"
- Time-based: "uploaded in December", "files this week"
- Conditional: "users who...", "files that...", "people with..."

### USE navigate ONLY FOR:
- Explicit navigation: "go to", "take me to", "navigate to", "open"
- Direct page requests: "files page", "settings", "dashboard"
- Location questions: "where can I see my files" → navigate

### EXAMPLES (Study these carefully):
| User Query | Tool | Reasoning |
|-----------|------|-----------|
| "give me users registered and approved who uploaded less than 5 files and their organization" | sql_query | Data request with filters |
| "show me people who uploaded less than five files" | sql_query | Filtered user list |
| "users with more than 10 uploads and their storage" | sql_query | User data with conditions |
| "which organization do these users belong to" | sql_query | Organization relationship query |
| "who approved user20@gmail.com" | sql_query | Approval tracking query |
| "list approved users with less than 3 files" | sql_query | Filtered user list |
| "go to my files" | navigate | Explicit navigation request |
| "where can I see my files" | navigate | Location question |
| "take me to settings" | navigate | Explicit navigation |
| "how do I upload files" | get_help | Help request |

## KEY RULE:
If the query mentions ANY of these → **ALWAYS use sql_query**:
- "give me", "show me", "list", "find" + users/files/data
- Numbers or quantities ("less than 5", "more than 10")
- Conditions ("who", "that", "with", "where")
- "organization", "belong", "uploaded", "registered", "approved"

## AMBIGUOUS CASES (Always choose sql_query):
- "show me files" → sql_query (listing data, not navigation)
- "users who..." → sql_query (data query)
- "give me..." → sql_query (data request)

Format responses with markdown. Be helpful and accurate."""

    def __init__(self):
        self.tools = AgentTools()
        self.client = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize the orchestrator."""
        if self._initialized:
            return
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OpenAI API key not found")
            return
        
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=api_key)
            self._initialized = True
            logger.info("✅ Agentic Orchestrator initialized")
        except ImportError:
            logger.error("openai package not available")
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name."""
        tool_map = {
            "sql_query": self.tools.sql_query,
            "navigate": self.tools.navigate,
            "get_help": self.tools.get_help,
            "get_user_info": self.tools.get_user_info,
            "reflect": self.tools.reflect,
        }
        
        handler = tool_map.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            return await handler(**arguments)
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"error": str(e)}
    
    async def process(self, query: str, user_context: Optional[Dict] = None) -> AgentResponse:
        """
        Process a query using the agentic approach.
        
        GPT-4o decides which tools to call and how to respond.
        """
        import time
        start = time.time()
        
        if not self._initialized:
            await self.initialize()
        
        if not self.client:
            return AgentResponse(
                message="I'm sorry, but I'm not fully configured. Please try again later.",
                reasoning="OpenAI client not available"
            )
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ]
        
        tool_calls_made = []
        max_iterations = 3  # Prevent infinite loops
        
        for iteration in range(max_iterations):
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    tools=self.tools.get_tool_definitions(),
                    tool_choice="auto",
                    temperature=0,
                    max_tokens=1000
                )
                
                assistant_message = response.choices[0].message
                
                # Check if there are tool calls
                if assistant_message.tool_calls:
                    # Add assistant message to history
                    messages.append({
                        "role": "assistant",
                        "content": assistant_message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in assistant_message.tool_calls
                        ]
                    })
                    
                    # Execute each tool call
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)
                        
                        logger.info(f"🔧 Tool call: {tool_name}({arguments})")
                        
                        result = await self._execute_tool(tool_name, arguments)
                        
                        tool_calls_made.append(ToolCall(
                            tool_name=tool_name,
                            arguments=arguments,
                            result=result
                        ))
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result)
                        })
                    
                    # Continue to get final response
                    continue
                
                # No tool calls - we have the final response
                latency = (time.time() - start) * 1000
                
                return AgentResponse(
                    message=assistant_message.content or "I've completed your request.",
                    tool_calls=tool_calls_made,
                    reasoning=f"Used {len(tool_calls_made)} tool(s)",
                    confidence=0.95,
                    latency_ms=latency,
                    tokens_used=response.usage.total_tokens if response.usage else 0
                )
                
            except Exception as e:
                logger.error(f"Agent processing error: {e}")
                return AgentResponse(
                    message=f"I encountered an error: {str(e)}",
                    reasoning=str(e),
                    confidence=0.0
                )
        
        # Max iterations reached
        return AgentResponse(
            message="I took too many steps trying to answer. Please try rephrasing your question.",
            tool_calls=tool_calls_made,
            reasoning="Max iterations reached",
            confidence=0.5
        )


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_agentic_instance: Optional[AgenticOrchestrator] = None

def get_agentic_orchestrator() -> AgenticOrchestrator:
    """Get or create the agentic orchestrator singleton."""
    global _agentic_instance
    if _agentic_instance is None:
        _agentic_instance = AgenticOrchestrator()
    return _agentic_instance


async def agentic_process(query: str, user_context: Optional[Dict] = None) -> AgentResponse:
    """Convenience function for processing a query agentically."""
    orchestrator = get_agentic_orchestrator()
    return await orchestrator.process(query, user_context)


# ============================================================================
# TEST / DEMO
# ============================================================================

async def demo():
    """Demo the agentic orchestrator."""
    orchestrator = AgenticOrchestrator()
    await orchestrator.initialize()
    
    test_queries = [
        "where can I see my files",
        "how many files do we have",
        "who uploaded the most files in december 2025",
        "go to settings",
        "show me files larger than 1MB",
        "help",
        "users who never uploaded anything",
    ]
    
    print("=" * 70)
    print("AGENTIC ORCHESTRATOR DEMO")
    print("=" * 70)
    
    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"Q: {query}")
        print("-" * 70)
        
        response = await orchestrator.process(query)
        
        print(f"Tools used: {[tc.tool_name for tc in response.tool_calls]}")
        print(f"Latency: {response.latency_ms:.0f}ms")
        print(f"Tokens: {response.tokens_used}")
        print(f"\nResponse:\n{response.message[:500]}")


if __name__ == "__main__":
    asyncio.run(demo())
