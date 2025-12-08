"""
Keycloak User Management Routes - Admin Operations.

Provides administrative endpoints for:
- User CRUD operations
- Role management
- Group management
- Password management
- MFA management
- Session management
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr

from core.keycloak import KeycloakToken
from api.routes.keycloak_auth import get_current_keycloak_user
from services.keycloak_admin_service import (
    get_keycloak_admin,
    KeycloakAdminClient,
    CreateUserRequest,
    UpdateUserRequest,
    KeycloakUser,
    KeycloakRole,
    KeycloakGroup,
)
from api.responses.response import SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/keycloak/users",
    tags=["keycloak-user-management"]
)


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

async def get_admin_client() -> KeycloakAdminClient:
    """Get Keycloak admin client."""
    return get_keycloak_admin()


def require_admin_role(current_user: KeycloakToken = Depends(get_current_keycloak_user)):
    """Require admin role for access."""
    if not current_user.has_any_role(["super_admin", "org_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user


def require_super_admin_role(current_user: KeycloakToken = Depends(get_current_keycloak_user)):
    """Require super admin role for access."""
    if not current_user.has_role("super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin role required"
        )
    return current_user


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class UserListResponse(BaseModel):
    """Response for user list."""
    users: List[KeycloakUser]
    total: int
    page: int
    page_size: int


class RoleAssignmentRequest(BaseModel):
    """Request to assign role to user."""
    role_name: str


class GroupAssignmentRequest(BaseModel):
    """Request to assign user to group."""
    group_path: str


class SetPasswordRequest(BaseModel):
    """Request to set user password."""
    password: str
    temporary: bool = False


# ============================================================================
# USER CRUD ENDPOINTS
# ============================================================================

@router.post(
    "/",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
    description="Create a new user in Keycloak (Admin only)"
)
async def create_user(
    user_data: CreateUserRequest,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """
    Create a new user in Keycloak.
    
    Requires admin role. Org admins can only create users in their organization.
    """
    # Org admins can only create users in their own organization
    if not current_user.has_role("super_admin"):
        if user_data.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only create users in your organization"
            )
        # Org admins can't create super_admins
        if "super_admin" in user_data.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot assign super_admin role"
            )
    
    user_id = await admin.create_user(user_data)
    
    return SuccessResponse(
        message="User created successfully",
        data={"user_id": user_id}
    )


@router.get(
    "/",
    response_model=UserListResponse,
    summary="List users",
    description="List users with pagination and filtering (Admin only)"
)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    email: Optional[str] = Query(None, description="Filter by email"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """
    List users with pagination and filtering.
    
    Org admins only see users in their organization.
    """
    first = (page - 1) * page_size
    
    users = await admin.list_users(
        first=first,
        max_results=page_size,
        search=search,
        email=email,
        enabled=enabled
    )
    
    # Org admins only see their organization's users
    if not current_user.has_role("super_admin") and current_user.organization_id:
        users = [
            u for u in users
            if u.attributes and 
            u.attributes.get("organization_id", [None])[0] == current_user.organization_id
        ]
    
    total = await admin.count_users()
    
    return UserListResponse(
        users=users,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{user_id}",
    response_model=KeycloakUser,
    summary="Get user by ID",
    description="Get user details by ID (Admin only)"
)
async def get_user(
    user_id: str,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Get user by ID."""
    user = await admin.get_user(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Org admins can only view users in their organization
    if not current_user.has_role("super_admin"):
        user_org = (user.attributes or {}).get("organization_id", [None])[0]
        if user_org != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access users outside your organization"
            )
    
    return user


@router.put(
    "/{user_id}",
    response_model=SuccessResponse,
    summary="Update user",
    description="Update user details (Admin only)"
)
async def update_user(
    user_id: str,
    user_data: UpdateUserRequest,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Update user details."""
    # Check user exists and admin has access
    existing = await admin.get_user(user_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Org admins can only update users in their organization
    if not current_user.has_role("super_admin"):
        user_org = (existing.attributes or {}).get("organization_id", [None])[0]
        if user_org != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify users outside your organization"
            )
    
    await admin.update_user(user_id, user_data)
    
    return SuccessResponse(
        message="User updated successfully",
        data={"user_id": user_id}
    )


@router.delete(
    "/{user_id}",
    response_model=SuccessResponse,
    summary="Delete user",
    description="Delete user (Super admin only)"
)
async def delete_user(
    user_id: str,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_super_admin_role)
):
    """Delete user. Requires super admin role."""
    await admin.delete_user(user_id)
    
    return SuccessResponse(
        message="User deleted successfully",
        data={"user_id": user_id}
    )


# ============================================================================
# PASSWORD MANAGEMENT
# ============================================================================

@router.post(
    "/{user_id}/password",
    response_model=SuccessResponse,
    summary="Set user password",
    description="Set password for a user (Admin only)"
)
async def set_user_password(
    user_id: str,
    password_data: SetPasswordRequest,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Set user password."""
    await admin.set_password(
        user_id=user_id,
        password=password_data.password,
        temporary=password_data.temporary
    )
    
    return SuccessResponse(
        message="Password updated successfully",
        data={"user_id": user_id, "temporary": password_data.temporary}
    )


@router.post(
    "/{user_id}/password-reset-email",
    response_model=SuccessResponse,
    summary="Send password reset email",
    description="Send password reset email to user (Admin only)"
)
async def send_password_reset_email(
    user_id: str,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Send password reset email to user."""
    await admin.send_password_reset_email(user_id)
    
    return SuccessResponse(
        message="Password reset email sent",
        data={"user_id": user_id}
    )


@router.post(
    "/{user_id}/verify-email",
    response_model=SuccessResponse,
    summary="Send verification email",
    description="Send email verification to user (Admin only)"
)
async def send_verify_email(
    user_id: str,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Send email verification to user."""
    await admin.send_verify_email(user_id)
    
    return SuccessResponse(
        message="Verification email sent",
        data={"user_id": user_id}
    )


# ============================================================================
# ROLE MANAGEMENT
# ============================================================================

@router.get(
    "/{user_id}/roles",
    response_model=List[KeycloakRole],
    summary="Get user roles",
    description="Get roles assigned to a user (Admin only)"
)
async def get_user_roles(
    user_id: str,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Get roles assigned to a user."""
    return await admin.get_user_roles(user_id)


@router.post(
    "/{user_id}/roles",
    response_model=SuccessResponse,
    summary="Assign role to user",
    description="Assign a role to a user (Admin only)"
)
async def assign_role_to_user(
    user_id: str,
    role_data: RoleAssignmentRequest,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Assign a role to a user."""
    # Org admins can't assign super_admin role
    if not current_user.has_role("super_admin") and role_data.role_name == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign super_admin role"
        )
    
    await admin.assign_role(user_id, role_data.role_name)
    
    return SuccessResponse(
        message=f"Role '{role_data.role_name}' assigned successfully",
        data={"user_id": user_id, "role": role_data.role_name}
    )


@router.delete(
    "/{user_id}/roles/{role_name}",
    response_model=SuccessResponse,
    summary="Remove role from user",
    description="Remove a role from a user (Admin only)"
)
async def remove_role_from_user(
    user_id: str,
    role_name: str,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Remove a role from a user."""
    await admin.remove_role(user_id, role_name)
    
    return SuccessResponse(
        message=f"Role '{role_name}' removed successfully",
        data={"user_id": user_id, "role": role_name}
    )


# ============================================================================
# GROUP MANAGEMENT
# ============================================================================

@router.get(
    "/{user_id}/groups",
    response_model=List[KeycloakGroup],
    summary="Get user groups",
    description="Get groups a user belongs to (Admin only)"
)
async def get_user_groups(
    user_id: str,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Get groups a user belongs to."""
    return await admin.get_user_groups(user_id)


@router.post(
    "/{user_id}/groups",
    response_model=SuccessResponse,
    summary="Add user to group",
    description="Add a user to a group (Admin only)"
)
async def add_user_to_group(
    user_id: str,
    group_data: GroupAssignmentRequest,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Add a user to a group."""
    await admin.add_user_to_group(user_id, group_data.group_path)
    
    return SuccessResponse(
        message=f"User added to group '{group_data.group_path}'",
        data={"user_id": user_id, "group": group_data.group_path}
    )


@router.delete(
    "/{user_id}/groups/{group_path:path}",
    response_model=SuccessResponse,
    summary="Remove user from group",
    description="Remove a user from a group (Admin only)"
)
async def remove_user_from_group(
    user_id: str,
    group_path: str,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Remove a user from a group."""
    # Add leading slash if not present
    if not group_path.startswith("/"):
        group_path = f"/{group_path}"
    
    await admin.remove_user_from_group(user_id, group_path)
    
    return SuccessResponse(
        message=f"User removed from group '{group_path}'",
        data={"user_id": user_id, "group": group_path}
    )


# ============================================================================
# MFA MANAGEMENT
# ============================================================================

@router.get(
    "/{user_id}/credentials",
    summary="Get user credentials",
    description="Get user's configured credentials (Admin only)"
)
async def get_user_credentials(
    user_id: str,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Get user's configured credentials (passwords, OTP, WebAuthn, etc.)."""
    credentials = await admin.get_user_credentials(user_id)
    
    return SuccessResponse(
        message="Credentials retrieved",
        data={"credentials": credentials}
    )


@router.delete(
    "/{user_id}/credentials/{credential_id}",
    response_model=SuccessResponse,
    summary="Delete user credential",
    description="Delete a specific credential (e.g., remove OTP) (Admin only)"
)
async def delete_user_credential(
    user_id: str,
    credential_id: str,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Delete a user credential (e.g., remove OTP configuration)."""
    await admin.delete_credential(user_id, credential_id)
    
    return SuccessResponse(
        message="Credential deleted",
        data={"user_id": user_id, "credential_id": credential_id}
    )


@router.post(
    "/{user_id}/require-mfa",
    response_model=SuccessResponse,
    summary="Require MFA setup",
    description="Require user to configure MFA on next login (Admin only)"
)
async def require_mfa(
    user_id: str,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Require user to configure MFA on next login."""
    await admin.require_mfa(user_id)
    
    return SuccessResponse(
        message="MFA configuration required on next login",
        data={"user_id": user_id}
    )


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

@router.get(
    "/{user_id}/sessions",
    summary="Get user sessions",
    description="Get active sessions for a user (Admin only)"
)
async def get_user_sessions(
    user_id: str,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Get active sessions for a user."""
    sessions = await admin.get_user_sessions(user_id)
    
    return SuccessResponse(
        message="Sessions retrieved",
        data={"sessions": sessions}
    )


@router.post(
    "/{user_id}/logout",
    response_model=SuccessResponse,
    summary="Logout user from all sessions",
    description="Force logout user from all sessions (Admin only)"
)
async def logout_user(
    user_id: str,
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Force logout user from all sessions."""
    await admin.logout_user(user_id)
    
    return SuccessResponse(
        message="User logged out from all sessions",
        data={"user_id": user_id}
    )


# ============================================================================
# REALM-LEVEL ENDPOINTS
# ============================================================================

@router.get(
    "/roles/available",
    response_model=List[KeycloakRole],
    summary="List available roles",
    description="Get all available realm roles (Admin only)"
)
async def list_available_roles(
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Get all available realm roles."""
    return await admin.get_realm_roles()


@router.get(
    "/groups/available",
    response_model=List[KeycloakGroup],
    summary="List available groups",
    description="Get all available groups (Admin only)"
)
async def list_available_groups(
    admin: KeycloakAdminClient = Depends(get_admin_client),
    current_user: KeycloakToken = Depends(require_admin_role)
):
    """Get all available groups."""
    return await admin.get_groups()
