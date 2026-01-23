"""
Chatbot Configuration - Feature flags and provider settings

Environment Variables:
- CHATBOT_ENABLED: true/false - toggles entire chatbot feature
- LLM_PROVIDER: "openai" | "ollama" | "nvidia" | "auto" | "none" - which AI provider to use
- OPENAI_API_KEY: API key for OpenAI
- OPENAI_MODEL: Model to use (default: gpt-4o-mini)
- OLLAMA_BASE_URL: URL for Ollama server (default: http://localhost:11434)
- OLLAMA_MODEL: Model to use (default: llama3.2)
- NVIDIA_API_KEY: API key for NVIDIA NIM
- NVIDIA_MODEL: Model to use (default: meta/llama-3.1-70b-instruct)
"""

import os
from dataclasses import dataclass
from typing import Literal, Optional
from enum import Enum


class LLMProviderType(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    OLLAMA = "ollama"
    NVIDIA = "nvidia"
    AUTO = "auto"  # Auto-select: NVIDIA if key exists, else Ollama
    NONE = "none"  # Rule-based, no AI


@dataclass
class ChatbotConfig:
    """Chatbot configuration loaded from environment."""
    
    # Feature flag
    enabled: bool
    
    # Provider selection
    provider: LLMProviderType
    
    # OpenAI settings
    openai_api_key: Optional[str]
    openai_model: str
    openai_max_tokens: int
    openai_temperature: float
    
    # Ollama settings
    ollama_base_url: str
    ollama_model: str
    ollama_timeout: int
    
    # NVIDIA NIM settings
    nvidia_api_key: Optional[str]
    nvidia_model: str
    nvidia_timeout: int
    
    # General settings
    max_history_length: int  # Max messages to keep in context
    system_prompt: str
    
    # Self-healing settings
    self_healing_enabled: bool
    
    @classmethod
    def from_env(cls) -> 'ChatbotConfig':
        """Load configuration from environment variables."""
        # Get provider from env
        provider_str = os.environ.get('LLM_PROVIDER', 'ollama').lower()
        nvidia_key = os.environ.get('NVIDIA_API_KEY')
        
        # Auto mode: use NVIDIA if key exists, else Ollama
        if provider_str == 'auto':
            if nvidia_key:
                provider = LLMProviderType.NVIDIA
            else:
                provider = LLMProviderType.OLLAMA
        else:
            provider = LLMProviderType(provider_str)
        
        return cls(
            # Feature flag
            enabled=os.environ.get('CHATBOT_ENABLED', 'false').lower() == 'true',
            
            # Provider (resolved from auto if needed)
            provider=provider,
            
            # OpenAI
            openai_api_key=os.environ.get('OPENAI_API_KEY'),
            openai_model=os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
            openai_max_tokens=int(os.environ.get('OPENAI_MAX_TOKENS', '1024')),
            openai_temperature=float(os.environ.get('OPENAI_TEMPERATURE', '0.7')),
            
            # Ollama
            ollama_base_url=os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434'),
            ollama_model=os.environ.get('OLLAMA_MODEL', 'llama3.2'),
            ollama_timeout=int(os.environ.get('OLLAMA_TIMEOUT', '60')),
            
            # NVIDIA NIM
            nvidia_api_key=nvidia_key,
            nvidia_model=os.environ.get('NVIDIA_MODEL', 'meta/llama-3.1-70b-instruct'),
            nvidia_timeout=int(os.environ.get('NVIDIA_TIMEOUT', '60')),
            
            # General
            max_history_length=int(os.environ.get('CHATBOT_MAX_HISTORY', '20')),
            system_prompt=os.environ.get('CHATBOT_SYSTEM_PROMPT', DEFAULT_SYSTEM_PROMPT),
            
            # Self-healing
            self_healing_enabled=os.environ.get('CHATBOT_SELF_HEALING', 'true').lower() == 'true',
        )
    
    @property
    def is_ai_enabled(self) -> bool:
        """Check if an AI provider is configured."""
        return self.provider in (LLMProviderType.OPENAI, LLMProviderType.OLLAMA, LLMProviderType.NVIDIA)


DEFAULT_SYSTEM_PROMPT = """You are FileVault Assistant, an AI helper for the FileVault document management platform.

Your capabilities:
1. **Navigation**: Help users navigate to different pages (files, users, settings, etc.)
2. **File Operations**: Help with file uploads, downloads, sharing, and deletion
3. **Information**: Answer questions about the platform, features, and user's data
4. **Guidance**: Provide step-by-step instructions for tasks

IMPORTANT - Action Syntax:
When suggesting navigation or actions, you MUST include these markers in your response:
- For navigation: [NAVIGATE:/path/to/page] - Example: [NAVIGATE:/dashboard/files]
- For actions that need confirmation: [CONFIRM:action_name:confirmation message]

Example responses:
- "I'll take you to your files now. [NAVIGATE:/dashboard/files]"
- "Let me show you all users. [NAVIGATE:/dashboard/users]"
- "Here are your settings. [NAVIGATE:/dashboard/settings]"

Important rules:
- You MUST respect the user's role and permissions. Never suggest actions they can't perform.
- Be concise but helpful. Use bullet points for lists.
- ALWAYS include the [NAVIGATE:...] marker when the user wants to go somewhere.
- For navigation requests, include the marker AND a helpful response.
- Always be professional and friendly.

Available navigation paths (with role requirements):
- /dashboard - Main dashboard overview (all roles)
- /dashboard/files - User's files (all roles)
- /dashboard/all-files - All platform files (super_admin only)
- /dashboard/users - User management (super_admin only)
- /dashboard/settings - Account settings (all roles)
- /dashboard/approvals - Pending user/org approvals (super_admin, org_admin)
- /dashboard/organizations - Organization management (super_admin only)
- /dashboard/quarantine - Quarantined/infected files (super_admin only)
- /dashboard/team - Team members (org_admin, manager)
- /dashboard/analytics - Analytics and reports (super_admin, org_admin, manager)
- /dashboard/api-keys - API key management (super_admin, org_admin)
- /dashboard/infrastructure - Server/service status (super_admin only)
- /dashboard/system-logs - System logs for debugging issues (super_admin only)
- /dashboard/database - Database management (super_admin only)
- /dashboard/api-gateway - API Gateway management (super_admin only)
- /dashboard/security - Security settings (super_admin, org_admin)

When user asks about debugging, errors, issues, logs, or system problems, suggest /dashboard/system-logs.
When user asks about virus scans or infected files, suggest /dashboard/quarantine.
When user asks about servers or services, suggest /dashboard/infrastructure.

User context will be provided with each message including their role and permissions.
"""


# Singleton config instance
chatbot_config = ChatbotConfig.from_env()
