"""
Provider Factory - Create the appropriate LLM provider based on configuration
"""

from typing import Optional
import logging

from .base import LLMProvider
from .openai_provider import OpenAIProvider, OpenAIFunctionCallingProvider
from .ollama_provider import OllamaProvider, OllamaChatProvider
from .rule_based import RuleBasedProvider
from ..config import chatbot_config, LLMProviderType

logger = logging.getLogger(__name__)

# Singleton provider instance
_provider_instance: Optional[LLMProvider] = None


def get_provider(use_function_calling: bool = True) -> LLMProvider:
    """
    Get the configured LLM provider.
    
    Uses a singleton pattern to reuse provider instances.
    
    Args:
        use_function_calling: Use function calling variant if available
        
    Returns:
        LLMProvider instance based on configuration
    """
    global _provider_instance
    
    if _provider_instance is not None:
        return _provider_instance
    
    provider_type = chatbot_config.provider
    
    if provider_type == LLMProviderType.OPENAI:
        if chatbot_config.openai_api_key:
            if use_function_calling:
                _provider_instance = OpenAIFunctionCallingProvider()
                logger.info("Initialized OpenAI provider with function calling")
            else:
                _provider_instance = OpenAIProvider()
                logger.info("Initialized OpenAI provider")
        else:
            logger.warning("OpenAI selected but no API key provided, falling back to rule-based")
            _provider_instance = RuleBasedProvider()
            
    elif provider_type == LLMProviderType.OLLAMA:
        # Use chat endpoint by default for Ollama
        _provider_instance = OllamaChatProvider()
        logger.info(f"Initialized Ollama provider (model: {chatbot_config.ollama_model})")
        
    else:
        _provider_instance = RuleBasedProvider()
        logger.info("Initialized rule-based provider (no AI)")
    
    return _provider_instance


def reset_provider():
    """Reset the provider instance (useful for testing or config changes)."""
    global _provider_instance
    _provider_instance = None


async def get_provider_health() -> dict:
    """Get health status of the current provider."""
    provider = get_provider()
    return await provider.health_check()
