"""
Base LLM Provider - Abstract interface for all providers
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum
import uuid


class MessageRole(str, Enum):
    """Message roles in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ActionType(str, Enum):
    """Types of actions the chatbot can suggest."""
    NAVIGATE = "navigate"           # Navigate to a page
    EXECUTE = "execute"             # Execute an API action
    CONFIRM = "confirm"             # Ask for confirmation before action
    INFO = "info"                   # Just information, no action
    ERROR = "error"                 # Error occurred


@dataclass
class ChatMessage:
    """A single message in the conversation."""
    role: MessageRole
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ChatMessage':
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
            message_id=data.get("message_id", str(uuid.uuid4())),
            metadata=data.get("metadata", {})
        )


@dataclass
class ChatAction:
    """An action the chatbot wants to perform."""
    type: ActionType
    payload: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    requires_confirmation: bool = False
    
    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "payload": self.payload,
            "description": self.description,
            "requires_confirmation": self.requires_confirmation
        }


@dataclass
class ChatResponse:
    """Response from the chatbot."""
    message: str
    actions: List[ChatAction] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)  # Quick reply suggestions
    provider: str = "unknown"
    processing_time_ms: int = 0
    tokens_used: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "actions": [a.to_dict() for a in self.actions],
            "suggestions": self.suggestions,
            "provider": self.provider,
            "processing_time_ms": self.processing_time_ms,
            "tokens_used": self.tokens_used
        }


@dataclass
class UserContext:
    """User context for RBAC-aware responses."""
    user_id: str
    email: str
    role: str  # super_admin, org_admin, manager, user, viewer
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    
    def to_prompt_context(self) -> str:
        """Convert to a context string for the LLM."""
        return f"""
Current User Context:
- User ID: {self.user_id}
- Email: {self.email}
- Role: {self.role}
- Organization: {self.organization_name or 'N/A'} (ID: {self.organization_id or 'N/A'})
- Permissions: {', '.join(self.permissions) if self.permissions else 'Standard user permissions'}

Based on the user's role:
- super_admin: Full access to all features and data
- org_admin: Can manage their organization's files and users
- manager: Can manage team files and view reports
- user: Can upload, download, and share their own files
- viewer: Read-only access to files shared with them
""".strip()


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging and responses."""
        pass
    
    @abstractmethod
    async def chat(
        self,
        message: str,
        history: List[ChatMessage],
        user_context: UserContext,
        system_prompt: str
    ) -> ChatResponse:
        """
        Process a chat message and return a response.
        
        Args:
            message: The user's message
            history: Previous messages in the conversation
            user_context: User's role and permissions
            system_prompt: System prompt for the AI
            
        Returns:
            ChatResponse with message, actions, and suggestions
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check if the provider is healthy and available."""
        pass
    
    def _parse_actions(self, response_text: str) -> List[ChatAction]:
        """
        Parse actions from the response text.
        
        Actions are marked with special syntax:
        [NAVIGATE:/dashboard/files]
        [EXECUTE:delete_file:file_id=123]
        [CONFIRM:delete_file:Are you sure?]
        """
        import re
        actions = []
        
        # Parse navigation actions
        nav_pattern = r'\[NAVIGATE:([^\]]+)\]'
        for match in re.finditer(nav_pattern, response_text):
            path = match.group(1).strip()
            actions.append(ChatAction(
                type=ActionType.NAVIGATE,
                payload={"path": path},
                description=f"Navigate to {path}"
            ))
        
        # Parse execute actions
        exec_pattern = r'\[EXECUTE:(\w+):([^\]]*)\]'
        for match in re.finditer(exec_pattern, response_text):
            action_name = match.group(1)
            params_str = match.group(2)
            params = dict(p.split('=') for p in params_str.split(',') if '=' in p)
            actions.append(ChatAction(
                type=ActionType.EXECUTE,
                payload={"action": action_name, "params": params},
                description=f"Execute {action_name}",
                requires_confirmation=True
            ))
        
        # Parse confirm actions
        confirm_pattern = r'\[CONFIRM:(\w+):([^\]]+)\]'
        for match in re.finditer(confirm_pattern, response_text):
            action_name = match.group(1)
            message = match.group(2)
            actions.append(ChatAction(
                type=ActionType.CONFIRM,
                payload={"action": action_name, "message": message},
                description=message,
                requires_confirmation=True
            ))
        
        return actions
    
    def _clean_response(self, response_text: str) -> str:
        """Remove action markers from response text."""
        import re
        # Remove all action markers
        cleaned = re.sub(r'\[(?:NAVIGATE|EXECUTE|CONFIRM):[^\]]+\]', '', response_text)
        # Clean up extra whitespace
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        return cleaned.strip()
    
    def _generate_suggestions(self, response_text: str, user_context: UserContext) -> List[str]:
        """Generate quick reply suggestions based on context."""
        suggestions = []
        
        # Common suggestions based on role
        if user_context.role in ('super_admin', 'org_admin'):
            suggestions.extend([
                "Show all files",
                "List users",
                "System status"
            ])
        else:
            suggestions.extend([
                "My files",
                "Upload a file",
                "Help"
            ])
        
        return suggestions[:4]  # Max 4 suggestions
