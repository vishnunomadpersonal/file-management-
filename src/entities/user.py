from infrastructure.db.mysql import mysql as db
from sqlalchemy import Column, String, DateTime, VARCHAR, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime


class User(db.Base):
    """
    User entity with authentication support.
    
    Users belong to an organization and have role-based access control.
    """
    __tablename__ = "users"
    
    id = Column(VARCHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic info
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    
    # Authentication
    password_hash = Column(String(255))  # Nullable for OAuth users
    
    # Organization
    organization_id = Column(VARCHAR(36), ForeignKey("organizations.id"), index=True)
    
    # Role and permissions
    role = Column(String(50), default="user")  # super_admin, org_admin, manager, user, viewer
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # OAuth info (for social login)
    oauth_provider = Column(String(50))  # google, github, etc.
    oauth_id = Column(String(255))
    
    # Profile
    avatar_url = Column(String(500))
    bio = Column(Text)
    
    # Security
    failed_login_attempts = Column(VARCHAR(5), default="0")
    locked_until = Column(DateTime)
    last_login_at = Column(DateTime)
    last_login_ip = Column(String(45))
    password_changed_at = Column(DateTime)
    
    # Email verification
    email_verified_at = Column(DateTime)
    verification_token = Column(String(255))
    
    # Password reset
    reset_token = Column(String(255))
    reset_token_expires_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    appointments = relationship("Appointment", back_populates="user", cascade="all, delete-orphan")
    files = relationship("File", back_populates="user", cascade="all, delete-orphan")