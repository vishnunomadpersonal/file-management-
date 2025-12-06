"""
API Routes for Model Versioning.

Provides endpoints for:
- Viewing version history
- Comparing versions
- Rollback operations
- Model status
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel, Field

from src.infrastructure.model_versioning import (
    get_model_manager,
    get_router_model_manager,
    get_incremental_model_manager,
    get_cost_model_manager,
    ModelVersionManager
)
from src.core.security import get_current_user, require_role

router = APIRouter(
    prefix="/api/v1/models",
    tags=["Model Versioning"]
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class RollbackRequest(BaseModel):
    """Request to rollback to a specific version."""
    version: int = Field(..., description="Version number to rollback to")


class CompareRequest(BaseModel):
    """Request to compare two versions."""
    version1: int = Field(..., description="First version to compare")
    version2: int = Field(..., description="Second version to compare")


class VersionInfo(BaseModel):
    """Information about a model version."""
    version: int
    created_at: str
    training_strategy: str
    samples_used: int
    accuracy: Optional[float]
    precision: Optional[float]
    recall: Optional[float]
    f1_score: Optional[float]
    training_time_seconds: float
    model_hash: str
    model_size_bytes: int
    parent_version: Optional[int]
    delta_id: Optional[str]
    is_active: bool


# ============================================================================
# ROUTES
# ============================================================================

@router.get("/")
async def list_models(current_user=Depends(get_current_user)):
    """
    List all tracked models.
    """
    models = [
        "learned_router",
        "incremental_model",
        "cost_optimizer"
    ]
    
    statuses = []
    for model_name in models:
        try:
            manager = get_model_manager(model_name)
            statuses.append({
                "model_name": model_name,
                "total_versions": len(manager.versions),
                "current_version": manager.current_version,
                "has_active_version": manager.get_active_version() is not None
            })
        except Exception as e:
            statuses.append({
                "model_name": model_name,
                "error": str(e)
            })
    
    return {
        "models": statuses,
        "total_models": len(models)
    }


@router.get("/{model_name}")
async def get_model_status(
    model_name: str,
    current_user=Depends(get_current_user)
):
    """
    Get detailed status and version history for a model.
    """
    manager = get_model_manager(model_name)
    return manager.get_status()


@router.get("/{model_name}/versions")
async def list_versions(
    model_name: str,
    current_user=Depends(get_current_user)
):
    """
    List all versions of a model.
    """
    manager = get_model_manager(model_name)
    history = manager.get_version_history()
    
    return {
        "model_name": model_name,
        "total_versions": len(history),
        "current_version": manager.current_version,
        "versions": [
            {
                "version": m.version,
                "created_at": m.created_at,
                "training_strategy": m.training_strategy,
                "samples_used": m.samples_used,
                "accuracy": m.accuracy,
                "f1_score": m.f1_score,
                "model_size_bytes": m.model_size_bytes,
                "is_active": m.is_active
            }
            for m in history
        ]
    }


@router.get("/{model_name}/versions/{version}")
async def get_version_details(
    model_name: str,
    version: int,
    current_user=Depends(get_current_user)
):
    """
    Get detailed information about a specific version.
    """
    manager = get_model_manager(model_name)
    
    if version not in manager.versions:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")
    
    metadata = manager.versions[version]
    
    return {
        "model_name": model_name,
        "version": metadata.version,
        "created_at": metadata.created_at,
        "training_strategy": metadata.training_strategy,
        "samples_used": metadata.samples_used,
        "metrics": {
            "accuracy": metadata.accuracy,
            "precision": metadata.precision,
            "recall": metadata.recall,
            "f1_score": metadata.f1_score
        },
        "training_time_seconds": metadata.training_time_seconds,
        "model_hash": metadata.model_hash,
        "model_size_bytes": metadata.model_size_bytes,
        "parent_version": metadata.parent_version,
        "delta_id": metadata.delta_id,
        "custom_metrics": metadata.custom_metrics,
        "is_active": metadata.is_active
    }


@router.get("/{model_name}/active")
async def get_active_version(
    model_name: str,
    current_user=Depends(get_current_user)
):
    """
    Get information about the currently active version.
    """
    manager = get_model_manager(model_name)
    active = manager.get_active_version()
    
    if not active:
        raise HTTPException(
            status_code=404, 
            detail=f"No active version for model {model_name}"
        )
    
    return {
        "model_name": model_name,
        "active_version": active.version,
        "created_at": active.created_at,
        "training_strategy": active.training_strategy,
        "metrics": {
            "accuracy": active.accuracy,
            "precision": active.precision,
            "recall": active.recall,
            "f1_score": active.f1_score
        }
    }


@router.post("/{model_name}/rollback")
async def rollback_version(
    model_name: str,
    request: RollbackRequest,
    current_user=Depends(require_role(["admin", "manager"]))
):
    """
    Rollback to a previous version.
    
    Requires admin or manager role.
    """
    manager = get_model_manager(model_name)
    
    # Get current version for logging
    previous_version = manager.current_version
    
    success = manager.rollback_to_version(request.version)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to rollback to version {request.version}"
        )
    
    return {
        "success": True,
        "message": f"Rolled back from version {previous_version} to {request.version}",
        "model_name": model_name,
        "previous_version": previous_version,
        "current_version": request.version,
        "initiated_by": current_user.email
    }


@router.post("/{model_name}/compare")
async def compare_versions(
    model_name: str,
    request: CompareRequest,
    current_user=Depends(get_current_user)
):
    """
    Compare two versions of a model.
    """
    manager = get_model_manager(model_name)
    
    comparison = manager.compare_versions(request.version1, request.version2)
    
    if "error" in comparison:
        raise HTTPException(status_code=404, detail=comparison["error"])
    
    return {
        "model_name": model_name,
        "comparison": comparison,
        "summary": _generate_comparison_summary(comparison)
    }


def _generate_comparison_summary(comparison: dict) -> str:
    """Generate a human-readable summary of version comparison."""
    v1, v2 = comparison["version1"], comparison["version2"]
    
    parts = [f"Comparing v{v1} → v{v2}:"]
    
    if comparison["accuracy_diff"] is not None:
        diff = comparison["accuracy_diff"]
        direction = "improved" if diff > 0 else "decreased" if diff < 0 else "unchanged"
        parts.append(f"Accuracy {direction} by {abs(diff):.4f}")
    
    if comparison["f1_diff"] is not None:
        diff = comparison["f1_diff"]
        direction = "improved" if diff > 0 else "decreased" if diff < 0 else "unchanged"
        parts.append(f"F1 Score {direction} by {abs(diff):.4f}")
    
    samples_diff = comparison["samples_diff"]
    parts.append(f"Training samples: {'+' if samples_diff >= 0 else ''}{samples_diff}")
    
    time_diff = comparison["training_time_diff"]
    parts.append(f"Training time: {'+' if time_diff >= 0 else ''}{time_diff:.2f}s")
    
    return " | ".join(parts)


# ============================================================================
# LEARNED ROUTER SPECIFIC ROUTES
# ============================================================================

@router.get("/router/status")
async def get_router_status(current_user=Depends(get_current_user)):
    """Get status of the learned router model."""
    manager = get_router_model_manager()
    return manager.get_status()


@router.post("/router/rollback")
async def rollback_router(
    request: RollbackRequest,
    current_user=Depends(require_role(["admin", "manager"]))
):
    """Rollback the learned router to a previous version."""
    manager = get_router_model_manager()
    success = manager.rollback_to_version(request.version)
    
    if not success:
        raise HTTPException(status_code=400, detail="Rollback failed")
    
    return {"success": True, "message": f"Router rolled back to v{request.version}"}


# ============================================================================
# INCREMENTAL MODEL SPECIFIC ROUTES
# ============================================================================

@router.get("/incremental/status")
async def get_incremental_model_status(current_user=Depends(get_current_user)):
    """Get status of the incremental ML model."""
    manager = get_incremental_model_manager()
    return manager.get_status()


@router.post("/incremental/rollback")
async def rollback_incremental_model(
    request: RollbackRequest,
    current_user=Depends(require_role(["admin", "manager"]))
):
    """Rollback the incremental model to a previous version."""
    manager = get_incremental_model_manager()
    success = manager.rollback_to_version(request.version)
    
    if not success:
        raise HTTPException(status_code=400, detail="Rollback failed")
    
    return {"success": True, "message": f"Incremental model rolled back to v{request.version}"}


# ============================================================================
# COST OPTIMIZER SPECIFIC ROUTES
# ============================================================================

@router.get("/cost/status")
async def get_cost_optimizer_status(current_user=Depends(get_current_user)):
    """Get status of the cost optimizer model."""
    manager = get_cost_model_manager()
    return manager.get_status()


@router.post("/cost/rollback")
async def rollback_cost_optimizer(
    request: RollbackRequest,
    current_user=Depends(require_role(["admin", "manager"]))
):
    """Rollback the cost optimizer to a previous version."""
    manager = get_cost_model_manager()
    success = manager.rollback_to_version(request.version)
    
    if not success:
        raise HTTPException(status_code=400, detail="Rollback failed")
    
    return {"success": True, "message": f"Cost optimizer rolled back to v{request.version}"}
