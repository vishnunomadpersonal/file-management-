"""
Security Module - Authentication, Authorization, and Security Utilities.

Implements:
- JWT token generation and validation
- Password hashing with bcrypt
- Role-based access control (RBAC)
- API key authentication
- Rate limiting helpers
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr

# ============================================================================
# CONFIGURATION
# ============================================================================

# JWT Settings - Load from environment with secure defaults
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# API Key Settings
API_KEY_HEADER = "X-API-Key"
API_KEYS: Dict[str, Dict[str, Any]] = {}  # Will be loaded from DB/config

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


# ============================================================================
# ENUMS AND MODELS
# ============================================================================

class Role(str, Enum):
    """User roles for RBAC."""
    SUPER_ADMIN = "super_admin"  # Full system access
    ORG_ADMIN = "org_admin"      # Organization admin
    MANAGER = "manager"          # Team/department manager
    USER = "user"                # Regular user
    VIEWER = "viewer"            # Read-only access
    API_SERVICE = "api_service"  # Service-to-service API access


class Permission(str, Enum):
    """Granular permissions."""
    # File permissions
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    FILE_DELETE = "file:delete"
    FILE_SHARE = "file:share"
    
    # User management
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # Organization management
    ORG_READ = "org:read"
    ORG_WRITE = "org:write"
    ORG_ADMIN = "org:admin"
    
    # Pipeline permissions
    PIPELINE_READ = "pipeline:read"
    PIPELINE_EXECUTE = "pipeline:execute"
    PIPELINE_TRAIN = "pipeline:train"
    PIPELINE_ADMIN = "pipeline:admin"
    
    # Analytics
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"
    
    # System administration
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_CONFIG = "system:config"


# Role -> Permissions mapping
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.SUPER_ADMIN: list(Permission),  # All permissions
    
    Role.ORG_ADMIN: [
        Permission.FILE_READ, Permission.FILE_WRITE, Permission.FILE_DELETE, Permission.FILE_SHARE,
        Permission.USER_READ, Permission.USER_WRITE, Permission.USER_DELETE,
        Permission.ORG_READ, Permission.ORG_WRITE, Permission.ORG_ADMIN,
        Permission.PIPELINE_READ, Permission.PIPELINE_EXECUTE, Permission.PIPELINE_TRAIN,
        Permission.ANALYTICS_READ, Permission.ANALYTICS_EXPORT,
    ],
    
    Role.MANAGER: [
        Permission.FILE_READ, Permission.FILE_WRITE, Permission.FILE_DELETE, Permission.FILE_SHARE,
        Permission.USER_READ,
        Permission.ORG_READ,
        Permission.PIPELINE_READ, Permission.PIPELINE_EXECUTE,
        Permission.ANALYTICS_READ,
    ],
    
    Role.USER: [
        Permission.FILE_READ, Permission.FILE_WRITE, Permission.FILE_DELETE,
        Permission.PIPELINE_READ, Permission.PIPELINE_EXECUTE,
        Permission.ANALYTICS_READ,
    ],
    
    Role.VIEWER: [
        Permission.FILE_READ,
        Permission.PIPELINE_READ,
        Permission.ANALYTICS_READ,
    ],
    
    Role.API_SERVICE: [
        Permission.FILE_READ, Permission.FILE_WRITE,
        Permission.PIPELINE_READ, Permission.PIPELINE_EXECUTE,
    ],
}


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    user_id: str
    email: Optional[str] = None
    role: Role
    organization_id: Optional[str] = None
    permissions: List[str] = []
    exp: Optional[datetime] = None


class TokenResponse(BaseModel):
    """Response model for token endpoints."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    role: str


@dataclass
class AuthenticatedUser:
    """Represents an authenticated user in request context."""
    user_id: str
    email: Optional[str]
    role: Role
    organization_id: Optional[str]
    permissions: List[Permission]
    token_type: str  # "bearer" or "api_key"
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions or Permission.SYSTEM_ADMIN in self.permissions
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(self.has_permission(p) for p in permissions)
    
    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Check if user has all specified permissions."""
        return all(self.has_permission(p) for p in permissions)
    
    def can_access_organization(self, org_id: str) -> bool:
        """Check if user can access a specific organization."""
        if self.role == Role.SUPER_ADMIN:
            return True
        return self.organization_id == org_id


# ============================================================================
# PASSWORD UTILITIES
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Note: bcrypt has a 72-byte limit. We truncate if necessary.
    """
    # Truncate to 72 bytes if needed (bcrypt limit)
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    # Apply same truncation for verification
    password_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


# ============================================================================
# JWT TOKEN UTILITIES
# ============================================================================

def create_access_token(
    user_id: str,
    email: Optional[str],
    role: Role,
    organization_id: Optional[str] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Get permissions for role
    permissions = [p.value for p in ROLE_PERMISSIONS.get(role, [])]
    
    to_encode = {
        "sub": user_id,
        "email": email,
        "role": role.value,
        "org_id": organization_id,
        "permissions": permissions,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenData:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenData(
            user_id=user_id,
            email=payload.get("email"),
            role=Role(payload.get("role", "user")),
            organization_id=payload.get("org_id"),
            permissions=payload.get("permissions", []),
            exp=datetime.fromtimestamp(payload.get("exp", 0))
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_refresh_token(token: str) -> str:
    """Verify a refresh token and return the user ID."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )


# ============================================================================
# API KEY UTILITIES
# ============================================================================

def generate_api_key() -> str:
    """Generate a new API key."""
    return f"sk_{secrets.token_urlsafe(32)}"


def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Validate an API key and return associated data."""
    # In production, this would query the database
    return API_KEYS.get(api_key)


# ============================================================================
# FASTAPI DEPENDENCIES
# ============================================================================

async def get_current_user(
    bearer_token: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header)
) -> AuthenticatedUser:
    """
    Get the current authenticated user from JWT token or API key.
    
    This is the main authentication dependency used across the API.
    """
    # Try Bearer token first
    if bearer_token:
        token_data = decode_token(bearer_token.credentials)
        return AuthenticatedUser(
            user_id=token_data.user_id,
            email=token_data.email,
            role=token_data.role,
            organization_id=token_data.organization_id,
            permissions=[Permission(p) for p in token_data.permissions if p in [e.value for e in Permission]],
            token_type="bearer"
        )
    
    # Try API key
    if api_key:
        key_data = validate_api_key(api_key)
        if key_data:
            role = Role(key_data.get("role", "api_service"))
            return AuthenticatedUser(
                user_id=key_data.get("user_id", "api_service"),
                email=key_data.get("email"),
                role=role,
                organization_id=key_data.get("organization_id"),
                permissions=ROLE_PERMISSIONS.get(role, []),
                token_type="api_key"
            )
    
    # No valid authentication provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Provide a valid Bearer token or API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_optional(
    bearer_token: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header)
) -> Optional[AuthenticatedUser]:
    """Get current user if authenticated, otherwise return None."""
    try:
        return await get_current_user(bearer_token, api_key)
    except HTTPException:
        return None


def require_permissions(*required_permissions: Permission):
    """
    Dependency factory that requires specific permissions.
    
    Usage:
        @router.get("/admin", dependencies=[Depends(require_permissions(Permission.SYSTEM_ADMIN))])
        async def admin_endpoint():
            ...
    """
    async def permission_checker(
        current_user: AuthenticatedUser = Depends(get_current_user)
    ) -> AuthenticatedUser:
        if not current_user.has_all_permissions(list(required_permissions)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {[p.value for p in required_permissions]}"
            )
        return current_user
    
    return permission_checker


def require_any_permission(*required_permissions: Permission):
    """Dependency factory that requires any of the specified permissions."""
    async def permission_checker(
        current_user: AuthenticatedUser = Depends(get_current_user)
    ) -> AuthenticatedUser:
        if not current_user.has_any_permission(list(required_permissions)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {[p.value for p in required_permissions]}"
            )
        return current_user
    
    return permission_checker


def require_role(*allowed_roles: Role):
    """Dependency factory that requires specific roles."""
    async def role_checker(
        current_user: AuthenticatedUser = Depends(get_current_user)
    ) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required one of: {[r.value for r in allowed_roles]}"
            )
        return current_user
    
    return role_checker


# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimiter:
    """
    Simple in-memory rate limiter.
    
    In production, use Redis-based rate limiting for distributed systems.
    """
    
    def __init__(self):
        self.requests: Dict[str, List[datetime]] = {}
    
    def is_allowed(
        self, 
        key: str, 
        max_requests: int, 
        window_seconds: int
    ) -> bool:
        """Check if a request is allowed under rate limit."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)
        
        # Clean old requests
        if key in self.requests:
            self.requests[key] = [
                t for t in self.requests[key] 
                if t > window_start
            ]
        else:
            self.requests[key] = []
        
        # Check limit
        if len(self.requests[key]) >= max_requests:
            return False
        
        # Record this request
        self.requests[key].append(now)
        return True
    
    def get_retry_after(self, key: str, window_seconds: int) -> int:
        """Get seconds until rate limit resets."""
        if key not in self.requests or not self.requests[key]:
            return 0
        
        oldest = min(self.requests[key])
        reset_time = oldest + timedelta(seconds=window_seconds)
        remaining = (reset_time - datetime.utcnow()).total_seconds()
        return max(0, int(remaining))


# Global rate limiter instance
rate_limiter = RateLimiter()


def create_rate_limit_dependency(max_requests: int, window_seconds: int):
    """Create a rate limiting dependency."""
    async def rate_limit_check(
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user)
    ):
        # Use user ID as rate limit key
        key = f"rate_limit:{current_user.user_id}"
        
        if not rate_limiter.is_allowed(key, max_requests, window_seconds):
            retry_after = rate_limiter.get_retry_after(key, window_seconds)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )
        
        return current_user
    
    return rate_limit_check


# Common rate limits
rate_limit_standard = create_rate_limit_dependency(100, 60)  # 100 req/min
rate_limit_strict = create_rate_limit_dependency(10, 60)      # 10 req/min
rate_limit_training = create_rate_limit_dependency(1, 3600)   # 1 req/hour
