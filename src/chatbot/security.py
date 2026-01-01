"""
Chatbot Security - RBAC filtering and permission checks
"""

from typing import List, Dict, Optional, Any
from functools import wraps
import logging

from .providers.base import UserContext, ChatAction, ActionType

logger = logging.getLogger(__name__)


# Navigation paths and their required permissions/roles
# Note: Permission values use format "file:read" (lowercase with colon)
NAVIGATION_PERMISSIONS = {
    "/dashboard": {
        "roles": ["super_admin", "org_admin", "manager", "user", "viewer"],
        "permissions": []
    },
    "/dashboard/files": {
        "roles": ["super_admin", "org_admin", "manager", "user", "viewer"],
        "permissions": ["file:read"]
    },
    "/dashboard/all-files": {
        "roles": ["super_admin", "org_admin"],
        "permissions": ["file:read"]
    },
    "/dashboard/users": {
        "roles": ["super_admin", "org_admin"],
        "permissions": ["user:read"]
    },
    "/dashboard/settings": {
        "roles": ["super_admin", "org_admin", "manager", "user", "viewer"],
        "permissions": []
    },
    "/dashboard/approvals": {
        "roles": ["super_admin", "org_admin", "manager"],
        "permissions": []
    },
    "/dashboard/organizations": {
        "roles": ["super_admin"],
        "permissions": []
    },
    # Additional pages
    "/dashboard/analytics": {
        "roles": ["super_admin", "org_admin", "manager"],
        "permissions": ["analytics:read"]
    },
    "/dashboard/api-gateway": {
        "roles": ["super_admin"],
        "permissions": ["system:admin"]
    },
    "/dashboard/api-keys": {
        "roles": ["super_admin", "org_admin"],
        "permissions": []
    },
    "/dashboard/database": {
        "roles": ["super_admin"],
        "permissions": ["system:admin"]
    },
    "/dashboard/infrastructure": {
        "roles": ["super_admin"],
        "permissions": ["system:admin"]
    },
    "/dashboard/platformadmin": {
        "roles": ["super_admin"],
        "permissions": ["system:admin"]
    },
    "/dashboard/quarantine": {
        "roles": ["super_admin", "org_admin"],
        "permissions": ["file:read"]
    },
    "/dashboard/security": {
        "roles": ["super_admin", "org_admin"],
        "permissions": []
    },
    "/dashboard/system-logs": {
        "roles": ["super_admin"],
        "permissions": ["system:admin"]
    },
    "/dashboard/team": {
        "roles": ["super_admin", "org_admin", "manager"],
        "permissions": ["user:read"]
    }
}


# Actions and their required permissions
# Note: Permission values use format "file:read" (lowercase with colon)
ACTION_PERMISSIONS = {
    "upload_file": {
        "roles": ["super_admin", "org_admin", "manager", "user"],
        "permissions": ["file:write"]
    },
    "download_file": {
        "roles": ["super_admin", "org_admin", "manager", "user", "viewer"],
        "permissions": ["file:read"]
    },
    "delete_file": {
        "roles": ["super_admin", "org_admin", "manager", "user"],
        "permissions": ["file:delete"]
    },
    "share_file": {
        "roles": ["super_admin", "org_admin", "manager", "user"],
        "permissions": ["file:share"]
    },
    "manage_users": {
        "roles": ["super_admin", "org_admin"],
        "permissions": ["user:write"]
    },
    "view_all_files": {
        "roles": ["super_admin", "org_admin"],
        "permissions": ["file:read"]
    },
    "search_files": {
        "roles": ["super_admin", "org_admin", "manager", "user", "viewer"],
        "permissions": ["file:read"]
    },
    "list_recent_files": {
        "roles": ["super_admin", "org_admin", "manager", "user", "viewer"],
        "permissions": ["file:read"]
    },
    "get_file_info": {
        "roles": ["super_admin", "org_admin", "manager", "user", "viewer"],
        "permissions": ["file:read"]
    }
}


def can_access_path(user_context: UserContext, path: str) -> bool:
    """
    Check if user can access a navigation path.
    
    Args:
        user_context: User's context with role and permissions
        path: Navigation path to check
        
    Returns:
        True if user can access the path
    """
    perms = NAVIGATION_PERMISSIONS.get(path)
    
    if perms is None:
        # Unknown path - deny by default for security
        logger.warning(f"Unknown path access check: {path}")
        return False
    
    # Check role
    if user_context.role not in perms["roles"]:
        return False
    
    # Check specific permissions if required
    required_perms = perms.get("permissions", [])
    if required_perms:
        user_perms = set(user_context.permissions)
        if not all(p in user_perms for p in required_perms):
            return False
    
    return True


def can_perform_action(user_context: UserContext, action: str) -> bool:
    """
    Check if user can perform an action.
    
    Args:
        user_context: User's context with role and permissions
        action: Action name to check
        
    Returns:
        True if user can perform the action
    """
    perms = ACTION_PERMISSIONS.get(action)
    
    if perms is None:
        # Unknown action - deny by default for security
        logger.warning(f"Unknown action permission check: {action}")
        return False
    
    # Check role
    if user_context.role not in perms["roles"]:
        return False
    
    # Check specific permissions if required
    required_perms = perms.get("permissions", [])
    if required_perms:
        user_perms = set(user_context.permissions)
        if not all(p in user_perms for p in required_perms):
            return False
    
    return True


def filter_actions(actions: List[ChatAction], user_context: UserContext) -> List[ChatAction]:
    """
    Filter actions based on user permissions.
    
    Removes any actions the user is not permitted to perform.
    
    Args:
        actions: List of actions from chatbot
        user_context: User's context
        
    Returns:
        Filtered list of permitted actions
    """
    filtered = []
    
    for action in actions:
        if action.type == ActionType.NAVIGATE:
            path = action.payload.get("path", "")
            if can_access_path(user_context, path):
                filtered.append(action)
            else:
                logger.debug(f"Filtered navigation to {path} for user {user_context.email}")
                
        elif action.type == ActionType.EXECUTE:
            action_name = action.payload.get("action", "")
            if can_perform_action(user_context, action_name):
                filtered.append(action)
            else:
                logger.debug(f"Filtered action {action_name} for user {user_context.email}")
                
        elif action.type == ActionType.CONFIRM:
            action_name = action.payload.get("action", "")
            if can_perform_action(user_context, action_name):
                filtered.append(action)
                
        else:
            # INFO and ERROR actions always allowed
            filtered.append(action)
    
    return filtered


def get_accessible_pages(user_context: UserContext) -> List[Dict[str, str]]:
    """
    Get list of pages accessible to the user.
    
    Args:
        user_context: User's context
        
    Returns:
        List of accessible pages with paths and descriptions
    """
    page_descriptions = {
        "/dashboard": "Main Dashboard",
        "/dashboard/files": "My Files",
        "/dashboard/all-files": "All Platform Files",
        "/dashboard/users": "User Management",
        "/dashboard/settings": "Account Settings",
        "/dashboard/approvals": "Pending Approvals",
        "/dashboard/organizations": "Organization Management",
        "/dashboard/quarantine": "Quarantined Files",
        "/dashboard/team": "Team Members",
        "/dashboard/analytics": "Analytics & Reports",
        "/dashboard/api-keys": "API Keys",
        "/dashboard/infrastructure": "Infrastructure Status",
        "/dashboard/system-logs": "System Logs (Debugging)",
        "/dashboard/database": "Database Management",
        "/dashboard/api-gateway": "API Gateway",
        "/dashboard/security": "Security Settings"
    }
    
    accessible = []
    for path, desc in page_descriptions.items():
        if can_access_path(user_context, path):
            accessible.append({
                "path": path,
                "name": desc
            })
    
    return accessible


def get_allowed_actions(user_context: UserContext) -> List[Dict[str, str]]:
    """
    Get list of actions the user can perform.
    
    Args:
        user_context: User's context
        
    Returns:
        List of allowed actions with names and descriptions
    """
    action_descriptions = {
        "upload_file": "Upload new files",
        "download_file": "Download files",
        "delete_file": "Delete files",
        "share_file": "Share files with others",
        "manage_users": "Manage user accounts",
        "view_all_files": "View all platform files",
        "search_files": "Search for files",
        "list_recent_files": "View recent files",
        "get_file_info": "Get file details"
    }
    
    allowed = []
    for action, desc in action_descriptions.items():
        if can_perform_action(user_context, action):
            allowed.append({
                "action": action,
                "description": desc
            })
    
    return allowed


def build_security_context(user_context: UserContext) -> str:
    """
    Build a security context string for the LLM prompt.
    
    This helps the AI understand what the user can and cannot do.
    """
    pages = get_accessible_pages(user_context)
    actions = get_allowed_actions(user_context)
    
    pages_str = "\n".join([f"- {p['name']} ({p['path']})" for p in pages])
    actions_str = "\n".join([f"- {a['description']}" for a in actions])
    
    return f"""
SECURITY CONTEXT - RESPECT THESE RESTRICTIONS:

User Role: {user_context.role}

Accessible Pages:
{pages_str}

Allowed Actions:
{actions_str}

IMPORTANT: Never suggest navigating to pages or performing actions not listed above.
If the user asks to do something they cannot, politely explain they don't have permission.
"""


class RBACFilter:
    """
    RBAC filter that can be applied to chatbot responses.
    
    Usage:
        filter = RBACFilter(user_context)
        response = filter.apply(chatbot_response)
    """
    
    def __init__(self, user_context: UserContext):
        self.user_context = user_context
        self._accessible_pages = None
        self._allowed_actions = None
    
    @property
    def accessible_pages(self) -> List[Dict[str, str]]:
        if self._accessible_pages is None:
            self._accessible_pages = get_accessible_pages(self.user_context)
        return self._accessible_pages
    
    @property
    def allowed_actions(self) -> List[Dict[str, str]]:
        if self._allowed_actions is None:
            self._allowed_actions = get_allowed_actions(self.user_context)
        return self._allowed_actions
    
    def filter_actions(self, actions: List[ChatAction]) -> List[ChatAction]:
        """Filter actions based on RBAC."""
        return filter_actions(actions, self.user_context)
    
    def can_navigate(self, path: str) -> bool:
        """Check if user can navigate to path."""
        return can_access_path(self.user_context, path)
    
    def can_execute(self, action: str) -> bool:
        """Check if user can execute action."""
        return can_perform_action(self.user_context, action)
    
    def get_security_context(self) -> str:
        """Get security context for LLM."""
        return build_security_context(self.user_context)
