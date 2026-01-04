"""
Organization Service - Business logic for organization management.

Handles organization CRUD, quota management, and tenant provisioning.
"""

import logging
import re
import secrets
import hashlib
from typing import Optional, List, Tuple
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator

from services.base_service import BaseService
from repositories.organization_repository import (
    OrganizationRepository,
    AuditLogRepository,
    APIKeyRepository
)
from entities.organization import Organization, AuditLog, APIKey
from entities.user import User
from core.tenant import TenantContext
from infrastructure.minio import minioStorage

# Redis Caching
try:
    from infrastructure.redis_cache import redis_cache
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis_cache = None

logger = logging.getLogger(__name__)

# Cache TTL configuration
CACHE_TTL_ORG = 300        # 5 minutes for org data
CACHE_TTL_ORG_LIST = 180   # 3 minutes for org lists
CACHE_TTL_STATS = 120      # 2 minutes for stats


# ============================================================================
# DTOs
# ============================================================================

class CreateOrganizationDTO(BaseModel):
    """DTO for creating a new organization."""
    name: str
    slug: Optional[str] = None
    email: Optional[EmailStr] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    plan: str = "free"
    
    @validator("slug", pre=True, always=True)
    def generate_slug(cls, v, values):
        if v:
            return cls.sanitize_slug(v)
        if "name" in values:
            return cls.sanitize_slug(values["name"])
        return None
    
    @staticmethod
    def sanitize_slug(text: str) -> str:
        """Convert text to URL-safe slug."""
        slug = text.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_-]+', '-', slug)
        slug = slug.strip('-')
        return slug[:100]  # Max 100 chars


class UpdateOrganizationDTO(BaseModel):
    """DTO for updating an organization."""
    name: Optional[str] = None
    description: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    settings: Optional[dict] = None


class CreateAPIKeyDTO(BaseModel):
    """DTO for creating an API key."""
    name: str
    scopes: Optional[List[str]] = None
    allowed_ips: Optional[List[str]] = None
    rate_limit: int = 1000
    expires_in_days: Optional[int] = None  # None = never expires


class OrganizationStatsDTO(BaseModel):
    """DTO for organization statistics."""
    id: str
    name: str
    slug: str
    plan: str
    user_count: int
    file_count: int
    storage_used_bytes: int
    storage_quota_bytes: int
    storage_usage_percent: float
    api_key_count: int
    created_at: datetime


# ============================================================================
# PLAN CONFIGURATIONS
# ============================================================================

PLAN_CONFIGS = {
    "free": {
        "storage_quota_bytes": 1 * 1024 * 1024 * 1024,  # 1 GB
        "max_users": 5,
        "max_files": 1000,
        "features": {
            "virus_scan": True,
            "ml_pipeline": False,
            "api_keys": False,
            "audit_logs": False,
            "custom_domains": False,
        }
    },
    "pro": {
        "storage_quota_bytes": 100 * 1024 * 1024 * 1024,  # 100 GB
        "max_users": 50,
        "max_files": 50000,
        "features": {
            "virus_scan": True,
            "ml_pipeline": True,
            "api_keys": True,
            "audit_logs": True,
            "custom_domains": False,
        }
    },
    "enterprise": {
        "storage_quota_bytes": 1024 * 1024 * 1024 * 1024,  # 1 TB
        "max_users": 500,
        "max_files": 500000,
        "features": {
            "virus_scan": True,
            "ml_pipeline": True,
            "api_keys": True,
            "audit_logs": True,
            "custom_domains": True,
            "sso": True,
            "dedicated_support": True,
        }
    }
}


# ============================================================================
# SERVICE
# ============================================================================

class OrganizationService(BaseService):
    """Service for organization management."""
    
    def __init__(self, db: Session):
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.audit_repo = AuditLogRepository(db)
        self.api_key_repo = APIKeyRepository(db)
    
    def _invalidate_org_caches(self, org_id: str = None, slug: str = None):
        """Invalidate organization-related caches."""
        if not REDIS_AVAILABLE or not redis_cache:
            return
        try:
            # Always clear the list cache
            redis_cache.delete_pattern("orgs:list:*")
            redis_cache.delete("orgs:count")
            
            if org_id:
                redis_cache.delete(f"org:id:{org_id}")
            if slug:
                redis_cache.delete(f"org:slug:{slug}")
            
            logger.debug(f"Invalidated org caches for {org_id or slug}")
        except Exception as e:
            logger.warning(f"Failed to invalidate org caches: {e}")

    def _serialize_org(self, org: Organization) -> dict:
        """Serialize organization for caching."""
        if org is None:
            return None
        return {
            'id': str(org.id),
            'name': org.name,
            'slug': org.slug,
            'email': org.email,
            'description': org.description,
            'phone': org.phone,
            'website': org.website,
            'plan': org.plan,
            'storage_quota_bytes': org.storage_quota_bytes,
            'storage_used_bytes': org.storage_used_bytes,
            'max_users': org.max_users,
            'max_files': org.max_files,
            'features': org.features,
            'settings': org.settings,
            'is_active': org.is_active,
            'is_verified': org.is_verified,
            'created_at': org.created_at.isoformat() if org.created_at else None,
            'updated_at': org.updated_at.isoformat() if org.updated_at else None,
        }
    
    # -------------------------------------------------------------------------
    # Organization CRUD
    # -------------------------------------------------------------------------
    
    def create_organization(
        self, 
        dto: CreateOrganizationDTO,
        created_by_user_id: str = None
    ) -> Tuple[Organization, Optional[str]]:
        """
        Create a new organization with storage bucket.
        
        Returns:
            Tuple of (organization, error_message)
        """
        # Check if slug is unique
        if self.org_repo.slug_exists(dto.slug):
            # Try adding a number suffix
            base_slug = dto.slug
            for i in range(1, 100):
                new_slug = f"{base_slug}-{i}"
                if not self.org_repo.slug_exists(new_slug):
                    dto.slug = new_slug
                    break
            else:
                return None, "Could not generate unique slug for organization"
        
        # Get plan configuration
        plan_config = PLAN_CONFIGS.get(dto.plan, PLAN_CONFIGS["free"])
        
        # Create organization
        org = Organization(
            name=dto.name,
            slug=dto.slug,
            email=dto.email,
            description=dto.description,
            phone=dto.phone,
            website=dto.website,
            plan=dto.plan,
            storage_quota_bytes=plan_config["storage_quota_bytes"],
            storage_used_bytes=0,
            max_users=plan_config["max_users"],
            max_files=plan_config["max_files"],
            features=plan_config["features"],
            settings={},
            is_active=True,
            is_verified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        org = self.org_repo.create(org)
        
        # Invalidate org list caches
        self._invalidate_org_caches()
        
        # Create MinIO bucket for tenant
        try:
            bucket_name = f"tenant-{org.slug}"
            self._create_tenant_bucket(bucket_name)
            logger.info(f"Created bucket {bucket_name} for organization {org.slug}")
        except Exception as e:
            logger.error(f"Failed to create bucket for {org.slug}: {e}")
            # Don't fail org creation, bucket can be created later
        
        # Log audit event
        self._log_audit(
            action="organization.create",
            resource_type="organization",
            resource_id=org.id,
            organization_id=org.id,
            user_id=created_by_user_id,
            details={"name": org.name, "slug": org.slug, "plan": org.plan}
        )
        
        return org, None
    
    def get_organization(self, org_id: str) -> Optional[Organization]:
        """Get organization by ID with caching."""
        cache_key = f"org:id:{org_id}"
        
        # Try cache first
        if REDIS_AVAILABLE and redis_cache:
            try:
                cached = redis_cache.get(cache_key)
                if cached:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return cached
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # Cache miss
        logger.debug(f"Cache MISS: {cache_key}")
        org = self.org_repo.get_by_id(org_id)
        
        # Store in cache
        if REDIS_AVAILABLE and redis_cache and org:
            try:
                redis_cache.set(cache_key, self._serialize_org(org), ttl=CACHE_TTL_ORG)
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        return org
    
    def get_organization_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug with caching."""
        cache_key = f"org:slug:{slug}"
        
        # Try cache first
        if REDIS_AVAILABLE and redis_cache:
            try:
                cached = redis_cache.get(cache_key)
                if cached:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return cached
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # Cache miss
        logger.debug(f"Cache MISS: {cache_key}")
        org = self.org_repo.get_by_slug_active(slug)
        
        # Store in cache
        if REDIS_AVAILABLE and redis_cache and org:
            try:
                redis_cache.set(cache_key, self._serialize_org(org), ttl=CACHE_TTL_ORG)
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        return org
    
    def update_organization(
        self,
        org_id: str,
        dto: UpdateOrganizationDTO,
        updated_by_user_id: str = None
    ) -> Tuple[Optional[Organization], Optional[str]]:
        """Update organization details."""
        org = self.org_repo.get_by_id(org_id)
        if not org:
            return None, "Organization not found"
        
        # Track changes for audit
        changes = {}
        
        if dto.name is not None and dto.name != org.name:
            changes["name"] = {"from": org.name, "to": dto.name}
            org.name = dto.name
        
        if dto.description is not None:
            org.description = dto.description
        
        if dto.email is not None:
            org.email = dto.email
        
        if dto.phone is not None:
            org.phone = dto.phone
        
        if dto.website is not None:
            org.website = dto.website
        
        if dto.settings is not None:
            org.settings = {**(org.settings or {}), **dto.settings}
        
        org.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(org)
        
        # Invalidate caches after update
        self._invalidate_org_caches(org_id=str(org.id), slug=org.slug)
        
        # Log audit event
        self._log_audit(
            action="organization.update",
            resource_type="organization",
            resource_id=org.id,
            organization_id=org.id,
            user_id=updated_by_user_id,
            details={"changes": changes}
        )
        
        return org, None
    
    def delete_organization(
        self,
        org_id: str,
        deleted_by_user_id: str = None,
        hard_delete: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Delete organization (soft delete by default).
        
        Hard delete will remove all data including files!
        """
        org = self.org_repo.get_by_id(org_id)
        if not org:
            return False, "Organization not found"
        
        # Invalidate caches before deletion
        self._invalidate_org_caches(org_id=str(org.id), slug=org.slug)
        
        if hard_delete:
            # Delete MinIO bucket and all files
            try:
                bucket_name = f"tenant-{org.slug}"
                self._delete_tenant_bucket(bucket_name)
            except Exception as e:
                logger.error(f"Failed to delete bucket for {org.slug}: {e}")
            
            # Delete organization from database
            self.org_repo.delete(org_id)
            
            # Log audit (to platform log since org is deleted)
            logger.warning(
                f"HARD DELETE: Organization {org.slug} ({org.id}) "
                f"deleted by user {deleted_by_user_id}"
            )
        else:
            # Soft delete
            self.org_repo.deactivate(org_id)
            
            # Log audit
            self._log_audit(
                action="organization.deactivate",
                resource_type="organization",
                resource_id=org.id,
                organization_id=org.id,
                user_id=deleted_by_user_id,
                details={"name": org.name, "slug": org.slug}
            )
        
        return True, None
    
    def list_organizations(
        self,
        skip: int = 0,
        limit: int = 100,
        plan: str = None,
        search: str = None
    ) -> Tuple[List[Organization], int]:
        """List organizations with pagination and filtering (with caching for non-search queries)."""
        
        # Only cache non-search queries
        if not search:
            cache_key = f"orgs:list:skip={skip}:limit={limit}:plan={plan or 'all'}"
            
            # Try cache first
            if REDIS_AVAILABLE and redis_cache:
                try:
                    cached = redis_cache.get(cache_key)
                    if cached:
                        logger.debug(f"Cache HIT: {cache_key}")
                        return cached.get('orgs', []), cached.get('total', 0)
                except Exception as e:
                    logger.warning(f"Redis cache read failed: {e}")
        
            # Cache miss
            logger.debug(f"Cache MISS: {cache_key}")
            orgs = self.org_repo.list_active(skip, limit, plan)
            total = self.org_repo.count_active(plan)
            
            # Store in cache
            if REDIS_AVAILABLE and redis_cache:
                try:
                    cache_data = {
                        'orgs': [self._serialize_org(o) for o in orgs],
                        'total': total
                    }
                    redis_cache.set(cache_key, cache_data, ttl=CACHE_TTL_ORG_LIST)
                except Exception as e:
                    logger.warning(f"Redis cache write failed: {e}")
            
            return orgs, total
        else:
            # Search queries are not cached (too dynamic)
            orgs = self.org_repo.search(search, skip, limit)
            total = len(orgs)  # Approximate for search
            return orgs, total
    
    # -------------------------------------------------------------------------
    # Plan & Quota Management
    # -------------------------------------------------------------------------
    
    def upgrade_plan(
        self,
        org_id: str,
        new_plan: str,
        expires_at: datetime = None,
        updated_by_user_id: str = None
    ) -> Tuple[Optional[Organization], Optional[str]]:
        """Upgrade organization to a new plan."""
        if new_plan not in PLAN_CONFIGS:
            return None, f"Invalid plan: {new_plan}"
        
        org = self.org_repo.get_by_id(org_id)
        if not org:
            return None, "Organization not found"
        
        old_plan = org.plan
        plan_config = PLAN_CONFIGS[new_plan]
        
        org = self.org_repo.update_plan(
            org_id=org_id,
            plan=new_plan,
            storage_quota=plan_config["storage_quota_bytes"],
            max_users=plan_config["max_users"],
            max_files=plan_config["max_files"],
            features=plan_config["features"],
            expires_at=expires_at
        )
        
        # Log audit
        self._log_audit(
            action="organization.plan_change",
            resource_type="organization",
            resource_id=org.id,
            organization_id=org.id,
            user_id=updated_by_user_id,
            details={"from_plan": old_plan, "to_plan": new_plan}
        )
        
        return org, None
    
    def check_quota(
        self,
        org_id: str,
        quota_type: str,
        required_amount: int = 1
    ) -> Tuple[bool, str]:
        """
        Check if organization has available quota.
        
        Returns:
            Tuple of (has_quota, message)
        """
        org = self.org_repo.get_by_id(org_id)
        if not org:
            return False, "Organization not found"
        
        if quota_type == "storage":
            available = org.storage_quota_bytes - org.storage_used_bytes
            if available < required_amount:
                return False, f"Storage quota exceeded. Available: {available} bytes"
            return True, "OK"
        
        elif quota_type == "users":
            current_users = self.db.query(User).filter(
                User.organization_id == org_id,
                User.is_active == True
            ).count()
            if current_users >= org.max_users:
                return False, f"User limit reached ({org.max_users})"
            return True, "OK"
        
        elif quota_type == "files":
            # Would need file count query
            return True, "OK"
        
        return False, f"Unknown quota type: {quota_type}"
    
    def update_storage_usage(
        self,
        org_id: str,
        bytes_delta: int
    ) -> Optional[Organization]:
        """Update storage usage (positive to add, negative to subtract)."""
        return self.org_repo.update_storage_usage(org_id, bytes_delta)
    
    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------
    
    def get_organization_stats(self, org_id: str) -> Optional[OrganizationStatsDTO]:
        """Get organization statistics."""
        org = self.org_repo.get_by_id(org_id)
        if not org:
            return None
        
        # Count users
        user_count = self.db.query(User).filter(
            User.organization_id == org_id,
            User.is_active == True
        ).count()
        
        # Count files (would need File entity with org_id)
        file_count = 0  # TODO: Implement when File has organization_id
        
        # Count API keys
        api_key_count = len(self.api_key_repo.list_by_organization(org_id))
        
        # Calculate storage usage
        usage_percent = 0
        if org.storage_quota_bytes > 0:
            usage_percent = (org.storage_used_bytes / org.storage_quota_bytes) * 100
        
        return OrganizationStatsDTO(
            id=org.id,
            name=org.name,
            slug=org.slug,
            plan=org.plan,
            user_count=user_count,
            file_count=file_count,
            storage_used_bytes=org.storage_used_bytes,
            storage_quota_bytes=org.storage_quota_bytes,
            storage_usage_percent=round(usage_percent, 2),
            api_key_count=api_key_count,
            created_at=org.created_at
        )
    
    # -------------------------------------------------------------------------
    # API Key Management
    # -------------------------------------------------------------------------
    
    def create_api_key(
        self,
        org_id: str,
        user_id: str,
        dto: CreateAPIKeyDTO
    ) -> Tuple[Optional[str], Optional[APIKey], Optional[str]]:
        """
        Create a new API key.
        
        Returns:
            Tuple of (plain_key, api_key_object, error_message)
            The plain_key is only returned once and should be shown to user.
        """
        org = self.org_repo.get_by_id(org_id)
        if not org:
            return None, None, "Organization not found"
        
        # Check if API keys feature is enabled
        if not org.features or not org.features.get("api_keys"):
            return None, None, "API keys feature not available on your plan"
        
        # Generate key
        plain_key = f"fm_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        key_prefix = plain_key[:10]
        
        # Calculate expiration
        expires_at = None
        if dto.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=dto.expires_in_days)
        
        api_key = APIKey(
            name=dto.name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            user_id=user_id,
            organization_id=org_id,
            role="api_service",
            scopes=dto.scopes,
            allowed_ips=dto.allowed_ips,
            rate_limit=dto.rate_limit,
            expires_at=expires_at,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        api_key = self.api_key_repo.create(api_key)
        
        # Log audit
        self._log_audit(
            action="api_key.create",
            resource_type="api_key",
            resource_id=api_key.id,
            organization_id=org_id,
            user_id=user_id,
            details={"name": dto.name, "prefix": key_prefix}
        )
        
        return plain_key, api_key, None
    
    def revoke_api_key(
        self,
        org_id: str,
        key_id: str,
        revoked_by_user_id: str = None
    ) -> Tuple[bool, Optional[str]]:
        """Revoke an API key."""
        api_key = self.api_key_repo.get_by_id(key_id)
        if not api_key:
            return False, "API key not found"
        
        if api_key.organization_id != org_id:
            return False, "API key does not belong to this organization"
        
        self.api_key_repo.revoke(key_id)
        
        # Log audit
        self._log_audit(
            action="api_key.revoke",
            resource_type="api_key",
            resource_id=key_id,
            organization_id=org_id,
            user_id=revoked_by_user_id,
            details={"name": api_key.name, "prefix": api_key.key_prefix}
        )
        
        return True, None
    
    def validate_api_key(self, plain_key: str) -> Optional[APIKey]:
        """Validate an API key and return the key object if valid."""
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        api_key = self.api_key_repo.get_by_key_hash(key_hash)
        
        if not api_key:
            return None
        
        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None
        
        # Update usage
        self.api_key_repo.update_usage(api_key.id)
        
        return api_key
    
    # -------------------------------------------------------------------------
    # Audit Logs
    # -------------------------------------------------------------------------
    
    def get_audit_logs(
        self,
        org_id: str,
        skip: int = 0,
        limit: int = 100,
        action: str = None,
        user_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Tuple[List[AuditLog], int]:
        """Get audit logs for an organization."""
        logs = self.audit_repo.list_by_organization(
            org_id=org_id,
            skip=skip,
            limit=limit,
            action=action,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        total = self.audit_repo.count_by_organization(
            org_id=org_id,
            action=action,
            start_date=start_date,
            end_date=end_date
        )
        
        return logs, total
    
    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------
    
    def _create_tenant_bucket(self, bucket_name: str) -> None:
        """Create MinIO bucket for tenant."""
        try:
            if not minioStorage.client.bucket_exists(bucket_name):
                minioStorage.client.make_bucket(bucket_name)
                logger.info(f"Created MinIO bucket: {bucket_name}")
        except Exception as e:
            logger.error(f"Failed to create bucket {bucket_name}: {e}")
            raise
    
    def _delete_tenant_bucket(self, bucket_name: str) -> None:
        """Delete MinIO bucket and all objects."""
        try:
            if minioStorage.client.bucket_exists(bucket_name):
                # Delete all objects first
                objects = minioStorage.client.list_objects(bucket_name, recursive=True)
                for obj in objects:
                    minioStorage.client.remove_object(bucket_name, obj.object_name)
                
                # Delete bucket
                minioStorage.client.remove_bucket(bucket_name)
                logger.info(f"Deleted MinIO bucket: {bucket_name}")
        except Exception as e:
            logger.error(f"Failed to delete bucket {bucket_name}: {e}")
            raise
    
    def _log_audit(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        organization_id: str,
        user_id: str = None,
        details: dict = None,
        status: str = "success",
        error_message: str = None
    ) -> None:
        """Log an audit event."""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                organization_id=organization_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                status=status,
                error_message=error_message,
                created_at=datetime.utcnow()
            )
            self.audit_repo.create(audit_log)
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
