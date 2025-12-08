"""
Organization API Routes - Multi-tenant organization management.

Provides endpoints for organization CRUD, stats, API keys, and audit logs.
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from infrastructure.db.mysql import mysql
from services.organization_service import (
    OrganizationService,
    CreateOrganizationDTO,
    UpdateOrganizationDTO,
    CreateAPIKeyDTO,
    OrganizationStatsDTO,
    PLAN_CONFIGS
)
from core.tenant import (
    get_tenant_context,
    TenantContext
)
from core.security import get_current_user, AuthenticatedUser, Role
from entities.organization import Organization

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


# ============================================================================
# Response Models
# ============================================================================

class OrganizationResponse(BaseModel):
    """Organization response model."""
    id: str
    name: str
    slug: str
    email: Optional[str]
    description: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    plan: str
    storage_quota_bytes: int
    storage_used_bytes: int
    max_users: int
    max_files: int
    features: Optional[dict] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OrganizationListResponse(BaseModel):
    """Paginated organization list response."""
    items: List[OrganizationResponse]
    total: int
    skip: int
    limit: int


class APIKeyResponse(BaseModel):
    """API key response (without the actual key)."""
    id: str
    name: str
    key_prefix: str
    role: str
    scopes: Optional[List[str]]
    rate_limit: int
    expires_at: Optional[datetime]
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    """Response when creating API key (includes plain key once)."""
    key: str  # Only shown once!
    api_key: APIKeyResponse


class AuditLogResponse(BaseModel):
    """Audit log response."""
    id: str
    user_id: Optional[str]
    action: str
    resource_type: str
    resource_id: str
    details: Optional[dict]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated audit log list response."""
    items: List[AuditLogResponse]
    total: int
    skip: int
    limit: int


class PlanInfoResponse(BaseModel):
    """Plan information response."""
    name: str
    storage_quota_bytes: int
    max_users: int
    max_files: int
    features: dict


class PlansListResponse(BaseModel):
    """List of available plans."""
    plans: dict


# ============================================================================
# Request Models
# ============================================================================

class CreateOrganizationRequest(BaseModel):
    """Create organization request."""
    name: str
    slug: Optional[str] = None
    email: Optional[EmailStr] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    plan: str = "free"


class UpdateOrganizationRequest(BaseModel):
    """Update organization request."""
    name: Optional[str] = None
    description: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    settings: Optional[dict] = None


class CreateAPIKeyRequest(BaseModel):
    """Create API key request."""
    name: str
    scopes: Optional[List[str]] = None
    allowed_ips: Optional[List[str]] = None
    rate_limit: int = 1000
    expires_in_days: Optional[int] = None


# ============================================================================
# Routes - Public
# ============================================================================

@router.get("/plans", response_model=PlansListResponse)
async def get_available_plans():
    """
    Get list of available subscription plans.
    
    Public endpoint - no authentication required.
    """
    return PlansListResponse(plans=PLAN_CONFIGS)


class PublicOrganizationInfo(BaseModel):
    """Minimal organization info for signup dropdown."""
    id: str
    name: str
    slug: str


class PublicOrganizationListResponse(BaseModel):
    """Public organization list for signup."""
    items: List[PublicOrganizationInfo]


@router.get("/public", response_model=PublicOrganizationListResponse)
async def list_organizations_public(
    db: Session = Depends(mysql.get_db)
):
    """
    Get list of organizations for signup dropdown.
    
    Public endpoint - no authentication required.
    Returns all active organizations with minimal info.
    """
    orgs = db.query(Organization).filter(
        Organization.is_active == True
    ).order_by(Organization.name).all()
    
    return PublicOrganizationListResponse(
        items=[PublicOrganizationInfo(id=o.id, name=o.name, slug=o.slug) for o in orgs]
    )


# ============================================================================
# Routes - Super Admin Only
# ============================================================================

@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_organization(
    request: CreateOrganizationRequest,
    db: Session = Depends(mysql.get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Create a new organization.
    
    Requires super_admin role or self-service signup enabled.
    """
    # Check permission (super_admin can create any org)
    if current_user.role != Role.SUPER_ADMIN:
        # Self-service: user can create their own org
        # For now, restrict to super_admin
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can create organizations"
        )
    
    service = OrganizationService(db)
    dto = CreateOrganizationDTO(**request.model_dump())
    
    org, error = service.create_organization(dto, current_user.id)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return OrganizationResponse.model_validate(org)


@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    plan: Optional[str] = Query(None, description="Filter by plan"),
    search: Optional[str] = Query(None, description="Search by name"),
    db: Session = Depends(mysql.get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    List all organizations.
    
    Requires super_admin role.
    """
    if current_user.role != Role.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can list all organizations"
        )
    
    service = OrganizationService(db)
    orgs, total = service.list_organizations(skip, limit, plan, search)
    
    return OrganizationListResponse(
        items=[OrganizationResponse.model_validate(o) for o in orgs],
        total=total,
        skip=skip,
        limit=limit
    )


@router.patch(
    "/{org_id}/plan",
    response_model=OrganizationResponse
)
async def update_organization_plan(
    org_id: str = Path(..., description="Organization ID"),
    plan: str = Query(..., description="New plan name"),
    expires_at: Optional[datetime] = Query(None, description="Plan expiration"),
    db: Session = Depends(mysql.get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Update organization plan.
    
    Requires super_admin role.
    """
    if current_user.role != Role.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can change plans"
        )
    
    service = OrganizationService(db)
    org, error = service.upgrade_plan(org_id, plan, expires_at, current_user.id)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return OrganizationResponse.model_validate(org)


@router.delete("/{org_id}")
async def delete_organization(
    org_id: str = Path(..., description="Organization ID"),
    hard_delete: bool = Query(False, description="Permanently delete all data"),
    db: Session = Depends(mysql.get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Delete an organization.
    
    Soft delete by default. Hard delete removes all data permanently!
    Requires super_admin role.
    """
    if current_user.role != Role.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can delete organizations"
        )
    
    service = OrganizationService(db)
    success, error = service.delete_organization(
        org_id, current_user.id, hard_delete
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Organization deleted successfully"}
    )


# ============================================================================
# Routes - Organization Context (tenant-aware)
# ============================================================================

@router.get("/current", response_model=OrganizationResponse)
async def get_current_organization(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(mysql.get_db)
):
    """
    Get the current organization (from tenant context).
    
    Requires valid tenant context.
    """
    if not tenant or not tenant.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization context"
        )
    
    service = OrganizationService(db)
    org = service.get_organization(tenant.organization_id)
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return OrganizationResponse.model_validate(org)


@router.get("/current/stats", response_model=OrganizationStatsDTO)
async def get_current_organization_stats(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(mysql.get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get current organization statistics.
    
    Requires admin or super_admin role.
    """
    if not tenant or not tenant.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization context"
        )
    
    if current_user.role not in [Role.ORG_ADMIN, Role.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view organization stats"
        )
    
    service = OrganizationService(db)
    stats = service.get_organization_stats(tenant.organization_id)
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return stats


@router.patch("/current", response_model=OrganizationResponse)
async def update_current_organization(
    request: UpdateOrganizationRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(mysql.get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Update current organization settings.
    
    Requires admin or super_admin role.
    """
    if not tenant or not tenant.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization context"
        )
    
    if current_user.role not in [Role.ORG_ADMIN, Role.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update organization"
        )
    
    service = OrganizationService(db)
    dto = UpdateOrganizationDTO(**request.model_dump())
    
    org, error = service.update_organization(
        tenant.organization_id, dto, current_user.id
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return OrganizationResponse.model_validate(org)


# ============================================================================
# Routes - API Keys
# ============================================================================

@router.post(
    "/current/api-keys",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    request: CreateAPIKeyRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(mysql.get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Create a new API key.
    
    The plain key is only returned once in this response.
    Store it securely - it cannot be retrieved again!
    
    Requires admin role and API keys feature enabled.
    """
    if not tenant or not tenant.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization context"
        )
    
    if current_user.role not in [Role.ORG_ADMIN, Role.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create API keys"
        )
    
    service = OrganizationService(db)
    dto = CreateAPIKeyDTO(**request.model_dump())
    
    plain_key, api_key, error = service.create_api_key(
        tenant.organization_id, current_user.id, dto
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return APIKeyCreateResponse(
        key=plain_key,
        api_key=APIKeyResponse.model_validate(api_key)
    )


@router.get("/current/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(mysql.get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    List all API keys for the current organization.
    
    Requires admin role.
    """
    if not tenant or not tenant.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization context"
        )
    
    if current_user.role not in [Role.ORG_ADMIN, Role.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view API keys"
        )
    
    service = OrganizationService(db)
    api_keys = service.api_key_repo.list_by_organization(tenant.organization_id)
    
    return [APIKeyResponse.model_validate(k) for k in api_keys]


@router.delete("/current/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str = Path(..., description="API key ID"),
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(mysql.get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Revoke an API key.
    
    Requires admin role.
    """
    if not tenant or not tenant.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization context"
        )
    
    if current_user.role not in [Role.ORG_ADMIN, Role.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can revoke API keys"
        )
    
    service = OrganizationService(db)
    success, error = service.revoke_api_key(
        tenant.organization_id, key_id, current_user.id
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "API key revoked successfully"}
    )


# ============================================================================
# Routes - Audit Logs
# ============================================================================

@router.get("/current/audit-logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    action: Optional[str] = Query(None, description="Filter by action"),
    user_id: Optional[str] = Query(None, description="Filter by user"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(mysql.get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get audit logs for the current organization.
    
    Requires admin role and audit logs feature enabled.
    """
    if not tenant or not tenant.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization context"
        )
    
    if current_user.role not in [Role.ORG_ADMIN, Role.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view audit logs"
        )
    
    # Check if audit logs feature is enabled
    service = OrganizationService(db)
    org = service.get_organization(tenant.organization_id)
    
    if not org.features or not org.features.get("audit_logs"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audit logs feature not available on your plan"
        )
    
    logs, total = service.get_audit_logs(
        tenant.organization_id,
        skip=skip,
        limit=limit,
        action=action,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(l) for l in logs],
        total=total,
        skip=skip,
        limit=limit
    )


# ============================================================================
# Routes - Quota Check (for internal use)
# ============================================================================

@router.get("/current/quota/{quota_type}")
async def check_quota(
    quota_type: str = Path(..., description="Quota type: storage, users, files"),
    amount: int = Query(1, description="Amount to check"),
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(mysql.get_db),
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Check if organization has available quota.
    
    Used internally before file uploads, user creation, etc.
    """
    if not tenant or not tenant.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization context"
        )
    
    service = OrganizationService(db)
    has_quota, message = service.check_quota(
        tenant.organization_id, quota_type, amount
    )
    
    return {
        "has_quota": has_quota,
        "message": message,
        "quota_type": quota_type,
        "requested_amount": amount
    }
