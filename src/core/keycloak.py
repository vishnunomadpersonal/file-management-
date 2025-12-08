"""
Keycloak Configuration Module.

Provides OIDC integration with Keycloak for enterprise authentication.
Supports:
- OIDC token validation
- Role-based access control
- Social login integration
- MFA/2FA support
- Session management
"""

import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from functools import lru_cache

import httpx
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode
from pydantic import BaseModel
from fastapi import HTTPException, status, Depends

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

class KeycloakSettings(BaseModel):
    """Keycloak connection settings."""
    server_url: str = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
    realm: str = os.getenv("KEYCLOAK_REALM", "filemanager")
    client_id: str = os.getenv("KEYCLOAK_CLIENT_ID", "filemanager-api")
    client_secret: str = os.getenv("KEYCLOAK_CLIENT_SECRET", "")
    admin_client_id: str = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "admin-cli")
    admin_username: str = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
    verify_ssl: bool = os.getenv("KEYCLOAK_VERIFY_SSL", "false").lower() == "true"
    enabled: bool = os.getenv("KEYCLOAK_ENABLED", "true").lower() == "true"
    
    # URLs derived from server_url and realm
    @property
    def issuer(self) -> str:
        return f"{self.server_url}/realms/{self.realm}"
    
    @property
    def authorization_endpoint(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/auth"
    
    @property
    def token_endpoint(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/token"
    
    @property
    def userinfo_endpoint(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/userinfo"
    
    @property
    def logout_endpoint(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/logout"
    
    @property
    def jwks_uri(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/certs"
    
    @property
    def introspection_endpoint(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/token/introspect"
    
    @property
    def admin_url(self) -> str:
        return f"{self.server_url}/admin/realms/{self.realm}"


@lru_cache()
def get_keycloak_settings() -> KeycloakSettings:
    """Get cached Keycloak settings."""
    return KeycloakSettings()


# ============================================================================
# TOKEN MODELS
# ============================================================================

@dataclass
class KeycloakToken:
    """Decoded Keycloak token data."""
    sub: str                          # User ID in Keycloak
    email: Optional[str] = None
    email_verified: bool = False
    preferred_username: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    name: Optional[str] = None
    roles: List[str] = None           # Realm roles
    permissions: List[str] = None     # Client roles
    organization_id: Optional[str] = None
    groups: List[str] = None
    azp: Optional[str] = None         # Authorized party (client_id)
    scope: Optional[str] = None
    exp: int = 0
    iat: int = 0
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = []
        if self.permissions is None:
            self.permissions = []
        if self.groups is None:
            self.groups = []
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific realm role."""
        return role in self.roles or "super_admin" in self.roles
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(self.has_role(r) for r in roles)
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific client permission."""
        return permission in self.permissions or "super_admin" in self.roles
    
    def has_any_permission(self, permissions: List[str]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(self.has_permission(p) for p in permissions)


class TokenResponse(BaseModel):
    """OAuth2 token response."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    refresh_expires_in: Optional[int] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None
    not_before_policy: Optional[int] = None
    session_state: Optional[str] = None


class UserInfo(BaseModel):
    """User info response from Keycloak."""
    sub: str
    email: Optional[str] = None
    email_verified: bool = False
    preferred_username: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    name: Optional[str] = None
    groups: Optional[List[str]] = None


# ============================================================================
# KEYCLOAK CLIENT
# ============================================================================

class KeycloakClient:
    """
    Keycloak client for authentication operations.
    
    Provides methods for:
    - Token validation
    - User authentication
    - Token refresh
    - User info retrieval
    """
    
    def __init__(self, settings: Optional[KeycloakSettings] = None):
        self.settings = settings or get_keycloak_settings()
        self._jwks_cache: Optional[Dict[str, Any]] = None
        self._http_client: Optional[httpx.AsyncClient] = None
    
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
    
    async def get_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from Keycloak."""
        if self._jwks_cache is not None:
            return self._jwks_cache
        
        client = await self.get_http_client()
        try:
            response = await client.get(self.settings.jwks_uri)
            response.raise_for_status()
            self._jwks_cache = response.json()
            return self._jwks_cache
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )
    
    def clear_jwks_cache(self):
        """Clear JWKS cache to force refresh."""
        self._jwks_cache = None
    
    async def validate_token(self, token: str) -> KeycloakToken:
        """
        Validate a Keycloak access token.
        
        Args:
            token: JWT access token
            
        Returns:
            KeycloakToken with decoded claims
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Get JWKS for signature verification
            jwks = await self.get_jwks()
            
            # Get unverified headers to find key
            unverified_headers = jwt.get_unverified_headers(token)
            kid = unverified_headers.get("kid")
            
            # Find matching key
            rsa_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    rsa_key = key
                    break
            
            if not rsa_key:
                # Try refreshing JWKS cache
                self.clear_jwks_cache()
                jwks = await self.get_jwks()
                for key in jwks.get("keys", []):
                    if key.get("kid") == kid:
                        rsa_key = key
                        break
            
            if not rsa_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to find appropriate key"
                )
            
            # Decode and verify token
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=self.settings.client_id,
                issuer=self.settings.issuer,
                options={
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_exp": True,
                }
            )
            
            # Extract roles and permissions
            realm_access = payload.get("realm_access", {})
            realm_roles = realm_access.get("roles", [])
            
            resource_access = payload.get("resource_access", {})
            client_access = resource_access.get(self.settings.client_id, {})
            client_roles = client_access.get("roles", [])
            
            # Also check for roles claim (from mapper)
            roles_claim = payload.get("roles", [])
            permissions_claim = payload.get("permissions", [])
            
            return KeycloakToken(
                sub=payload.get("sub"),
                email=payload.get("email"),
                email_verified=payload.get("email_verified", False),
                preferred_username=payload.get("preferred_username"),
                given_name=payload.get("given_name"),
                family_name=payload.get("family_name"),
                name=payload.get("name"),
                roles=list(set(realm_roles + roles_claim)),
                permissions=list(set(client_roles + permissions_claim)),
                organization_id=payload.get("organization_id"),
                groups=payload.get("groups", []),
                azp=payload.get("azp"),
                scope=payload.get("scope"),
                exp=payload.get("exp", 0),
                iat=payload.get("iat", 0),
            )
            
        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def authenticate(
        self,
        username: str,
        password: str,
        scope: str = "openid profile email"
    ) -> TokenResponse:
        """
        Authenticate user with username/password.
        
        Args:
            username: User's email or username
            password: User's password
            scope: OAuth2 scopes
            
        Returns:
            TokenResponse with access and refresh tokens
        """
        client = await self.get_http_client()
        
        data = {
            "grant_type": "password",
            "client_id": self.settings.client_id,
            "client_secret": self.settings.client_secret,
            "username": username,
            "password": password,
            "scope": scope,
        }
        
        try:
            response = await client.post(
                self.settings.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
            
            response.raise_for_status()
            return TokenResponse(**response.json())
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )
    
    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            TokenResponse with new access and refresh tokens
        """
        client = await self.get_http_client()
        
        data = {
            "grant_type": "refresh_token",
            "client_id": self.settings.client_id,
            "client_secret": self.settings.client_secret,
            "refresh_token": refresh_token,
        }
        
        try:
            response = await client.post(
                self.settings.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 400:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token"
                )
            
            response.raise_for_status()
            return TokenResponse(**response.json())
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )
    
    async def get_user_info(self, access_token: str) -> UserInfo:
        """
        Get user info from Keycloak.
        
        Args:
            access_token: Valid access token
            
        Returns:
            UserInfo with user details
        """
        client = await self.get_http_client()
        
        try:
            response = await client.get(
                self.settings.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid access token"
                )
            
            response.raise_for_status()
            return UserInfo(**response.json())
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )
    
    async def logout(self, refresh_token: str) -> bool:
        """
        Logout user by invalidating refresh token.
        
        Args:
            refresh_token: Refresh token to invalidate
            
        Returns:
            True if successful
        """
        client = await self.get_http_client()
        
        data = {
            "client_id": self.settings.client_id,
            "client_secret": self.settings.client_secret,
            "refresh_token": refresh_token,
        }
        
        try:
            response = await client.post(
                self.settings.logout_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            return response.status_code in (200, 204)
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
    
    async def introspect_token(self, token: str) -> Dict[str, Any]:
        """
        Introspect a token to check if it's active.
        
        Args:
            token: Access or refresh token
            
        Returns:
            Introspection response
        """
        client = await self.get_http_client()
        
        data = {
            "client_id": self.settings.client_id,
            "client_secret": self.settings.client_secret,
            "token": token,
        }
        
        try:
            response = await client.post(
                self.settings.introspection_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Token introspection failed: {e}")
            return {"active": False}
    
    def get_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        scope: str = "openid profile email",
        response_type: str = "code",
        **kwargs
    ) -> str:
        """
        Get Keycloak authorization URL for OAuth2 flow.
        
        Args:
            redirect_uri: Callback URL after auth
            state: CSRF state parameter
            scope: OAuth2 scopes
            response_type: OAuth2 response type
            **kwargs: Additional parameters (e.g., kc_idp_hint for social login)
            
        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.settings.client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": scope,
            "response_type": response_type,
        }
        params.update(kwargs)
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.settings.authorization_endpoint}?{query_string}"
    
    async def exchange_code(
        self,
        code: str,
        redirect_uri: str
    ) -> TokenResponse:
        """
        Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from callback
            redirect_uri: Same redirect_uri used in auth request
            
        Returns:
            TokenResponse with tokens
        """
        client = await self.get_http_client()
        
        data = {
            "grant_type": "authorization_code",
            "client_id": self.settings.client_id,
            "client_secret": self.settings.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        
        try:
            response = await client.post(
                self.settings.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 400:
                error = response.json()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error.get("error_description", "Invalid authorization code")
                )
            
            response.raise_for_status()
            return TokenResponse(**response.json())
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Code exchange failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )


# ============================================================================
# GLOBAL INSTANCES AND DEPENDENCY INJECTION
# ============================================================================

# Global Keycloak client instance
_keycloak_client: Optional[KeycloakClient] = None


def get_keycloak_client() -> KeycloakClient:
    """Get global Keycloak client instance."""
    global _keycloak_client
    if _keycloak_client is None:
        _keycloak_client = KeycloakClient()
    return _keycloak_client


async def close_keycloak_client():
    """Close global Keycloak client."""
    global _keycloak_client
    if _keycloak_client is not None:
        await _keycloak_client.close()
        _keycloak_client = None


# Aliases for backward compatibility and cleaner API
KeycloakOIDC = KeycloakClient
KeycloakUser = KeycloakToken


def get_keycloak_oidc() -> KeycloakClient:
    """Alias for get_keycloak_client for OIDC-focused usage."""
    return get_keycloak_client()


# ============================================================================
# FASTAPI DEPENDENCIES
# ============================================================================

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_security = HTTPBearer(auto_error=False)


async def get_current_user_keycloak(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
    keycloak: KeycloakClient = Depends(get_keycloak_client)
) -> KeycloakToken:
    """
    FastAPI dependency to get the current authenticated user from Keycloak token.
    
    Usage:
        @router.get("/protected")
        async def protected_route(user: KeycloakToken = Depends(get_current_user_keycloak)):
            return {"user_id": user.sub, "email": user.email}
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return await keycloak.validate_token(credentials.credentials)


def require_keycloak_role(*required_roles: str):
    """
    FastAPI dependency factory that requires specific Keycloak roles.
    
    Usage:
        @router.get("/admin")
        async def admin_route(user: KeycloakToken = Depends(require_keycloak_role("admin", "super_admin"))):
            return {"message": "Admin access granted"}
    """
    async def role_checker(
        user: KeycloakToken = Depends(get_current_user_keycloak)
    ) -> KeycloakToken:
        if not user.has_any_role(list(required_roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}"
            )
        return user
    
    return role_checker


def require_keycloak_permission(*required_permissions: str):
    """
    FastAPI dependency factory that requires specific Keycloak client permissions.
    
    Usage:
        @router.get("/files")
        async def files_route(user: KeycloakToken = Depends(require_keycloak_permission("files:read"))):
            return {"message": "Access granted"}
    """
    async def permission_checker(
        user: KeycloakToken = Depends(get_current_user_keycloak)
    ) -> KeycloakToken:
        if not user.has_any_permission(list(required_permissions)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required permissions: {', '.join(required_permissions)}"
            )
        return user
    
    return permission_checker