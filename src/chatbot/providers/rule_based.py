"""
Rule-Based Provider - Pattern matching without AI

This provider handles basic queries using predefined patterns and responses.
Useful when:
- AI providers are not configured
- Cost optimization for simple queries
- Offline/air-gapped environments
- Fallback when AI fails
"""

import time
import re
from typing import List, Dict, Any, Tuple, Optional
import logging

from .base import (
    LLMProvider, ChatMessage, ChatResponse, ChatAction,
    ActionType, UserContext
)

logger = logging.getLogger(__name__)


class RuleBasedProvider(LLMProvider):
    """
    Rule-based chatbot using pattern matching.
    
    No AI costs, instant responses, predictable behavior.
    """
    
    def __init__(self):
        self.patterns = self._build_patterns()
    
    @property
    def name(self) -> str:
        return "rule-based"
    
    def _build_patterns(self) -> List[Tuple[re.Pattern, callable]]:
        """Build regex patterns and their handlers."""
        return [
            # Greetings
            (
                re.compile(r'\b(hi|hello|hey|greetings)\b', re.IGNORECASE),
                self._handle_greeting
            ),
            # Help
            (
                re.compile(r'\b(help|assist|support|how do i|how to)\b', re.IGNORECASE),
                self._handle_help
            ),
            # Navigation - Files (expanded patterns)
            (
                re.compile(r'\b(my files?|show files?|view files?|go to files?|open files?|take me to.*files?|navigate.*files?|files? page)\b', re.IGNORECASE),
                self._handle_navigate_files
            ),
            # Navigation - All Files (admin)
            (
                re.compile(r'\b(all files|platform files|all documents|every file)\b', re.IGNORECASE),
                self._handle_navigate_all_files
            ),
            # Navigation - Users (expanded)
            (
                re.compile(r'\b(users?|manage users?|user management|show users?|take me to.*users?|list users?)\b', re.IGNORECASE),
                self._handle_navigate_users
            ),
            # Navigation - Settings (expanded)
            (
                re.compile(r'\b(settings|preferences|account settings|my account|take me to.*settings)\b', re.IGNORECASE),
                self._handle_navigate_settings
            ),
            # Navigation - Dashboard (expanded)
            (
                re.compile(r'\b(dashboard|home|main page|go home|take me to.*dashboard|take me home)\b', re.IGNORECASE),
                self._handle_navigate_dashboard
            ),
            # Navigation - Organizations
            (
                re.compile(r'\b(organizations?|orgs?|tenants?|take me to.*org)\b', re.IGNORECASE),
                self._handle_navigate_organizations
            ),
            # Navigation - Approvals
            (
                re.compile(r'\b(approvals?|pending|review)\b', re.IGNORECASE),
                self._handle_navigate_approvals
            ),
            # Navigation - Analytics
            (
                re.compile(r'\b(analytics?|reports?|statistics?|metrics?|insights?|take me to.*analytics)\b', re.IGNORECASE),
                self._handle_navigate_analytics
            ),
            # Navigation - API Gateway
            (
                re.compile(r'\b(api gateway|gateway|kong|take me to.*gateway)\b', re.IGNORECASE),
                self._handle_navigate_api_gateway
            ),
            # Navigation - API Keys
            (
                re.compile(r'\b(api keys?|keys?|tokens?|take me to.*api.?keys?)\b', re.IGNORECASE),
                self._handle_navigate_api_keys
            ),
            # Navigation - Database
            (
                re.compile(r'\b(database|db|mysql|take me to.*database)\b', re.IGNORECASE),
                self._handle_navigate_database
            ),
            # Navigation - System Logs (must be before Infrastructure to match "system logs" correctly)
            (
                re.compile(r'\b(system logs?|audit logs?|logs?|history|take me to.*logs?)\b', re.IGNORECASE),
                self._handle_navigate_system_logs
            ),
            # Navigation - Infrastructure (removed "system" to avoid conflict with system logs)
            (
                re.compile(r'\b(infrastructure|infra|servers?|take me to.*infrastructure)\b', re.IGNORECASE),
                self._handle_navigate_infrastructure
            ),
            # Navigation - Platform Admin
            (
                re.compile(r'\b(platform admin|platformadmin|admin panel|admin page|take me to.*platform.?admin)\b', re.IGNORECASE),
                self._handle_navigate_platformadmin
            ),
            # Navigation - Quarantine
            (
                re.compile(r'\b(quarantine|quarantined|infected|virus|malware|take me to.*quarantine)\b', re.IGNORECASE),
                self._handle_navigate_quarantine
            ),
            # Navigation - Security
            (
                re.compile(r'\b(security|permissions|access control|rbac|take me to.*security)\b', re.IGNORECASE),
                self._handle_navigate_security
            ),
            # Navigation - Team
            (
                re.compile(r'\b(team|members?|colleagues?|staff|take me to.*team)\b', re.IGNORECASE),
                self._handle_navigate_team
            ),
            # File Upload
            (
                re.compile(r'\b(upload|upload file|add file|new file)\b', re.IGNORECASE),
                self._handle_upload
            ),
            # File Download
            (
                re.compile(r'\b(download|get file|save file)\b', re.IGNORECASE),
                self._handle_download
            ),
            # File Share
            (
                re.compile(r'\b(share|sharing|share file|send file)\b', re.IGNORECASE),
                self._handle_share
            ),
            # File Delete
            (
                re.compile(r'\b(delete|remove|trash|delete file)\b', re.IGNORECASE),
                self._handle_delete
            ),
            # Status/Info
            (
                re.compile(r'\b(status|my role|who am i|my permissions|what can i do)\b', re.IGNORECASE),
                self._handle_status
            ),
            # Thanks
            (
                re.compile(r'\b(thanks|thank you|thx|ty)\b', re.IGNORECASE),
                self._handle_thanks
            ),
            # Goodbye
            (
                re.compile(r'\b(bye|goodbye|see you|exit|quit)\b', re.IGNORECASE),
                self._handle_goodbye
            ),
        ]
    
    async def chat(
        self,
        message: str,
        history: List[ChatMessage],
        user_context: UserContext,
        system_prompt: str
    ) -> ChatResponse:
        """Process message using pattern matching."""
        start_time = time.time()
        
        # Try each pattern
        for pattern, handler in self.patterns:
            if pattern.search(message):
                response = handler(message, user_context)
                response.processing_time_ms = int((time.time() - start_time) * 1000)
                return response
        
        # Default response
        processing_time = int((time.time() - start_time) * 1000)
        return ChatResponse(
            message=self._default_response(user_context),
            actions=[],
            suggestions=self._get_default_suggestions(user_context),
            provider=self.name,
            processing_time_ms=processing_time
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Rule-based is always healthy."""
        return {
            "status": "healthy",
            "provider": self.name,
            "patterns_loaded": len(self.patterns),
            "note": "Rule-based provider is always available"
        }
    
    # ========== Handler Methods ==========
    
    def _handle_greeting(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle greeting messages."""
        role_greeting = {
            "super_admin": "As a Super Admin, you have full access to all platform features.",
            "org_admin": "As an Organization Admin, you can manage your organization's files and users.",
            "manager": "As a Manager, you can manage team files and view reports.",
            "user": "You can upload, download, and share files.",
            "viewer": "You have read-only access to shared files."
        }
        
        greeting = role_greeting.get(ctx.role, "Welcome to FileVault!")
        
        return ChatResponse(
            message=f"Hello {ctx.email}! 👋 Welcome to FileVault Assistant.\n\n{greeting}\n\nHow can I help you today?",
            actions=[],
            suggestions=self._get_default_suggestions(ctx),
            provider=self.name
        )
    
    def _handle_help(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle help requests."""
        help_text = """Here's what I can help you with:

📁 **File Management**
- Upload, download, share, and delete files
- Navigate to your files or search

🧭 **Navigation**
- Take you to any page in the app
- Show your dashboard, files, settings

ℹ️ **Information**
- Your role and permissions
- How to use features

Just tell me what you'd like to do!"""
        
        return ChatResponse(
            message=help_text,
            actions=[],
            suggestions=["My files", "Upload file", "My role"],
            provider=self.name
        )
    
    def _handle_navigate_files(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to user's files."""
        return ChatResponse(
            message="Taking you to your files. 📁",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/files"},
                    description="Navigate to My Files"
                )
            ],
            suggestions=["Upload file", "Help"],
            provider=self.name
        )
    
    def _handle_navigate_all_files(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to all files (admin only)."""
        if ctx.role not in ("super_admin", "org_admin"):
            return ChatResponse(
                message="Sorry, you don't have permission to view all platform files. You can access your own files instead.",
                actions=[
                    ChatAction(
                        type=ActionType.NAVIGATE,
                        payload={"path": "/dashboard/files"},
                        description="Navigate to My Files"
                    )
                ],
                suggestions=["My files", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to all platform files. 📂",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/all-files"},
                    description="Navigate to All Files"
                )
            ],
            suggestions=["My files", "Help"],
            provider=self.name
        )
    
    def _handle_navigate_users(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to user management."""
        if ctx.role not in ("super_admin", "org_admin"):
            return ChatResponse(
                message="Sorry, user management is only available to administrators.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to user management. 👥",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/users"},
                    description="Navigate to User Management"
                )
            ],
            suggestions=["All files", "Settings"],
            provider=self.name
        )
    
    def _handle_navigate_settings(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to settings."""
        return ChatResponse(
            message="Taking you to your account settings. ⚙️",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/settings"},
                    description="Navigate to Settings"
                )
            ],
            suggestions=["My files", "Dashboard"],
            provider=self.name
        )
    
    def _handle_navigate_dashboard(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to dashboard."""
        return ChatResponse(
            message="Taking you to the dashboard. 🏠",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard"},
                    description="Navigate to Dashboard"
                )
            ],
            suggestions=["My files", "Settings"],
            provider=self.name
        )
    
    def _handle_navigate_organizations(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to organizations (super admin only)."""
        if ctx.role != "super_admin":
            return ChatResponse(
                message="Sorry, organization management is only available to Super Admins.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to organization management. 🏢",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/organizations"},
                    description="Navigate to Organizations"
                )
            ],
            suggestions=["All files", "Users"],
            provider=self.name
        )
    
    def _handle_navigate_approvals(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to approvals."""
        return ChatResponse(
            message="Taking you to file approvals. ✅",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/approvals"},
                    description="Navigate to Approvals"
                )
            ],
            suggestions=["My files", "Dashboard"],
            provider=self.name
        )
    
    def _handle_navigate_analytics(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to analytics."""
        if ctx.role not in ("super_admin", "org_admin", "manager"):
            return ChatResponse(
                message="Sorry, analytics is only available to managers and above.",
                actions=[],
                suggestions=["My files", "Dashboard", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to analytics. 📊",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/analytics"},
                    description="Navigate to Analytics"
                )
            ],
            suggestions=["Dashboard", "My files"],
            provider=self.name
        )
    
    def _handle_navigate_api_gateway(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to API gateway (super admin only)."""
        if ctx.role != "super_admin":
            return ChatResponse(
                message="Sorry, API Gateway management is only available to Super Admins.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to API Gateway management. 🔌",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/api-gateway"},
                    description="Navigate to API Gateway"
                )
            ],
            suggestions=["Infrastructure", "System logs"],
            provider=self.name
        )
    
    def _handle_navigate_api_keys(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to API keys."""
        if ctx.role not in ("super_admin", "org_admin"):
            return ChatResponse(
                message="Sorry, API key management is only available to administrators.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to API keys management. 🔑",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/api-keys"},
                    description="Navigate to API Keys"
                )
            ],
            suggestions=["Settings", "Security"],
            provider=self.name
        )
    
    def _handle_navigate_database(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to database management (super admin only)."""
        if ctx.role != "super_admin":
            return ChatResponse(
                message="Sorry, database management is only available to Super Admins.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to database management. 🗄️",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/database"},
                    description="Navigate to Database"
                )
            ],
            suggestions=["Infrastructure", "System logs"],
            provider=self.name
        )
    
    def _handle_navigate_infrastructure(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to infrastructure (super admin only)."""
        if ctx.role != "super_admin":
            return ChatResponse(
                message="Sorry, infrastructure management is only available to Super Admins.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to infrastructure management. 🖥️",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/infrastructure"},
                    description="Navigate to Infrastructure"
                )
            ],
            suggestions=["Database", "System logs"],
            provider=self.name
        )
    
    def _handle_navigate_platformadmin(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to platform admin (super admin only)."""
        if ctx.role != "super_admin":
            return ChatResponse(
                message="Sorry, platform administration is only available to Super Admins.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to platform administration. 🛠️",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/platformadmin"},
                    description="Navigate to Platform Admin"
                )
            ],
            suggestions=["Organizations", "System logs"],
            provider=self.name
        )
    
    def _handle_navigate_quarantine(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to quarantine."""
        if ctx.role not in ("super_admin", "org_admin"):
            return ChatResponse(
                message="Sorry, quarantine access is only available to administrators.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to quarantined files. ⚠️",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/quarantine"},
                    description="Navigate to Quarantine"
                )
            ],
            suggestions=["All files", "Security"],
            provider=self.name
        )
    
    def _handle_navigate_security(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to security."""
        if ctx.role not in ("super_admin", "org_admin"):
            return ChatResponse(
                message="Sorry, security settings are only available to administrators.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to security settings. 🔒",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/security"},
                    description="Navigate to Security"
                )
            ],
            suggestions=["Users", "API keys"],
            provider=self.name
        )
    
    def _handle_navigate_system_logs(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to system logs (super admin only)."""
        if ctx.role != "super_admin":
            return ChatResponse(
                message="Sorry, system logs are only available to Super Admins.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to system logs. 📋",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/system-logs"},
                    description="Navigate to System Logs"
                )
            ],
            suggestions=["Infrastructure", "Database"],
            provider=self.name
        )
    
    def _handle_navigate_team(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to team management."""
        if ctx.role not in ("super_admin", "org_admin", "manager"):
            return ChatResponse(
                message="Sorry, team management is only available to managers and above.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to team management. 👥",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/team"},
                    description="Navigate to Team"
                )
            ],
            suggestions=["Users", "Analytics"],
            provider=self.name
        )

    def _handle_upload(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle file upload guidance."""
        if ctx.role == "viewer":
            return ChatResponse(
                message="Sorry, viewers cannot upload files. Please contact your administrator if you need upload access.",
                actions=[],
                suggestions=["My files", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="""To upload a file:

1. Go to your **Files** page
2. Click the **Upload** button (or drag & drop)
3. Select your file(s)
4. Wait for the upload to complete

Let me take you to the Files page so you can upload.""",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/files"},
                    description="Navigate to Files to upload"
                )
            ],
            suggestions=["My files", "Help"],
            provider=self.name
        )
    
    def _handle_download(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle file download guidance."""
        return ChatResponse(
            message="""To download a file:

1. Go to your **Files** page
2. Find the file you want to download
3. Click the **Download** icon or menu option

Let me take you to your files.""",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/files"},
                    description="Navigate to Files"
                )
            ],
            suggestions=["My files", "Help"],
            provider=self.name
        )
    
    def _handle_share(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle file sharing guidance."""
        if ctx.role == "viewer":
            return ChatResponse(
                message="Sorry, viewers cannot share files. Please contact your administrator for sharing permissions.",
                actions=[],
                suggestions=["My files", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="""To share a file:

1. Go to your **Files** page
2. Find the file you want to share
3. Click the **Share** icon
4. Copy the share link or enter recipient email

Let me take you to your files.""",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/files"},
                    description="Navigate to Files"
                )
            ],
            suggestions=["My files", "Help"],
            provider=self.name
        )
    
    def _handle_delete(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle file deletion guidance."""
        if ctx.role == "viewer":
            return ChatResponse(
                message="Sorry, viewers cannot delete files.",
                actions=[],
                suggestions=["My files", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="""To delete a file:

1. Go to your **Files** page
2. Find the file you want to delete
3. Click the **Delete** icon or menu option
4. Confirm the deletion

⚠️ **Warning**: Deleted files cannot be recovered!

Let me take you to your files.""",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/files"},
                    description="Navigate to Files"
                )
            ],
            suggestions=["My files", "Help"],
            provider=self.name
        )
    
    def _handle_status(self, message: str, ctx: UserContext) -> ChatResponse:
        """Show user's status and permissions."""
        role_descriptions = {
            "super_admin": "**Super Admin** - Full access to all features across all organizations",
            "org_admin": "**Organization Admin** - Manage your organization's files and users",
            "manager": "**Manager** - Manage team files and view reports",
            "user": "**User** - Upload, download, and share your own files",
            "viewer": "**Viewer** - Read-only access to shared files"
        }
        
        role_desc = role_descriptions.get(ctx.role, "Standard User")
        
        status_text = f"""**Your Account Status**

📧 **Email**: {ctx.email}
🔑 **Role**: {role_desc}
🏢 **Organization**: {ctx.organization_name or 'N/A'}

**Your Permissions**:
{self._format_permissions(ctx)}"""
        
        return ChatResponse(
            message=status_text,
            actions=[],
            suggestions=self._get_default_suggestions(ctx),
            provider=self.name
        )
    
    def _format_permissions(self, ctx: UserContext) -> str:
        """Format permissions list."""
        if not ctx.permissions:
            return "- Standard user permissions"
        
        permission_icons = {
            "FILE_READ": "📖 Read files",
            "FILE_WRITE": "✏️ Write files",
            "FILE_DELETE": "🗑️ Delete files",
            "FILE_SHARE": "🔗 Share files",
            "USER_READ": "👁️ View users",
            "USER_WRITE": "👤 Manage users",
            "ADMIN_ACCESS": "🔐 Admin access"
        }
        
        lines = []
        for perm in ctx.permissions:
            icon_text = permission_icons.get(perm, f"• {perm}")
            lines.append(f"- {icon_text}")
        
        return "\n".join(lines) if lines else "- Standard user permissions"
    
    def _handle_thanks(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle thank you messages."""
        return ChatResponse(
            message="You're welcome! 😊 Is there anything else I can help you with?",
            actions=[],
            suggestions=self._get_default_suggestions(ctx),
            provider=self.name
        )
    
    def _handle_goodbye(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle goodbye messages."""
        return ChatResponse(
            message="Goodbye! 👋 Have a great day! I'm here whenever you need help.",
            actions=[],
            suggestions=["Help"],
            provider=self.name
        )
    
    def _default_response(self, ctx: UserContext) -> str:
        """Default response when no pattern matches."""
        return """I'm not sure I understand that request. Here are some things you can ask me:

- "Take me to my files"
- "How do I upload a file?"
- "What's my role?"
- "Help"

Or try one of the suggestions below!"""
    
    def _get_default_suggestions(self, ctx: UserContext) -> List[str]:
        """Get default suggestions based on user role."""
        if ctx.role in ("super_admin", "org_admin"):
            return ["My files", "All files", "Users", "Help"]
        elif ctx.role == "viewer":
            return ["My files", "Settings", "Help"]
        else:
            return ["My files", "Upload file", "Settings", "Help"]
