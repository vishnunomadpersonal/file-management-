"""
Keycloak Admin Service - User and Role Management.

Provides administrative operations:
- User CRUD operations
- Role assignments
- Group management
- Password reset
- MFA management
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr

from core.keycloak import get_keycloak_settings, KeycloakSettings

logger = logging.getLogger(__name__)


# ============================================================================
# MODELS
# ============================================================================

class KeycloakUser(BaseModel):
    """Keycloak user representation."""
    id: Optional[str] = None
    username: str
    email: Optional[str] = None
    email_verified: bool = False
    enabled: bool = True
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    attributes: Optional[Dict[str, List[str]]] = None
    realm_roles: Optional[List[str]] = None
    groups: Optional[List[str]] = None
    created_timestamp: Optional[int] = None


class CreateUserRequest(BaseModel):
    """Request to create a new user in Keycloak."""
    email: EmailStr
    username: Optional[str] = None  # Defaults to email
    first_name: str
    last_name: str
    password: str
    temporary_password: bool = False
    email_verified: bool = False
    enabled: bool = True
    roles: List[str] = ["user"]
    organization_id: Optional[str] = None
    groups: Optional[List[str]] = None


class UpdateUserRequest(BaseModel):
    """Request to update a user in Keycloak."""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    enabled: Optional[bool] = None
    email_verified: Optional[bool] = None
    organization_id: Optional[str] = None


class SetPasswordRequest(BaseModel):
    """Request to set user password."""
    password: str
    temporary: bool = False


class KeycloakRole(BaseModel):
    """Keycloak role representation."""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    composite: bool = False


class KeycloakGroup(BaseModel):
    """Keycloak group representation."""
    id: Optional[str] = None
    name: str
    path: Optional[str] = None
    sub_groups: Optional[List['KeycloakGroup']] = None


# ============================================================================
# KEYCLOAK ADMIN CLIENT
# ============================================================================

class KeycloakAdminClient:
    """
    Keycloak Admin Client for user and role management.
    
    Uses Keycloak Admin REST API with service account authentication.
    """
    
    def __init__(self, settings: Optional[KeycloakSettings] = None):
        self.settings = settings or get_keycloak_settings()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._admin_token: Optional[str] = None
        self._token_expires_at: int = 0
    
    async def get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                verify=self.settings.verify_ssl,
                timeout=30.0
            )
        return self._http_client
    
    async def close(self):
        """Close HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
    
    async def _get_admin_token(self) -> str:
        """
        Get admin access token for Keycloak Admin API.
        
        Uses client credentials or password grant depending on configuration.
        """
        import time
        
        # Return cached token if still valid
        if self._admin_token and self._token_expires_at > time.time() + 60:
            return self._admin_token
        
        client = await self.get_http_client()
        
        # Try to authenticate with admin credentials
        token_url = f"{self.settings.server_url}/realms/master/protocol/openid-connect/token"
        
        data = {
            "grant_type": "password",
            "client_id": self.settings.admin_client_id,
            "username": self.settings.admin_username,
            "password": self.settings.admin_password,
        }
        
        try:
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get admin token: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to authenticate with Keycloak admin"
                )
            
            token_data = response.json()
            self._admin_token = token_data["access_token"]
            self._token_expires_at = time.time() + token_data.get("expires_in", 300)
            
            return self._admin_token
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Admin token error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Keycloak admin service unavailable"
            )
    
    async def _admin_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Optional[Any]:
        """Make authenticated request to Keycloak Admin API."""
        token = await self._get_admin_token()
        client = await self.get_http_client()
        
        url = f"{self.settings.admin_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await client.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                headers=headers
            )
            
            if response.status_code == 401:
                # Token might be expired, retry once
                self._admin_token = None
                token = await self._get_admin_token()
                headers["Authorization"] = f"Bearer {token}"
                response = await client.request(
                    method=method,
                    url=url,
                    json=json_data,
                    params=params,
                    headers=headers
                )
            
            if response.status_code == 404:
                return None
            
            if response.status_code == 409:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Resource already exists"
                )
            
            if response.status_code >= 400:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("errorMessage", error_detail)
                except:
                    pass
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )
            
            if response.status_code == 204:
                return None
            
            if response.status_code == 201:
                # Created - get ID from Location header
                location = response.headers.get("Location", "")
                if location:
                    return {"id": location.split("/")[-1]}
                return None
            
            if response.content:
                return response.json()
            return None
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Admin request failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Keycloak admin service unavailable"
            )
    
    # ========================================================================
    # USER OPERATIONS
    # ========================================================================
    
    async def create_user(self, user_data: CreateUserRequest) -> str:
        """
        Create a new user in Keycloak.
        
        Returns:
            User ID of the created user
        """
        username = user_data.username or user_data.email
        
        payload = {
            "username": username,
            "email": user_data.email,
            "emailVerified": user_data.email_verified,
            "enabled": user_data.enabled,
            "firstName": user_data.first_name,
            "lastName": user_data.last_name,
            "credentials": [
                {
                    "type": "password",
                    "value": user_data.password,
                    "temporary": user_data.temporary_password
                }
            ],
            "attributes": {}
        }
        
        if user_data.organization_id:
            payload["attributes"]["organization_id"] = [user_data.organization_id]
        
        result = await self._admin_request("POST", "users", json_data=payload)
        
        if not result or "id" not in result:
            # User created but no ID returned, fetch by username
            user = await self.get_user_by_username(username)
            if user:
                user_id = user.id
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="User created but ID not found"
                )
        else:
            user_id = result["id"]
        
        # Assign roles
        if user_data.roles:
            for role_name in user_data.roles:
                try:
                    await self.assign_role(user_id, role_name)
                except Exception as e:
                    logger.warning(f"Failed to assign role {role_name}: {e}")
        
        # Assign to groups
        if user_data.groups:
            for group_path in user_data.groups:
                try:
                    await self.add_user_to_group(user_id, group_path)
                except Exception as e:
                    logger.warning(f"Failed to add to group {group_path}: {e}")
        
        logger.info(f"Created user: {username} (ID: {user_id})")
        return user_id
    
    async def get_user(self, user_id: str) -> Optional[KeycloakUser]:
        """Get user by ID."""
        result = await self._admin_request("GET", f"users/{user_id}")
        
        if not result:
            return None
        
        return KeycloakUser(
            id=result.get("id"),
            username=result.get("username"),
            email=result.get("email"),
            email_verified=result.get("emailVerified", False),
            enabled=result.get("enabled", True),
            first_name=result.get("firstName"),
            last_name=result.get("lastName"),
            attributes=result.get("attributes"),
            created_timestamp=result.get("createdTimestamp"),
        )
    
    async def get_user_by_email(self, email: str) -> Optional[KeycloakUser]:
        """Get user by email."""
        result = await self._admin_request(
            "GET", "users",
            params={"email": email, "exact": "true"}
        )
        
        if not result or len(result) == 0:
            return None
        
        user_data = result[0]
        return KeycloakUser(
            id=user_data.get("id"),
            username=user_data.get("username"),
            email=user_data.get("email"),
            email_verified=user_data.get("emailVerified", False),
            enabled=user_data.get("enabled", True),
            first_name=user_data.get("firstName"),
            last_name=user_data.get("lastName"),
            attributes=user_data.get("attributes"),
            created_timestamp=user_data.get("createdTimestamp"),
        )
    
    async def get_user_by_username(self, username: str) -> Optional[KeycloakUser]:
        """Get user by username."""
        result = await self._admin_request(
            "GET", "users",
            params={"username": username, "exact": "true"}
        )
        
        if not result or len(result) == 0:
            return None
        
        user_data = result[0]
        return KeycloakUser(
            id=user_data.get("id"),
            username=user_data.get("username"),
            email=user_data.get("email"),
            email_verified=user_data.get("emailVerified", False),
            enabled=user_data.get("enabled", True),
            first_name=user_data.get("firstName"),
            last_name=user_data.get("lastName"),
            attributes=user_data.get("attributes"),
            created_timestamp=user_data.get("createdTimestamp"),
        )
    
    async def update_user(self, user_id: str, user_data: UpdateUserRequest) -> bool:
        """Update user details."""
        payload = {}
        
        if user_data.email is not None:
            payload["email"] = user_data.email
        if user_data.first_name is not None:
            payload["firstName"] = user_data.first_name
        if user_data.last_name is not None:
            payload["lastName"] = user_data.last_name
        if user_data.enabled is not None:
            payload["enabled"] = user_data.enabled
        if user_data.email_verified is not None:
            payload["emailVerified"] = user_data.email_verified
        if user_data.organization_id is not None:
            payload["attributes"] = {"organization_id": [user_data.organization_id]}
        
        await self._admin_request("PUT", f"users/{user_id}", json_data=payload)
        return True
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user by ID."""
        await self._admin_request("DELETE", f"users/{user_id}")
        logger.info(f"Deleted user: {user_id}")
        return True
    
    async def list_users(
        self,
        first: int = 0,
        max_results: int = 100,
        search: Optional[str] = None,
        email: Optional[str] = None,
        enabled: Optional[bool] = None
    ) -> List[KeycloakUser]:
        """List users with pagination and filtering."""
        params = {
            "first": first,
            "max": max_results
        }
        
        if search:
            params["search"] = search
        if email:
            params["email"] = email
        if enabled is not None:
            params["enabled"] = str(enabled).lower()
        
        result = await self._admin_request("GET", "users", params=params)
        
        if not result:
            return []
        
        return [
            KeycloakUser(
                id=u.get("id"),
                username=u.get("username"),
                email=u.get("email"),
                email_verified=u.get("emailVerified", False),
                enabled=u.get("enabled", True),
                first_name=u.get("firstName"),
                last_name=u.get("lastName"),
                attributes=u.get("attributes"),
                created_timestamp=u.get("createdTimestamp"),
            )
            for u in result
        ]
    
    async def count_users(self) -> int:
        """Get total user count."""
        result = await self._admin_request("GET", "users/count")
        return result if isinstance(result, int) else 0
    
    # ========================================================================
    # PASSWORD OPERATIONS
    # ========================================================================
    
    async def set_password(
        self,
        user_id: str,
        password: str,
        temporary: bool = False
    ) -> bool:
        """Set user password."""
        payload = {
            "type": "password",
            "value": password,
            "temporary": temporary
        }
        
        await self._admin_request(
            "PUT",
            f"users/{user_id}/reset-password",
            json_data=payload
        )
        return True
    
    async def send_password_reset_email(self, user_id: str) -> bool:
        """Send password reset email to user."""
        await self._admin_request(
            "PUT",
            f"users/{user_id}/execute-actions-email",
            json_data=["UPDATE_PASSWORD"]
        )
        return True
    
    async def send_verify_email(self, user_id: str) -> bool:
        """Send email verification to user."""
        await self._admin_request(
            "PUT",
            f"users/{user_id}/send-verify-email"
        )
        return True
    
    # ========================================================================
    # ROLE OPERATIONS
    # ========================================================================
    
    async def get_realm_roles(self) -> List[KeycloakRole]:
        """Get all realm roles."""
        result = await self._admin_request("GET", "roles")
        
        if not result:
            return []
        
        return [
            KeycloakRole(
                id=r.get("id"),
                name=r.get("name"),
                description=r.get("description"),
                composite=r.get("composite", False)
            )
            for r in result
        ]
    
    async def get_role_by_name(self, role_name: str) -> Optional[KeycloakRole]:
        """Get realm role by name."""
        result = await self._admin_request("GET", f"roles/{role_name}")
        
        if not result:
            return None
        
        return KeycloakRole(
            id=result.get("id"),
            name=result.get("name"),
            description=result.get("description"),
            composite=result.get("composite", False)
        )
    
    async def get_user_roles(self, user_id: str) -> List[KeycloakRole]:
        """Get roles assigned to a user."""
        result = await self._admin_request(
            "GET",
            f"users/{user_id}/role-mappings/realm"
        )
        
        if not result:
            return []
        
        return [
            KeycloakRole(
                id=r.get("id"),
                name=r.get("name"),
                description=r.get("description"),
                composite=r.get("composite", False)
            )
            for r in result
        ]
    
    async def assign_role(self, user_id: str, role_name: str) -> bool:
        """Assign a realm role to a user."""
        role = await self.get_role_by_name(role_name)
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role not found: {role_name}"
            )
        
        payload = [{"id": role.id, "name": role.name}]
        
        await self._admin_request(
            "POST",
            f"users/{user_id}/role-mappings/realm",
            json_data=payload
        )
        
        logger.info(f"Assigned role {role_name} to user {user_id}")
        return True
    
    async def remove_role(self, user_id: str, role_name: str) -> bool:
        """Remove a realm role from a user."""
        role = await self.get_role_by_name(role_name)
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role not found: {role_name}"
            )
        
        payload = [{"id": role.id, "name": role.name}]
        
        await self._admin_request(
            "DELETE",
            f"users/{user_id}/role-mappings/realm",
            json_data=payload
        )
        
        logger.info(f"Removed role {role_name} from user {user_id}")
        return True
    
    # ========================================================================
    # GROUP OPERATIONS
    # ========================================================================
    
    async def get_groups(self) -> List[KeycloakGroup]:
        """Get all groups."""
        result = await self._admin_request("GET", "groups")
        
        if not result:
            return []
        
        return [
            KeycloakGroup(
                id=g.get("id"),
                name=g.get("name"),
                path=g.get("path"),
            )
            for g in result
        ]
    
    async def get_group_by_path(self, path: str) -> Optional[KeycloakGroup]:
        """Get group by path (e.g., '/Users')."""
        result = await self._admin_request(
            "GET", "groups",
            params={"search": path}
        )
        
        if not result:
            return None
        
        for g in result:
            if g.get("path") == path:
                return KeycloakGroup(
                    id=g.get("id"),
                    name=g.get("name"),
                    path=g.get("path"),
                )
        
        return None
    
    async def get_user_groups(self, user_id: str) -> List[KeycloakGroup]:
        """Get groups a user belongs to."""
        result = await self._admin_request("GET", f"users/{user_id}/groups")
        
        if not result:
            return []
        
        return [
            KeycloakGroup(
                id=g.get("id"),
                name=g.get("name"),
                path=g.get("path"),
            )
            for g in result
        ]
    
    async def add_user_to_group(self, user_id: str, group_path: str) -> bool:
        """Add user to a group by group path."""
        group = await self.get_group_by_path(group_path)
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group not found: {group_path}"
            )
        
        await self._admin_request(
            "PUT",
            f"users/{user_id}/groups/{group.id}"
        )
        
        logger.info(f"Added user {user_id} to group {group_path}")
        return True
    
    async def remove_user_from_group(self, user_id: str, group_path: str) -> bool:
        """Remove user from a group."""
        group = await self.get_group_by_path(group_path)
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group not found: {group_path}"
            )
        
        await self._admin_request(
            "DELETE",
            f"users/{user_id}/groups/{group.id}"
        )
        
        logger.info(f"Removed user {user_id} from group {group_path}")
        return True
    
    # ========================================================================
    # MFA OPERATIONS
    # ========================================================================
    
    async def get_user_credentials(self, user_id: str) -> List[Dict]:
        """Get user's configured credentials (passwords, OTP, etc.)."""
        result = await self._admin_request("GET", f"users/{user_id}/credentials")
        return result or []
    
    async def delete_credential(self, user_id: str, credential_id: str) -> bool:
        """Delete a user credential (e.g., remove OTP)."""
        await self._admin_request(
            "DELETE",
            f"users/{user_id}/credentials/{credential_id}"
        )
        return True
    
    async def require_mfa(self, user_id: str) -> bool:
        """Require user to configure MFA on next login."""
        await self._admin_request(
            "PUT",
            f"users/{user_id}/execute-actions-email",
            json_data=["CONFIGURE_TOTP"]
        )
        return True
    
    # ========================================================================
    # SESSION OPERATIONS
    # ========================================================================
    
    async def get_user_sessions(self, user_id: str) -> List[Dict]:
        """Get active sessions for a user."""
        result = await self._admin_request("GET", f"users/{user_id}/sessions")
        return result or []
    
    async def logout_user(self, user_id: str) -> bool:
        """Logout user from all sessions."""
        await self._admin_request("POST", f"users/{user_id}/logout")
        logger.info(f"Logged out user: {user_id}")
        return True


# Global admin client instance
_admin_client: Optional[KeycloakAdminClient] = None


def get_keycloak_admin() -> KeycloakAdminClient:
    """Get global Keycloak admin client instance."""
    global _admin_client
    if _admin_client is None:
        _admin_client = KeycloakAdminClient()
    return _admin_client


async def close_keycloak_admin():
    """Close global Keycloak admin client."""
    global _admin_client
    if _admin_client is not None:
        await _admin_client.close()
        _admin_client = None
