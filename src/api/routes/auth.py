"""
Authentication Routes - Login, Register, Token Management.

Provides:
- User registration
- Login (email/password)
- Token refresh
- Password reset
- Email verification
- Logout
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime, timedelta
import secrets
import logging

from infrastructure.db.mysql import mysql
from repositories.user_repository import UserRepo
from services.user_service import UserService
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    decode_token,
    get_current_user,
    AuthenticatedUser,
    Role,
    TokenResponse,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    rate_limiter
)
from api.responses.response import SuccessResponse, ErrorResponse
from entities.user import User
from entities.organization import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["authentication"]
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class RegisterRequest(BaseModel):
    """User registration request."""
    name: str
    email: EmailStr
    password: str
    organization_name: Optional[str] = None  # If creating new org
    organization_id: Optional[str] = None    # If joining existing org
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters')
        if len(v) > 100:
            raise ValueError('Name must be less than 100 characters')
        return v.strip()


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str
    remember_me: bool = False


class RefreshTokenRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class ChangePasswordRequest(BaseModel):
    """Change password request for logged-in users."""
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserProfile(BaseModel):
    """User profile response."""
    id: str
    name: str
    email: str
    role: str
    organization_id: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_db():
    return next(mysql.get_db())


def log_audit(
    db: Session,
    action: str,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success",
    error_message: Optional[str] = None
):
    """Log an audit entry."""
    try:
        audit = AuditLog(
            action=action,
            user_id=user_id,
            user_email=user_email,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log audit: {e}")


def get_client_ip(request: Request) -> str:
    """Get client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/register", response_model=SuccessResponse[TokenResponse])
async def register(
    request: Request,
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user.
    
    Creates a new user account with email/password authentication.
    Optionally creates a new organization or joins an existing one.
    """
    # Check rate limit (5 registrations per IP per hour)
    ip = get_client_ip(request)
    if not rate_limiter.is_allowed(f"register:{ip}", 5, 3600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later."
        )
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        log_audit(
            db, "user.register.failed", 
            user_email=data.email,
            ip_address=ip,
            status="failure",
            error_message="Email already exists"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create organization if needed
    organization_id = data.organization_id
    if data.organization_name and not organization_id:
        from entities.organization import Organization
        import re
        
        # Generate slug from name
        slug = re.sub(r'[^a-z0-9]+', '-', data.organization_name.lower()).strip('-')
        
        # Check if slug exists
        existing_org = db.query(Organization).filter(Organization.slug == slug).first()
        if existing_org:
            slug = f"{slug}-{secrets.token_hex(4)}"
        
        org = Organization(
            name=data.organization_name,
            slug=slug,
            email=data.email
        )
        db.add(org)
        db.flush()
        organization_id = org.id
    
    # Create user
    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        organization_id=organization_id,
        role="org_admin" if data.organization_name else "user",  # First user of org is admin
        is_active=True,
        verification_token=secrets.token_urlsafe(32)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate tokens
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=Role(user.role),
        organization_id=user.organization_id
    )
    refresh_token = create_refresh_token(user_id=user.id)
    
    # Log audit
    log_audit(
        db, "user.register",
        user_id=user.id,
        user_email=user.email,
        resource_type="user",
        resource_id=user.id,
        ip_address=ip,
        details={"organization_id": organization_id}
    )
    
    logger.info(f"New user registered: {user.email}")
    
    return SuccessResponse(data=TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        role=user.role
    ))


@router.post("/login", response_model=SuccessResponse[TokenResponse])
async def login(
    request: Request,
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    
    Returns access and refresh tokens on success.
    """
    ip = get_client_ip(request)
    
    # Check rate limit (10 login attempts per IP per minute)
    if not rate_limiter.is_allowed(f"login:{ip}", 10, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
    
    # Find user
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user:
        log_audit(
            db, "user.login.failed",
            user_email=data.email,
            ip_address=ip,
            status="failure",
            error_message="User not found"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account is locked. Try again after {user.locked_until}"
        )
    
    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Verify password
    if not user.password_hash or not verify_password(data.password, user.password_hash):
        # Increment failed attempts
        attempts = int(user.failed_login_attempts or 0) + 1
        user.failed_login_attempts = str(attempts)
        
        # Lock account after 5 failed attempts
        if attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            db.commit()
            log_audit(
                db, "user.login.locked",
                user_id=user.id,
                user_email=user.email,
                ip_address=ip,
                status="failure",
                error_message=f"Account locked after {attempts} failed attempts"
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account locked due to too many failed attempts. Try again in 15 minutes."
            )
        
        db.commit()
        log_audit(
            db, "user.login.failed",
            user_id=user.id,
            user_email=user.email,
            ip_address=ip,
            status="failure",
            error_message="Invalid password"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Reset failed attempts on successful login
    user.failed_login_attempts = "0"
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = ip
    db.commit()
    
    # Generate tokens
    expires_delta = timedelta(days=7) if data.remember_me else None
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=Role(user.role),
        organization_id=user.organization_id,
        expires_delta=expires_delta
    )
    
    refresh_expires = timedelta(days=30) if data.remember_me else None
    refresh_token = create_refresh_token(user_id=user.id, expires_delta=refresh_expires)
    
    # Log audit
    log_audit(
        db, "user.login",
        user_id=user.id,
        user_email=user.email,
        ip_address=ip,
        user_agent=request.headers.get("User-Agent")
    )
    
    logger.info(f"User logged in: {user.email}")
    
    return SuccessResponse(data=TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        role=user.role
    ))


@router.post("/refresh", response_model=SuccessResponse[TokenResponse])
async def refresh_token(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using a refresh token.
    """
    user_id = verify_refresh_token(data.refresh_token)
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Generate new tokens
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=Role(user.role),
        organization_id=user.organization_id
    )
    new_refresh_token = create_refresh_token(user_id=user.id)
    
    return SuccessResponse(data=TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        role=user.role
    ))


@router.get("/me", response_model=SuccessResponse[UserProfile])
async def get_current_user_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile.
    """
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return SuccessResponse(data=UserProfile(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        organization_id=user.organization_id,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login_at=user.last_login_at
    ))


@router.post("/password/change")
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change password for logged-in user.
    """
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify current password
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    user.password_hash = hash_password(data.new_password)
    user.password_changed_at = datetime.utcnow()
    db.commit()
    
    log_audit(
        db, "user.password.changed",
        user_id=user.id,
        user_email=user.email,
        ip_address=get_client_ip(request)
    )
    
    return SuccessResponse(data={"message": "Password changed successfully"})


@router.post("/password/reset")
async def request_password_reset(
    data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Request password reset email.
    
    Sends a password reset link to the user's email.
    """
    user = db.query(User).filter(User.email == data.email).first()
    
    # Always return success to prevent email enumeration
    if user:
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expires_at = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        
        # In production, send email here
        # background_tasks.add_task(send_reset_email, user.email, reset_token)
        
        logger.info(f"Password reset requested for: {data.email}")
    
    return SuccessResponse(data={
        "message": "If an account with that email exists, a password reset link has been sent."
    })


@router.post("/password/reset/confirm")
async def confirm_password_reset(
    data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Confirm password reset with token.
    """
    user = db.query(User).filter(User.reset_token == data.token).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    if user.reset_token_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    
    # Update password
    user.password_hash = hash_password(data.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    user.password_changed_at = datetime.utcnow()
    user.failed_login_attempts = "0"
    user.locked_until = None
    db.commit()
    
    logger.info(f"Password reset completed for: {user.email}")
    
    return SuccessResponse(data={"message": "Password reset successfully"})


@router.post("/logout")
async def logout(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout current user.
    
    In a production system, this would invalidate the refresh token.
    """
    log_audit(
        db, "user.logout",
        user_id=current_user.user_id,
        ip_address=get_client_ip(request)
    )
    
    # In production, add refresh token to blacklist or delete from DB
    
    return SuccessResponse(data={"message": "Logged out successfully"})
