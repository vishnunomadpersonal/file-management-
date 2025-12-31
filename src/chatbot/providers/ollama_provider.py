"""
Ollama Provider - Local LLM integration using Ollama
"""

import time
import httpx
from typing import List, Dict, Any
import logging
import json

from .base import (
    LLMProvider, ChatMessage, ChatResponse, ChatAction,
    ActionType, UserContext, MessageRole
)
from ..config import chatbot_config

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """
    Ollama-based LLM provider for local, private AI inference.
    
    Benefits:
    - No API costs
    - Data stays local
    - Works offline
    - Customizable models
    """
    
    def __init__(self):
        self.base_url = chatbot_config.ollama_base_url
        self.model = chatbot_config.ollama_model
        self.timeout = chatbot_config.ollama_timeout
    
    @property
    def name(self) -> str:
        return "ollama"
    
    async def chat(
        self,
        message: str,
        history: List[ChatMessage],
        user_context: UserContext,
        system_prompt: str
    ) -> ChatResponse:
        """Process chat message using Ollama API."""
        start_time = time.time()
        
        try:
            # Build the prompt
            prompt = self._build_prompt(message, history, user_context, system_prompt)
            
            # Call Ollama API
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 1024,
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
            
            response_text = result.get("response", "")
            
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
                tokens_used=result.get("eval_count")
            )
            
        except httpx.TimeoutException:
            logger.error(f"Ollama timeout after {self.timeout}s")
            processing_time = int((time.time() - start_time) * 1000)
            
            return ChatResponse(
                message="I'm taking too long to respond. The local AI might be processing a complex request. Please try a simpler question.",
                actions=[ChatAction(type=ActionType.ERROR, payload={"error": "timeout"})],
                suggestions=["Try again", "Simpler question"],
                provider=self.name,
                processing_time_ms=processing_time
            )
            
        except httpx.ConnectError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}")
            processing_time = int((time.time() - start_time) * 1000)
            
            return ChatResponse(
                message="I cannot connect to the local AI service. Please ensure Ollama is running.",
                actions=[ChatAction(type=ActionType.ERROR, payload={"error": "connection_failed"})],
                suggestions=["Check Ollama", "Try again"],
                provider=self.name,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Ollama error: {str(e)}")
            processing_time = int((time.time() - start_time) * 1000)
            
            return ChatResponse(
                message="I encountered an error with the local AI. Please try again.",
                actions=[ChatAction(type=ActionType.ERROR, payload={"error": str(e)})],
                suggestions=["Try again", "Help"],
                provider=self.name,
                processing_time_ms=processing_time
            )
    
    def _build_prompt(
        self,
        message: str,
        history: List[ChatMessage],
        user_context: UserContext,
        system_prompt: str
    ) -> str:
        """Build the prompt for Ollama (uses chat template format)."""
        # Build conversation in Llama format
        prompt_parts = []
        
        # System prompt with user context
        full_system = f"{system_prompt}\n\n{user_context.to_prompt_context()}"
        prompt_parts.append(f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{full_system}<|eot_id|>")
        
        # Add history
        for msg in history[-chatbot_config.max_history_length:]:
            role = msg.role.value
            if role == "assistant":
                prompt_parts.append(f"<|start_header_id|>assistant<|end_header_id|>\n\n{msg.content}<|eot_id|>")
            else:
                prompt_parts.append(f"<|start_header_id|>user<|end_header_id|>\n\n{msg.content}<|eot_id|>")
        
        # Add current message
        prompt_parts.append(f"<|start_header_id|>user<|end_header_id|>\n\n{message}<|eot_id|>")
        prompt_parts.append("<|start_header_id|>assistant<|end_header_id|>\n\n")
        
        return "".join(prompt_parts)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if Ollama is running and model is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Check if Ollama is running
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                
                models = response.json().get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]
                
                model_available = self.model.split(":")[0] in model_names
                
                return {
                    "status": "healthy" if model_available else "degraded",
                    "provider": self.name,
                    "model": self.model,
                    "model_available": model_available,
                    "available_models": model_names[:5],  # First 5 models
                    "ollama_url": self.base_url
                }
                
        except httpx.ConnectError:
            return {
                "status": "unhealthy",
                "provider": self.name,
                "error": f"Cannot connect to Ollama at {self.base_url}",
                "ollama_url": self.base_url
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.name,
                "error": str(e),
                "ollama_url": self.base_url
            }


class OllamaChatProvider(OllamaProvider):
    """
    Ollama provider using the /api/chat endpoint for better conversation support.
    """
    
    async def chat(
        self,
        message: str,
        history: List[ChatMessage],
        user_context: UserContext,
        system_prompt: str
    ) -> ChatResponse:
        """Process chat using Ollama's chat endpoint."""
        start_time = time.time()
        
        try:
            messages = self._build_messages(message, history, user_context, system_prompt)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 1024,
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
            
            response_text = result.get("message", {}).get("content", "")
            
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
                provider=f"{self.name}-chat",
                processing_time_ms=processing_time,
                tokens_used=result.get("eval_count")
            )
            
        except Exception as e:
            # Fall back to generate endpoint
            logger.warning(f"Ollama chat endpoint failed, falling back to generate: {e}")
            return await super().chat(message, history, user_context, system_prompt)
    
    def _build_messages(
        self,
        message: str,
        history: List[ChatMessage],
        user_context: UserContext,
        system_prompt: str
    ) -> List[Dict[str, str]]:
        """Build messages array for Ollama chat API."""
        messages = []
        
        # System message with user context
        full_system = f"{system_prompt}\n\n{user_context.to_prompt_context()}"
        messages.append({
            "role": "system",
            "content": full_system
        })
        
        # Add history
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
