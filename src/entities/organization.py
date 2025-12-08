"""
Organization Entity - Multi-tenant support.

Organizations are the top-level container for users, files, and resources.
Each organization has its own data isolation and quota management.
"""

from infrastructure.db.mysql import mysql as db
from sqlalchemy import Column, String, DateTime, VARCHAR, Integer, Boolean, JSON, Text
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime


class Organization(db.Base):
    """
    Organization entity for multi-tenant support.
    
    Each organization:
    - Has its own users, files, and appointments
    - Has configurable storage quotas
    - Can have custom settings and features
    """
    __tablename__ = "organizations"
    
    id = Column(VARCHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic info
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)  # URL-friendly name
    description = Column(Text)
    
    # Contact info
    email = Column(String(255))
    phone = Column(String(50))
    website = Column(String(255))
    
    # Subscription/Plan
    plan = Column(String(50), default="free")  # free, pro, enterprise
    plan_expires_at = Column(DateTime)
    
    # Quotas
    storage_quota_bytes = Column(Integer, default=1073741824)  # 1GB default
    storage_used_bytes = Column(Integer, default=0)
    max_users = Column(Integer, default=5)
    max_files = Column(Integer, default=1000)
    
    # Features flags
    features = Column(JSON(none_as_null=True))  # {"ml_pipeline": true, "virus_scan": true}
    
    # Settings
    settings = Column(JSON(none_as_null=True))  # Custom org settings
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    files = relationship("File", back_populates="organization")
    folders = relationship("Folder", back_populates="organization", foreign_keys="Folder.organization_id")
    
    def has_feature(self, feature_name: str) -> bool:
        """Check if organization has a specific feature enabled."""
        if not self.features:
            return False
        return self.features.get(feature_name, False)
    
    def has_storage_quota(self, additional_bytes: int = 0) -> bool:
        """Check if organization has enough storage quota."""
        return (self.storage_used_bytes + additional_bytes) <= self.storage_quota_bytes
    
    def storage_usage_percent(self) -> float:
        """Get storage usage as percentage."""
        if self.storage_quota_bytes == 0:
            return 100.0
        return (self.storage_used_bytes / self.storage_quota_bytes) * 100


class AuditLog(db.Base):
    """
    Audit log for tracking all important actions.
    
    Used for compliance, security monitoring, and debugging.
    """
    __tablename__ = "audit_logs"
    
    id = Column(VARCHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Who
    user_id = Column(VARCHAR(36), index=True)
    user_email = Column(String(255))
    organization_id = Column(VARCHAR(36), index=True)
    
    # What
    action = Column(String(100), nullable=False, index=True)  # e.g., "file.upload", "user.login"
    resource_type = Column(String(50))  # e.g., "file", "user", "organization"
    resource_id = Column(VARCHAR(36))
    
    # Details
    details = Column(JSON(none_as_null=True))  # Additional context
    changes = Column(JSON(none_as_null=True))  # Before/after for updates
    
    # Request context
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(500))
    request_id = Column(String(36))
    
    # Result
    status = Column(String(20), default="success")  # success, failure, error
    error_message = Column(Text)
    
    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class APIKey(db.Base):
    """
    API Key for service-to-service authentication.
    
    Allows external services to authenticate without user credentials.
    """
    __tablename__ = "api_keys"
    
    id = Column(VARCHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Key info
    name = Column(String(255), nullable=False)  # Descriptive name
    key_hash = Column(String(255), nullable=False, unique=True)  # Hashed key (never store plain)
    key_prefix = Column(String(10), nullable=False)  # First few chars for identification
    
    # Owner
    user_id = Column(VARCHAR(36), nullable=False, index=True)
    organization_id = Column(VARCHAR(36), nullable=False, index=True)
    
    # Permissions
    role = Column(String(50), default="api_service")
    scopes = Column(JSON(none_as_null=True))  # List of allowed permissions
    
    # Restrictions
    allowed_ips = Column(JSON(none_as_null=True))  # IP whitelist
    rate_limit = Column(Integer, default=1000)  # Requests per hour
    
    # Usage tracking
    last_used_at = Column(DateTime)
    usage_count = Column(Integer, default=0)
    
    # Expiration
    expires_at = Column(DateTime)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class RefreshToken(db.Base):
    """
    Refresh token storage for JWT authentication.
    
    Allows token revocation and tracking of active sessions.
    """
    __tablename__ = "refresh_tokens"
    
    id = Column(VARCHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Token info
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    
    # Owner
    user_id = Column(VARCHAR(36), nullable=False, index=True)
    
    # Session info
    device_info = Column(String(255))
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    # Expiration
    expires_at = Column(DateTime, nullable=False)
    
    # Status
    is_revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime)
    revoked_reason = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = Column(DateTime)
