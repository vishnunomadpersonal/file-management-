"""
Organization Repository - Database operations for organizations.

Handles all database interactions for organization (tenant) management.
"""

import logging
from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from repositories.base_repository import BaseRepo
from entities.organization import Organization, AuditLog, APIKey
from entities.user import User

logger = logging.getLogger(__name__)


class OrganizationRepository(BaseRepo[Organization]):
    """Repository for Organization entity operations."""
    
    def __init__(self, db: Session):
        super().__init__(Organization, db)
    
    def get_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by URL slug."""
        return self.db.query(Organization).filter(
            Organization.slug == slug
        ).first()
    
    def get_by_slug_active(self, slug: str) -> Optional[Organization]:
        """Get active organization by URL slug."""
        return self.db.query(Organization).filter(
            Organization.slug == slug,
            Organization.is_active == True
        ).first()
    
    def get_by_name(self, name: str) -> Optional[Organization]:
        """Get organization by name."""
        return self.db.query(Organization).filter(
            Organization.name == name
        ).first()
    
    def slug_exists(self, slug: str, exclude_id: str = None) -> bool:
        """Check if slug is already taken."""
        query = self.db.query(Organization).filter(Organization.slug == slug)
        if exclude_id:
            query = query.filter(Organization.id != exclude_id)
        return query.count() > 0
    
    def list_active(
        self, 
        skip: int = 0, 
        limit: int = 100,
        plan: str = None
    ) -> List[Organization]:
        """List active organizations with optional filtering."""
        query = self.db.query(Organization).filter(
            Organization.is_active == True
        )
        
        if plan:
            query = query.filter(Organization.plan == plan)
        
        return query.order_by(Organization.name).offset(skip).limit(limit).all()
    
    def count_active(self, plan: str = None) -> int:
        """Count active organizations."""
        query = self.db.query(Organization).filter(
            Organization.is_active == True
        )
        if plan:
            query = query.filter(Organization.plan == plan)
        return query.count()
    
    def search(
        self, 
        query_str: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Organization]:
        """Search organizations by name or email."""
        return self.db.query(Organization).filter(
            Organization.is_active == True,
            or_(
                Organization.name.ilike(f"%{query_str}%"),
                Organization.email.ilike(f"%{query_str}%"),
                Organization.slug.ilike(f"%{query_str}%")
            )
        ).offset(skip).limit(limit).all()
    
    def get_user_organizations(self, user_id: str) -> List[Organization]:
        """Get all organizations a user belongs to."""
        return self.db.query(Organization).join(
            User, User.organization_id == Organization.id
        ).filter(
            User.id == user_id,
            Organization.is_active == True
        ).all()
    
    def update_storage_usage(
        self, 
        org_id: str, 
        bytes_delta: int
    ) -> Optional[Organization]:
        """Update storage usage (positive to add, negative to subtract)."""
        org = self.get_by_id(org_id)
        if not org:
            return None
        
        new_usage = max(0, org.storage_used_bytes + bytes_delta)
        org.storage_used_bytes = new_usage
        org.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(org)
        return org
    
    def get_storage_stats(self, org_id: str) -> dict:
        """Get storage statistics for an organization."""
        org = self.get_by_id(org_id)
        if not org:
            return {}
        
        return {
            "quota_bytes": org.storage_quota_bytes,
            "used_bytes": org.storage_used_bytes,
            "available_bytes": max(0, org.storage_quota_bytes - org.storage_used_bytes),
            "usage_percent": (org.storage_used_bytes / org.storage_quota_bytes * 100) if org.storage_quota_bytes > 0 else 0
        }
    
    def update_plan(
        self, 
        org_id: str, 
        plan: str,
        storage_quota: int = None,
        max_users: int = None,
        max_files: int = None,
        features: dict = None,
        expires_at: datetime = None
    ) -> Optional[Organization]:
        """Update organization plan and quotas."""
        org = self.get_by_id(org_id)
        if not org:
            return None
        
        org.plan = plan
        org.updated_at = datetime.utcnow()
        
        if storage_quota is not None:
            org.storage_quota_bytes = storage_quota
        if max_users is not None:
            org.max_users = max_users
        if max_files is not None:
            org.max_files = max_files
        if features is not None:
            org.features = features
        if expires_at is not None:
            org.plan_expires_at = expires_at
        
        self.db.commit()
        self.db.refresh(org)
        return org
    
    def deactivate(self, org_id: str) -> Optional[Organization]:
        """Deactivate an organization (soft delete)."""
        org = self.get_by_id(org_id)
        if not org:
            return None
        
        org.is_active = False
        org.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(org)
        return org
    
    def reactivate(self, org_id: str) -> Optional[Organization]:
        """Reactivate a deactivated organization."""
        org = self.get_by_id(org_id)
        if not org:
            return None
        
        org.is_active = True
        org.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(org)
        return org


class AuditLogRepository(BaseRepo[AuditLog]):
    """Repository for AuditLog entity operations."""
    
    def __init__(self, db: Session):
        super().__init__(AuditLog, db)
    
    def list_by_organization(
        self,
        org_id: str,
        skip: int = 0,
        limit: int = 100,
        action: str = None,
        user_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[AuditLog]:
        """List audit logs for an organization with filtering."""
        query = self.db.query(AuditLog).filter(
            AuditLog.organization_id == org_id
        )
        
        if action:
            query = query.filter(AuditLog.action == action)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    
    def count_by_organization(
        self,
        org_id: str,
        action: str = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> int:
        """Count audit logs for an organization."""
        query = self.db.query(AuditLog).filter(
            AuditLog.organization_id == org_id
        )
        
        if action:
            query = query.filter(AuditLog.action == action)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        return query.count()
    
    def get_action_summary(
        self,
        org_id: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[dict]:
        """Get summary of actions for an organization."""
        from sqlalchemy import func
        
        query = self.db.query(
            AuditLog.action,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.organization_id == org_id
        )
        
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        results = query.group_by(AuditLog.action).all()
        return [{"action": r[0], "count": r[1]} for r in results]


class APIKeyRepository(BaseRepo[APIKey]):
    """Repository for APIKey entity operations."""
    
    def __init__(self, db: Session):
        super().__init__(APIKey, db)
    
    def get_by_key_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by its hash."""
        return self.db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()
    
    def get_by_prefix(self, prefix: str) -> Optional[APIKey]:
        """Get API key by its prefix (for identification)."""
        return self.db.query(APIKey).filter(
            APIKey.key_prefix == prefix,
            APIKey.is_active == True
        ).first()
    
    def list_by_organization(
        self,
        org_id: str,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False
    ) -> List[APIKey]:
        """List API keys for an organization."""
        query = self.db.query(APIKey).filter(
            APIKey.organization_id == org_id
        )
        
        if not include_inactive:
            query = query.filter(APIKey.is_active == True)
        
        return query.offset(skip).limit(limit).all()
    
    def list_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[APIKey]:
        """List API keys created by a user."""
        return self.db.query(APIKey).filter(
            APIKey.user_id == user_id,
            APIKey.is_active == True
        ).offset(skip).limit(limit).all()
    
    def revoke(self, key_id: str) -> Optional[APIKey]:
        """Revoke an API key."""
        key = self.get_by_id(key_id)
        if not key:
            return None
        
        key.is_active = False
        key.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(key)
        return key
    
    def update_usage(self, key_id: str) -> Optional[APIKey]:
        """Update last used timestamp and increment usage count."""
        key = self.get_by_id(key_id)
        if not key:
            return None
        
        key.last_used_at = datetime.utcnow()
        key.usage_count = (key.usage_count or 0) + 1
        self.db.commit()
        return key
