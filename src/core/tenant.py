"""
Multi-Tenant Middleware and Context.

Provides tenant isolation and context management for the multi-tenant
file management platform. Supports path-based tenant identification.

Architecture:
    /api/v1/org/{org_slug}/... -> Tenant-scoped routes
    /api/v1/auth/...           -> Auth routes (no tenant context)
    /api/v1/platform/...       -> Super admin routes (all tenants)
"""

import logging
from typing import Optional, Callable, Any
from dataclasses import dataclass
from contextvars import ContextVar
from functools import wraps

from fastapi import Request, HTTPException, status, Depends
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.orm import Session

from infrastructure.db.mysql import mysql
from entities.organization import Organization
from core.security import get_current_user, AuthenticatedUser, Role

logger = logging.getLogger(__name__)

# ============================================================================
# CONTEXT VARIABLES
# ============================================================================

# Current tenant context (thread-safe)
_current_tenant: ContextVar[Optional["TenantContext"]] = ContextVar(
    "current_tenant", default=None
)

# Request context
_current_request_id: ContextVar[Optional[str]] = ContextVar(
    "current_request_id", default=None
)


@dataclass
class TenantContext:
    """
    Tenant context containing organization information.
    
    This is set per-request and available throughout the request lifecycle.
    """
    organization_id: str
    organization_slug: str
    organization_name: str
    plan: str
    features: dict
    settings: dict
    storage_quota_bytes: int
    storage_used_bytes: int
    max_users: int
    max_files: int
    is_active: bool
    
    @property
    def storage_available_bytes(self) -> int:
        """Remaining storage quota."""
        return max(0, self.storage_quota_bytes - self.storage_used_bytes)
    
    @property
    def storage_usage_percent(self) -> float:
        """Storage usage as percentage."""
        if self.storage_quota_bytes == 0:
            return 100.0
        return (self.storage_used_bytes / self.storage_quota_bytes) * 100
    
    def has_feature(self, feature_name: str) -> bool:
        """Check if tenant has a specific feature enabled."""
        if not self.features:
            return False
        return self.features.get(feature_name, False)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a tenant-specific setting."""
        if not self.settings:
            return default
        return self.settings.get(key, default)
    
    @property
    def bucket_name(self) -> str:
        """MinIO bucket name for this tenant."""
        return f"tenant-{self.organization_slug}"


def get_current_tenant() -> Optional[TenantContext]:
    """Get the current tenant context."""
    return _current_tenant.get()


def get_current_request_id() -> Optional[str]:
    """Get the current request ID."""
    return _current_request_id.get()


def set_current_tenant(tenant: Optional[TenantContext]) -> None:
    """Set the current tenant context."""
    _current_tenant.set(tenant)


def set_current_request_id(request_id: Optional[str]) -> None:
    """Set the current request ID."""
    _current_request_id.set(request_id)


# ============================================================================
# TENANT MIDDLEWARE
# ============================================================================

class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and validate tenant context from request path.
    
    Routes:
    - /api/v1/org/{slug}/... -> Extract tenant from path
    - /api/v1/auth/... -> No tenant context
    - /api/v1/platform/... -> Super admin, no single tenant
    - Other -> Legacy routes, tenant from user's organization
    """
    
    # Paths that don't require tenant context
    NO_TENANT_PATHS = [
        "/api/v1/auth",
        "/api/v1/health",
        "/api/v1/pipeline/health",
        "/api/v1/platform",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract request ID from Kong headers
        request_id = (
            request.headers.get("X-Request-ID") or
            request.headers.get("X-Correlation-ID")
        )
        set_current_request_id(request_id)
        
        # Check if path needs tenant context
        path = request.url.path
        
        # Skip tenant extraction for certain paths
        if any(path.startswith(p) for p in self.NO_TENANT_PATHS):
            set_current_tenant(None)
            response = await call_next(request)
            return response
        
        # Extract tenant from path: /api/v1/org/{slug}/...
        tenant_context = None
        if path.startswith("/api/v1/org/"):
            parts = path.split("/")
            if len(parts) >= 5:  # /api/v1/org/{slug}/...
                org_slug = parts[4]
                tenant_context = await self._load_tenant(org_slug, request)
        
        # Store tenant context
        set_current_tenant(tenant_context)
        
        # Add tenant info to request state for easy access
        request.state.tenant = tenant_context
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add tenant headers to response (for debugging)
        if tenant_context:
            response.headers["X-Tenant-ID"] = tenant_context.organization_id
            response.headers["X-Tenant-Slug"] = tenant_context.organization_slug
        
        if request_id:
            response.headers["X-Request-ID"] = request_id
        
        return response
    
    async def _load_tenant(
        self, 
        org_slug: str, 
        request: Request
    ) -> Optional[TenantContext]:
        """Load tenant from database by slug."""
        try:
            db: Session = next(mysql.get_db())
            try:
                org = db.query(Organization).filter(
                    Organization.slug == org_slug,
                    Organization.is_active == True
                ).first()
                
                if not org:
                    logger.warning(f"Tenant not found: {org_slug}")
                    return None
                
                return TenantContext(
                    organization_id=org.id,
                    organization_slug=org.slug,
                    organization_name=org.name,
                    plan=org.plan or "free",
                    features=org.features or {},
                    settings=org.settings or {},
                    storage_quota_bytes=org.storage_quota_bytes or 0,
                    storage_used_bytes=org.storage_used_bytes or 0,
                    max_users=org.max_users or 5,
                    max_files=org.max_files or 1000,
                    is_active=org.is_active,
                )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error loading tenant {org_slug}: {e}")
            return None


# ============================================================================
# DEPENDENCIES
# ============================================================================

async def get_tenant_context(request: Request) -> Optional[TenantContext]:
    """
    FastAPI dependency that returns the tenant context (or None).
    
    Unlike require_tenant, this doesn't raise an error if no tenant.
    Useful for routes that work with or without tenant context.
    
    Usage:
        @router.get("/organizations/current")
        async def get_org(tenant: TenantContext = Depends(get_tenant_context)):
            if tenant:
                return tenant
            raise HTTPException(...)
    """
    return getattr(request.state, "tenant", None) or get_current_tenant()


async def require_tenant(request: Request) -> TenantContext:
    """
    FastAPI dependency that requires a valid tenant context.
    
    Usage:
        @router.get("/files")
        async def list_files(tenant: TenantContext = Depends(require_tenant)):
            # tenant.organization_id, tenant.bucket_name, etc.
    """
    tenant = getattr(request.state, "tenant", None) or get_current_tenant()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required. Use /api/v1/org/{slug}/... routes."
        )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is inactive. Please contact support."
        )
    
    return tenant


async def require_tenant_member(
    tenant: TenantContext = Depends(require_tenant),
    user: AuthenticatedUser = Depends(get_current_user),
) -> tuple[TenantContext, AuthenticatedUser]:
    """
    Require authenticated user to be a member of the current tenant.
    
    Usage:
        @router.get("/files")
        async def list_files(
            ctx: tuple = Depends(require_tenant_member)
        ):
            tenant, user = ctx
    """
    # Super admins can access any tenant
    if user.role == Role.SUPER_ADMIN:
        return tenant, user
    
    # Check if user belongs to this organization
    if user.organization_id != tenant.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization."
        )
    
    return tenant, user


async def require_tenant_admin(
    tenant: TenantContext = Depends(require_tenant),
    user: AuthenticatedUser = Depends(get_current_user),
) -> tuple[TenantContext, AuthenticatedUser]:
    """
    Require authenticated user to be an admin of the current tenant.
    """
    tenant, user = await require_tenant_member(tenant, user)
    
    if user.role not in [Role.SUPER_ADMIN, Role.ORG_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin access required."
        )
    
    return tenant, user


async def require_tenant_manager(
    tenant: TenantContext = Depends(require_tenant),
    user: AuthenticatedUser = Depends(get_current_user),
) -> tuple[TenantContext, AuthenticatedUser]:
    """
    Require authenticated user to be at least a manager of the current tenant.
    """
    tenant, user = await require_tenant_member(tenant, user)
    
    if user.role not in [Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager access required."
        )
    
    return tenant, user


def require_feature(feature_name: str):
    """
    Dependency factory that requires a specific feature to be enabled.
    
    Usage:
        @router.post("/ml/train")
        async def train_model(
            tenant: TenantContext = Depends(require_feature("ml_pipeline"))
        ):
            pass
    """
    async def feature_checker(
        tenant: TenantContext = Depends(require_tenant)
    ) -> TenantContext:
        if not tenant.has_feature(feature_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature_name}' is not enabled for your organization. "
                       f"Please upgrade your plan."
            )
        return tenant
    
    return feature_checker


def require_quota(quota_type: str):
    """
    Dependency factory that checks quota availability.
    
    Usage:
        @router.post("/files/upload")
        async def upload_file(
            tenant: TenantContext = Depends(require_quota("storage"))
        ):
            pass
    """
    async def quota_checker(
        tenant: TenantContext = Depends(require_tenant)
    ) -> TenantContext:
        if quota_type == "storage":
            if tenant.storage_usage_percent >= 100:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Storage quota exceeded. Please upgrade your plan or delete unused files."
                )
        elif quota_type == "files":
            # Would need to check current file count
            pass
        elif quota_type == "users":
            # Would need to check current user count
            pass
        
        return tenant
    
    return quota_checker


# ============================================================================
# TENANT-SCOPED QUERY HELPERS
# ============================================================================

class TenantScopedQuery:
    """
    Helper class for building tenant-scoped database queries.
    
    Usage:
        query = TenantScopedQuery(db, tenant)
        files = query.filter(File).filter(File.status == 'active').all()
    """
    
    def __init__(self, db: Session, tenant: TenantContext):
        self.db = db
        self.tenant = tenant
    
    def filter(self, model):
        """Start a tenant-scoped query for a model."""
        if hasattr(model, 'organization_id'):
            return self.db.query(model).filter(
                model.organization_id == self.tenant.organization_id
            )
        return self.db.query(model)


def tenant_filter(query, model, tenant: TenantContext):
    """
    Add tenant filter to an existing query.
    
    Usage:
        query = db.query(File)
        query = tenant_filter(query, File, tenant)
    """
    if hasattr(model, 'organization_id'):
        return query.filter(model.organization_id == tenant.organization_id)
    return query


# ============================================================================
# AUDIT LOGGING
# ============================================================================

def log_audit_event(
    action: str,
    resource_type: str = None,
    resource_id: str = None,
    details: dict = None,
    status: str = "success",
    error_message: str = None,
):
    """
    Log an audit event for compliance.
    
    Usage:
        log_audit_event(
            action="file.upload",
            resource_type="file",
            resource_id=file.id,
            details={"filename": file.filename, "size": file.size}
        )
    """
    from entities.organization import AuditLog
    from datetime import datetime
    
    tenant = get_current_tenant()
    request_id = get_current_request_id()
    
    # This would typically be done async/background
    logger.info(
        f"AUDIT: action={action} "
        f"resource={resource_type}:{resource_id} "
        f"tenant={tenant.organization_slug if tenant else 'N/A'} "
        f"request_id={request_id} "
        f"status={status}"
    )
    
    # In production, would write to AuditLog table
    # audit_entry = AuditLog(
    #     organization_id=tenant.organization_id if tenant else None,
    #     action=action,
    #     resource_type=resource_type,
    #     resource_id=resource_id,
    #     details=details,
    #     request_id=request_id,
    #     status=status,
    #     error_message=error_message,
    #     created_at=datetime.utcnow()
    # )
    # db.add(audit_entry)
    # db.commit()


# ============================================================================
# TENANT-AWARE ROUTE CLASS
# ============================================================================

class TenantRoute(APIRoute):
    """
    Custom route class that automatically adds tenant context logging.
    
    Usage:
        router = APIRouter(route_class=TenantRoute)
    """
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def tenant_route_handler(request: Request) -> Response:
            tenant = get_current_tenant()
            request_id = get_current_request_id()
            
            logger.info(
                f"Request: {request.method} {request.url.path} "
                f"tenant={tenant.organization_slug if tenant else 'N/A'} "
                f"request_id={request_id}"
            )
            
            response = await original_route_handler(request)
            
            logger.info(
                f"Response: {request.method} {request.url.path} "
                f"status={response.status_code} "
                f"request_id={request_id}"
            )
            
            return response
        
        return tenant_route_handler
