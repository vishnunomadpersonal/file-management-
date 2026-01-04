"""
NVIDIA NIM Provider for FileVault AI Chatbot
=============================================
Uses NVIDIA NIM API for fast, accurate LLM responses.
Supports multiple models including Nemotron and Llama.
"""

import os
import logging
import httpx
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NvidiaChatResponse:
    """Response from NVIDIA API."""
    message: str
    success: bool
    provider: str = "nvidia"
    model: str = ""
    tokens_used: Optional[int] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None


class NvidiaProvider:
    """
    NVIDIA NIM API Provider.
    
    Supported models:
    - nvidia/nemotron-3-nano-30b-a3b (recommended for SQL)
    - meta/llama-3.1-70b-instruct
    - meta/llama-3.1-8b-instruct
    - qwen/qwen3-next-80b-a3b-thinking
    """
    
    BASE_URL = "https://integrate.api.nvidia.com/v1"
    
    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        timeout: float = 60.0
    ):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY is required")
        
        # Default to Qwen3 Next 80B for SQL/coding tasks (fastest + accurate)
        self.model = model or os.getenv("NVIDIA_MODEL", "qwen/qwen3-next-80b-a3b-instruct")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"NVIDIA NIM Provider initialized with model: {self.model}")
    
    async def chat(
        self,
        message: str,
        system_prompt: str = None,
        context: Dict[str, Any] = None,
        **kwargs
    ) -> NvidiaChatResponse:
        """Send a chat message to NVIDIA NIM API."""
        
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add user message
        messages.append({
            "role": "user",
            "content": message
        })
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "top_p": kwargs.get("top_p", 0.9),
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"NVIDIA API error: {response.status_code} - {error_text}")
                    return NvidiaChatResponse(
                        message=f"Error: API returned {response.status_code}",
                        success=False,
                        provider="nvidia",
                        model=self.model,
                        error=error_text
                    )
                
                data = response.json()
                
                # Extract response
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                
                return NvidiaChatResponse(
                    message=content,
                    success=True,
                    provider="nvidia",
                    model=self.model,
                    tokens_used=usage.get("total_tokens"),
                    metadata={
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "completion_tokens": usage.get("completion_tokens"),
                        "finish_reason": data["choices"][0].get("finish_reason")
                    }
                )
                
        except httpx.TimeoutException:
            logger.error(f"NVIDIA API timeout after {self.timeout}s")
            return NvidiaChatResponse(
                message="Request timed out. Please try again.",
                success=False,
                provider="nvidia",
                model=self.model,
                error="Timeout"
            )
        except Exception as e:
            logger.error(f"NVIDIA API error: {e}")
            return NvidiaChatResponse(
                message=f"Error communicating with NVIDIA API: {str(e)}",
                success=False,
                provider="nvidia",
                model=self.model,
                error=str(e)
            )
    
    async def generate_sql(
        self,
        question: str,
        schema: str,
        examples: str = "",
        **kwargs
    ) -> str:
        """Generate SQL from natural language using NVIDIA NIM."""
        
        system_prompt = f"""You are an expert SQL developer. Generate MySQL queries based on user questions.

{schema}

{examples}

Rules:
1. ONLY generate SELECT queries - never INSERT, UPDATE, DELETE, DROP
2. Use table aliases (u for users, f for files, o for organizations)
3. Always add LIMIT 50 unless user specifies otherwise
4. For aggregations with GROUP BY, include ALL non-aggregated columns in GROUP BY
5. Use LEFT JOIN when counting records that might be zero
6. Output ONLY the SQL query - no explanations

Generate a MySQL SELECT query:"""

        response = await self.chat(
            message=question,
            system_prompt=system_prompt,
            temperature=0.1,  # Low temperature for SQL accuracy
            **kwargs
        )
        
        if response.success:
            sql = response.message.strip()
            # Clean up markdown if present
            if sql.startswith('```'):
                sql = sql.split('```')[1]
                if sql.startswith('sql'):
                    sql = sql[3:]
            sql = sql.strip().rstrip(';') + ';'
            return sql
        else:
            raise Exception(f"SQL generation failed: {response.error}")
    
    def get_provider_name(self) -> str:
        return "nvidia"
    
    def get_model_name(self) -> str:
        return self.model
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if NVIDIA API key is configured."""
        return bool(os.getenv("NVIDIA_API_KEY"))


class NvidiaLangChainLLM:
    """
    LangChain-compatible wrapper for NVIDIA NIM.
    Can be used as a drop-in replacement for ChatOllama.
    """
    
    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        temperature: float = 0.1,
        **kwargs
    ):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self.model = model or os.getenv("NVIDIA_MODEL", "qwen/qwen3-next-80b-a3b-instruct")
        self.temperature = temperature
        self.base_url = "https://integrate.api.nvidia.com/v1"
        
    async def ainvoke(self, prompt: str) -> "AIMessage":
        """Async invoke for LangChain compatibility."""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Handle both string and PromptValue inputs
        if hasattr(prompt, 'to_string'):
            prompt_text = prompt.to_string()
        else:
            prompt_text = str(prompt)
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": self.temperature,
            "max_tokens": 2048,
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"NVIDIA API error: {response.status_code} - {response.text}")
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            return AIMessage(content=content)
    
    def invoke(self, prompt: str) -> "AIMessage":
        """Sync invoke for LangChain compatibility."""
        import asyncio
        return asyncio.run(self.ainvoke(prompt))


class AIMessage:
    """Simple AIMessage class for LangChain compatibility."""
    def __init__(self, content: str):
        self.content = content
