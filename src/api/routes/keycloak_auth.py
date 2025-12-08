"""
Keycloak Authentication Routes - OAuth2/OIDC Integration.

Provides:
- Direct login with Keycloak (password grant)
- OAuth2 authorization code flow
- Social login integration (Google, GitHub, Microsoft, etc.)
- Token refresh
- Logout
- User info
"""

import secrets
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from core.keycloak import (
    get_keycloak_client,
    KeycloakClient,
    KeycloakToken,
    TokenResponse,
    UserInfo,
    get_keycloak_settings,
)
from infrastructure.db.mysql import mysql
from api.responses.response import SuccessResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/auth/keycloak",
    tags=["keycloak-authentication"]
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class KeycloakLoginRequest(BaseModel):
    """Login request with Keycloak credentials."""
    email: EmailStr
    password: str
    remember_me: bool = False


class KeycloakTokenResponse(BaseModel):
    """Token response for Keycloak authentication."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int
    refresh_expires_in: Optional[int] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None


class KeycloakRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class KeycloakLogoutRequest(BaseModel):
    """Logout request."""
    refresh_token: str


class SocialLoginProvider(BaseModel):
    """Social login provider info."""
    name: str
    alias: str
    login_url: str


class AuthorizationUrlResponse(BaseModel):
    """OAuth2 authorization URL response."""
    authorization_url: str
    state: str


class CodeExchangeRequest(BaseModel):
    """OAuth2 code exchange request."""
    code: str
    state: str
    redirect_uri: str


class KeycloakUserProfile(BaseModel):
    """User profile from Keycloak."""
    id: str
    email: Optional[str]
    email_verified: bool
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: Optional[str]
    roles: List[str]
    permissions: List[str]
    organization_id: Optional[str]
    groups: List[str]


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

async def get_keycloak() -> KeycloakClient:
    """Get Keycloak client dependency."""
    return get_keycloak_client()


async def get_current_keycloak_user(
    request: Request,
    keycloak: KeycloakClient = Depends(get_keycloak)
) -> KeycloakToken:
    """
    Get current authenticated user from Keycloak token.
    
    Extracts and validates JWT token from Authorization header.
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    return await keycloak.validate_token(token)


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@router.post(
    "/login",
    response_model=KeycloakTokenResponse,
    summary="Login with email and password",
    description="Authenticate user with Keycloak using email and password"
)
async def keycloak_login(
    request: KeycloakLoginRequest,
    keycloak: KeycloakClient = Depends(get_keycloak)
):
    """
    Authenticate user with Keycloak.
    
    Uses the OAuth2 password grant to authenticate directly with Keycloak.
    Returns access token and refresh token.
    """
    try:
        token_response = await keycloak.authenticate(
            username=request.email,
            password=request.password,
            scope="openid profile email offline_access" if request.remember_me else "openid profile email"
        )
        
        logger.info(f"User logged in: {request.email}")
        
        return KeycloakTokenResponse(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            token_type=token_response.token_type,
            expires_in=token_response.expires_in,
            refresh_expires_in=token_response.refresh_expires_in,
            scope=token_response.scope,
            id_token=token_response.id_token,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post(
    "/refresh",
    response_model=KeycloakTokenResponse,
    summary="Refresh access token",
    description="Get new access token using refresh token"
)
async def keycloak_refresh(
    request: KeycloakRefreshRequest,
    keycloak: KeycloakClient = Depends(get_keycloak)
):
    """
    Refresh access token using refresh token.
    
    Returns new access token and optionally new refresh token.
    """
    try:
        token_response = await keycloak.refresh_token(request.refresh_token)
        
        return KeycloakTokenResponse(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            token_type=token_response.token_type,
            expires_in=token_response.expires_in,
            refresh_expires_in=token_response.refresh_expires_in,
            scope=token_response.scope,
            id_token=token_response.id_token,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post(
    "/logout",
    summary="Logout user",
    description="Invalidate refresh token and end session"
)
async def keycloak_logout(
    request: KeycloakLogoutRequest,
    keycloak: KeycloakClient = Depends(get_keycloak)
):
    """
    Logout user by invalidating refresh token.
    
    This ends the Keycloak session and invalidates tokens.
    """
    success = await keycloak.logout(request.refresh_token)
    
    if success:
        return SuccessResponse(
            message="Successfully logged out",
            data={"logged_out": True}
        )
    else:
        return SuccessResponse(
            message="Logout completed",
            data={"logged_out": True, "warning": "Could not fully invalidate server session"}
        )


@router.get(
    "/me",
    response_model=KeycloakUserProfile,
    summary="Get current user profile",
    description="Get profile of currently authenticated user"
)
async def keycloak_me(
    current_user: KeycloakToken = Depends(get_current_keycloak_user)
):
    """
    Get current user's profile from Keycloak token.
    
    Returns user information extracted from the validated JWT token.
    """
    return KeycloakUserProfile(
        id=current_user.sub,
        email=current_user.email,
        email_verified=current_user.email_verified,
        username=current_user.preferred_username,
        first_name=current_user.given_name,
        last_name=current_user.family_name,
        full_name=current_user.name,
        roles=current_user.roles,
        permissions=current_user.permissions,
        organization_id=current_user.organization_id,
        groups=current_user.groups,
    )


@router.get(
    "/userinfo",
    response_model=UserInfo,
    summary="Get user info from Keycloak",
    description="Fetch fresh user info from Keycloak userinfo endpoint"
)
async def keycloak_userinfo(
    request: Request,
    keycloak: KeycloakClient = Depends(get_keycloak)
):
    """
    Get user info directly from Keycloak.
    
    Unlike /me which uses cached token claims, this fetches
    fresh data from Keycloak's userinfo endpoint.
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = auth_header[7:]
    return await keycloak.get_user_info(token)


# ============================================================================
# OAUTH2 AUTHORIZATION CODE FLOW
# ============================================================================

@router.get(
    "/authorize",
    response_model=AuthorizationUrlResponse,
    summary="Get OAuth2 authorization URL",
    description="Get Keycloak authorization URL for browser-based login"
)
async def get_authorization_url(
    redirect_uri: str = Query(..., description="Callback URL after authentication"),
    scope: str = Query("openid profile email", description="OAuth2 scopes"),
    idp_hint: Optional[str] = Query(None, description="Identity provider hint (e.g., 'google', 'github')"),
    keycloak: KeycloakClient = Depends(get_keycloak)
):
    """
    Get Keycloak authorization URL.
    
    Use this URL to redirect users to Keycloak for authentication.
    After successful auth, user will be redirected to redirect_uri with a code.
    
    For social login, use idp_hint parameter:
    - 'google' for Google login
    - 'github' for GitHub login
    - 'microsoft' for Microsoft login
    """
    state = secrets.token_urlsafe(32)
    
    extra_params = {}
    if idp_hint:
        extra_params["kc_idp_hint"] = idp_hint
    
    auth_url = keycloak.get_authorization_url(
        redirect_uri=redirect_uri,
        state=state,
        scope=scope,
        **extra_params
    )
    
    return AuthorizationUrlResponse(
        authorization_url=auth_url,
        state=state
    )


@router.post(
    "/callback",
    response_model=KeycloakTokenResponse,
    summary="Exchange authorization code for tokens",
    description="Exchange OAuth2 authorization code for access and refresh tokens"
)
async def exchange_authorization_code(
    request: CodeExchangeRequest,
    keycloak: KeycloakClient = Depends(get_keycloak)
):
    """
    Exchange authorization code for tokens.
    
    Call this after receiving the authorization code from Keycloak callback.
    """
    try:
        token_response = await keycloak.exchange_code(
            code=request.code,
            redirect_uri=request.redirect_uri
        )
        
        return KeycloakTokenResponse(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            token_type=token_response.token_type,
            expires_in=token_response.expires_in,
            refresh_expires_in=token_response.refresh_expires_in,
            scope=token_response.scope,
            id_token=token_response.id_token,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code exchange failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to exchange authorization code"
        )


@router.get(
    "/callback",
    summary="OAuth2 callback endpoint",
    description="Callback endpoint for OAuth2 authorization code flow"
)
async def oauth2_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter"),
    redirect_uri: str = Query("http://localhost:3000/auth/callback", description="Frontend callback URL"),
    keycloak: KeycloakClient = Depends(get_keycloak)
):
    """
    OAuth2 callback endpoint.
    
    This is called by Keycloak after successful authentication.
    It exchanges the code for tokens and redirects to the frontend.
    """
    try:
        # Note: In production, you should validate the state parameter
        # against a stored value to prevent CSRF attacks
        
        token_response = await keycloak.exchange_code(
            code=code,
            redirect_uri=f"{get_keycloak_settings().server_url.replace('keycloak', 'localhost')}/api/v1/auth/keycloak/callback"
        )
        
        # Redirect to frontend with tokens (or use secure cookie)
        # In production, use secure httpOnly cookies or redirect to frontend
        # which then fetches tokens from a secure endpoint
        frontend_url = f"{redirect_uri}?access_token={token_response.access_token}&refresh_token={token_response.refresh_token}"
        
        return RedirectResponse(url=frontend_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth2 callback failed: {e}")
        return RedirectResponse(url=f"{redirect_uri}?error=authentication_failed")


# ============================================================================
# SOCIAL LOGIN HELPERS
# ============================================================================

@router.get(
    "/social/providers",
    response_model=List[SocialLoginProvider],
    summary="List available social login providers",
    description="Get list of configured social login providers"
)
async def list_social_providers(
    redirect_uri: str = Query("http://localhost:3000/auth/callback", description="Callback URL")
):
    """
    List available social login providers.
    
    Returns configured identity providers with their login URLs.
    """
    settings = get_keycloak_settings()
    keycloak = get_keycloak_client()
    
    # Common social providers that might be configured
    providers = [
        {
            "name": "Google",
            "alias": "google",
            "login_url": keycloak.get_authorization_url(
                redirect_uri=redirect_uri,
                state=secrets.token_urlsafe(16),
                kc_idp_hint="google"
            )
        },
        {
            "name": "GitHub",
            "alias": "github",
            "login_url": keycloak.get_authorization_url(
                redirect_uri=redirect_uri,
                state=secrets.token_urlsafe(16),
                kc_idp_hint="github"
            )
        },
        {
            "name": "Microsoft",
            "alias": "microsoft",
            "login_url": keycloak.get_authorization_url(
                redirect_uri=redirect_uri,
                state=secrets.token_urlsafe(16),
                kc_idp_hint="microsoft"
            )
        },
    ]
    
    return [SocialLoginProvider(**p) for p in providers]


@router.get(
    "/social/{provider}",
    summary="Redirect to social login",
    description="Redirect to social identity provider for login"
)
async def social_login_redirect(
    provider: str,
    redirect_uri: str = Query("http://localhost:3000/auth/callback", description="Callback URL after login")
):
    """
    Redirect to social identity provider.
    
    Supported providers (when configured in Keycloak):
    - google
    - github
    - microsoft
    - facebook
    - twitter
    - linkedin
    """
    keycloak = get_keycloak_client()
    state = secrets.token_urlsafe(32)
    
    auth_url = keycloak.get_authorization_url(
        redirect_uri=redirect_uri,
        state=state,
        scope="openid profile email",
        kc_idp_hint=provider
    )
    
    return RedirectResponse(url=auth_url)


# ============================================================================
# TOKEN INTROSPECTION
# ============================================================================

@router.post(
    "/introspect",
    summary="Introspect token",
    description="Check if a token is active and get its claims"
)
async def introspect_token(
    token: str,
    keycloak: KeycloakClient = Depends(get_keycloak)
):
    """
    Introspect a token.
    
    Returns whether the token is active and its claims.
    """
    result = await keycloak.introspect_token(token)
    return SuccessResponse(
        message="Token introspected",
        data=result
    )


# ============================================================================
# KEYCLOAK HEALTH CHECK
# ============================================================================

@router.get(
    "/health",
    summary="Keycloak health check",
    description="Check if Keycloak is reachable and healthy"
)
async def keycloak_health(
    keycloak: KeycloakClient = Depends(get_keycloak)
):
    """
    Check Keycloak health.
    
    Attempts to fetch JWKS to verify Keycloak is accessible.
    """
    try:
        # Clear cache to force fresh fetch
        keycloak.clear_jwks_cache()
        await keycloak.get_jwks()
        
        settings = get_keycloak_settings()
        
        return SuccessResponse(
            message="Keycloak is healthy",
            data={
                "status": "healthy",
                "server_url": settings.server_url,
                "realm": settings.realm,
                "issuer": settings.issuer
            }
        )
    except Exception as e:
        logger.error(f"Keycloak health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Keycloak is not available: {str(e)}"
        )


# ============================================================================
# CONFIGURATION ENDPOINTS
# ============================================================================

@router.get(
    "/config",
    summary="Get Keycloak configuration",
    description="Get public Keycloak configuration for frontend"
)
async def get_keycloak_config():
    """
    Get public Keycloak configuration.
    
    Returns configuration needed by frontend to initialize Keycloak client.
    """
    settings = get_keycloak_settings()
    
    return {
        "realm": settings.realm,
        "auth_server_url": settings.server_url,
        "client_id": "filemanager-frontend",  # Public client for frontend
        "authorization_endpoint": settings.authorization_endpoint,
        "token_endpoint": settings.token_endpoint,
        "userinfo_endpoint": settings.userinfo_endpoint,
        "logout_endpoint": settings.logout_endpoint,
    }
