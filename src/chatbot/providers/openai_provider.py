"""
OpenAI Provider - GPT-4 and GPT-3.5 integration
"""

import time
from typing import List, Dict, Any, Optional
import logging

from .base import (
    LLMProvider, ChatMessage, ChatResponse, ChatAction,
    ActionType, UserContext, MessageRole
)
from ..config import chatbot_config

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI-based LLM provider using GPT models."""
    
    def __init__(self):
        self._client = None
        self._async_client = None
    
    @property
    def name(self) -> str:
        return "openai"
    
    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=chatbot_config.openai_api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._client
    
    async def _get_async_client(self):
        """Lazy initialization of async OpenAI client."""
        if self._async_client is None:
            try:
                from openai import AsyncOpenAI
                self._async_client = AsyncOpenAI(api_key=chatbot_config.openai_api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._async_client
    
    async def chat(
        self,
        message: str,
        history: List[ChatMessage],
        user_context: UserContext,
        system_prompt: str
    ) -> ChatResponse:
        """Process chat message using OpenAI API."""
        start_time = time.time()
        
        try:
            client = await self._get_async_client()
            
            # Build messages array
            messages = self._build_messages(message, history, user_context, system_prompt)
            
            # Call OpenAI API
            response = await client.chat.completions.create(
                model=chatbot_config.openai_model,
                messages=messages,
                max_tokens=chatbot_config.openai_max_tokens,
                temperature=chatbot_config.openai_temperature,
            )
            
            # Extract response
            response_text = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else None
            
            # Parse actions from response
            actions = self._parse_actions(response_text)
            clean_message = self._clean_response(response_text)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(clean_message, user_context)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return ChatResponse(
                message=clean_message,
                actions=actions,
                suggestions=suggestions,
                provider=self.name,
                processing_time_ms=processing_time,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            processing_time = int((time.time() - start_time) * 1000)
            
            return ChatResponse(
                message=f"I apologize, but I encountered an error processing your request. Please try again.",
                actions=[ChatAction(type=ActionType.ERROR, payload={"error": str(e)})],
                suggestions=["Try again", "Help"],
                provider=self.name,
                processing_time_ms=processing_time
            )
    
    def _build_messages(
        self,
        message: str,
        history: List[ChatMessage],
        user_context: UserContext,
        system_prompt: str
    ) -> List[Dict[str, str]]:
        """Build the messages array for OpenAI API."""
        messages = []
        
        # System prompt with user context
        full_system_prompt = f"{system_prompt}\n\n{user_context.to_prompt_context()}"
        messages.append({
            "role": "system",
            "content": full_system_prompt
        })
        
        # Add conversation history
        for msg in history[-chatbot_config.max_history_length:]:
            messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": message
        })
        
        return messages
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if OpenAI API is accessible."""
        try:
            client = await self._get_async_client()
            
            # Simple models list call to check connectivity
            models = await client.models.list()
            
            return {
                "status": "healthy",
                "provider": self.name,
                "model": chatbot_config.openai_model,
                "api_accessible": True
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.name,
                "error": str(e),
                "api_accessible": False
            }


class OpenAIFunctionCallingProvider(OpenAIProvider):
    """
    Extended OpenAI provider with function calling support.
    
    This enables more structured interactions where the AI can call
    defined functions for navigation, file operations, etc.
    """
    
    def __init__(self):
        super().__init__()
        self._tools = self._define_tools()
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define available tools for function calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "navigate_to_page",
                    "description": "Navigate the user to a specific page in the application",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "The page path to navigate to",
                                "enum": [
                                    "/dashboard",
                                    "/dashboard/files",
                                    "/dashboard/all-files",
                                    "/dashboard/users",
                                    "/dashboard/settings",
                                    "/dashboard/approvals",
                                    "/dashboard/organizations"
                                ]
                            },
                            "reason": {
                                "type": "string",
                                "description": "Brief explanation of why navigating here"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_files",
                    "description": "Search for files by name or type",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for file name"
                            },
                            "file_type": {
                                "type": "string",
                                "description": "Filter by file type (pdf, docx, xlsx, etc.)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_file_info",
                    "description": "Get information about a specific file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_id": {
                                "type": "string",
                                "description": "The ID of the file"
                            }
                        },
                        "required": ["file_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_recent_files",
                    "description": "List the user's most recent files",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of files to return",
                                "default": 5
                            }
                        }
                    }
                }
            }
        ]
    
    async def chat(
        self,
        message: str,
        history: List[ChatMessage],
        user_context: UserContext,
        system_prompt: str
    ) -> ChatResponse:
        """Process chat with function calling support."""
        start_time = time.time()
        
        try:
            client = await self._get_async_client()
            messages = self._build_messages(message, history, user_context, system_prompt)
            
            # First call with tools
            response = await client.chat.completions.create(
                model=chatbot_config.openai_model,
                messages=messages,
                tools=self._tools,
                tool_choice="auto",
                max_tokens=chatbot_config.openai_max_tokens,
                temperature=chatbot_config.openai_temperature,
            )
            
            response_message = response.choices[0].message
            actions = []
            
            # Check if the model wants to call a function
            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = eval(tool_call.function.arguments)
                    
                    action = self._tool_call_to_action(function_name, function_args)
                    if action:
                        actions.append(action)
            
            response_text = response_message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else None
            
            # Also parse any inline actions
            inline_actions = self._parse_actions(response_text)
            actions.extend(inline_actions)
            
            clean_message = self._clean_response(response_text)
            suggestions = self._generate_suggestions(clean_message, user_context)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return ChatResponse(
                message=clean_message,
                actions=actions,
                suggestions=suggestions,
                provider=f"{self.name}-functions",
                processing_time_ms=processing_time,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            logger.error(f"OpenAI Function Calling error: {str(e)}")
            # Fall back to base provider
            return await super().chat(message, history, user_context, system_prompt)
    
    def _tool_call_to_action(self, function_name: str, args: Dict[str, Any]) -> Optional[ChatAction]:
        """Convert a tool call to a ChatAction."""
        if function_name == "navigate_to_page":
            return ChatAction(
                type=ActionType.NAVIGATE,
                payload={"path": args.get("path")},
                description=args.get("reason", f"Navigate to {args.get('path')}")
            )
        elif function_name == "search_files":
            return ChatAction(
                type=ActionType.EXECUTE,
                payload={"action": "search_files", "params": args},
                description=f"Search files: {args.get('query', '')}"
            )
        elif function_name == "get_file_info":
            return ChatAction(
                type=ActionType.EXECUTE,
                payload={"action": "get_file_info", "params": args},
                description="Get file information"
            )
        elif function_name == "list_recent_files":
            return ChatAction(
                type=ActionType.EXECUTE,
                payload={"action": "list_recent_files", "params": args},
                description="List recent files"
            )
        return None
