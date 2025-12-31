"""
Chatbot Package - RBAC-Aware Agentic Chatbot

This package provides a modular, production-grade chatbot with:
- Multi-provider support (OpenAI, Ollama, Rule-based)
- RBAC-aware responses and actions
- Real-time WebSocket communication
- Navigation and file operation capabilities
"""

from .config import chatbot_config, ChatbotConfig
from .orchestrator import ChatbotOrchestrator, get_chatbot

__all__ = [
    'chatbot_config',
    'ChatbotConfig',
    'ChatbotOrchestrator',
    'get_chatbot',
]
