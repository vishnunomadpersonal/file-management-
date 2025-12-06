"""
API Routes for Feedback Management.

Provides endpoints for:
- Recording feedback
- Viewing feedback history
- Triggering training
- Training history
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from pydantic import BaseModel, Field

from src.services.feedback_service import get_feedback_service
from src.infrastructure.db.database import get_db
from src.core.security import get_current_user, require_role

router = APIRouter(
    prefix="/api/v1/feedback",
    tags=["Feedback & Learning"]
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class RecordPredictionRequest(BaseModel):
    """Request to record a prediction."""
    delta_id: str
    strategy: str = Field(..., description="full, incremental, partial, or skip")
    predicted_cost: float
    predicted_benefit: float
    delta_size: int
    delta_significance: float
    affected_tables: Optional[List[str]] = None
    predicted_accuracy: Optional[float] = None


class RecordOutcomeRequest(BaseModel):
    """Request to record an outcome."""
    actual_cost: float
    actual_benefit: float
    actual_accuracy: Optional[float] = None
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    user_comment: Optional[str] = None


class CompleteFeedbackRequest(BaseModel):
    """Request to record complete feedback (prediction + outcome)."""
    delta_id: str
    strategy: str
    predicted_cost: float
    actual_cost: float
    predicted_benefit: float
    actual_benefit: float
    delta_size: int
    delta_significance: float
    affected_tables: Optional[List[str]] = None
    predicted_accuracy: Optional[float] = None
    actual_accuracy: Optional[float] = None


class TrainRequest(BaseModel):
    """Request to trigger training."""
    force: bool = Field(
        False, 
        description="Train even if minimum samples not reached"
    )


# ============================================================================
# ROUTES
# ============================================================================

@router.post("/predict")
async def record_prediction(
    request: RecordPredictionRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Record a prediction before executing a strategy.
    
    Call this when a routing decision is made, before executing.
    Returns a feedback_id to use when recording the outcome.
    """
    service = get_feedback_service(db)
    
    feedback_id = service.record_prediction(
        delta_id=request.delta_id,
        strategy=request.strategy,
        predicted_cost=request.predicted_cost,
        predicted_benefit=request.predicted_benefit,
        delta_size=request.delta_size,
        delta_significance=request.delta_significance,
        affected_tables=request.affected_tables,
        predicted_accuracy=request.predicted_accuracy
    )
    
    return {
        "success": True,
        "feedback_id": feedback_id,
        "message": "Prediction recorded. Call /outcome/{feedback_id} after execution."
    }


@router.post("/outcome/{feedback_id}")
async def record_outcome(
    feedback_id: str,
    request: RecordOutcomeRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Record the actual outcome after executing a strategy.
    
    Call this after the strategy has been executed with real results.
    """
    service = get_feedback_service(db)
    
    feedback = service.record_outcome(
        feedback_id=feedback_id,
        actual_cost=request.actual_cost,
        actual_benefit=request.actual_benefit,
        actual_accuracy=request.actual_accuracy,
        user_rating=request.user_rating,
        user_comment=request.user_comment
    )
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return {
        "success": True,
        "feedback_id": feedback_id,
        "was_correct": feedback.was_correct,
        "improvement_ratio": feedback.improvement_ratio
    }


@router.post("/complete")
async def record_complete_feedback(
    request: CompleteFeedbackRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Record complete feedback (prediction + outcome) in one call.
    
    Use this when you have both prediction and outcome available together.
    """
    service = get_feedback_service(db)
    
    feedback_id = service.record_complete_feedback(
        delta_id=request.delta_id,
        strategy=request.strategy,
        predicted_cost=request.predicted_cost,
        actual_cost=request.actual_cost,
        predicted_benefit=request.predicted_benefit,
        actual_benefit=request.actual_benefit,
        delta_size=request.delta_size,
        delta_significance=request.delta_significance,
        affected_tables=request.affected_tables,
        predicted_accuracy=request.predicted_accuracy,
        actual_accuracy=request.actual_accuracy
    )
    
    return {
        "success": True,
        "feedback_id": feedback_id,
        "message": "Complete feedback recorded"
    }


@router.get("/readiness")
async def get_training_readiness(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Check if we're ready to train the router model.
    
    Returns:
    - ready_for_training: Boolean
    - available_samples: Number of unused feedback samples
    - min_samples_required: Minimum needed for training
    """
    service = get_feedback_service(db)
    return service.get_training_readiness()


@router.post("/train")
async def trigger_training(
    request: TrainRequest,
    db=Depends(get_db),
    current_user=Depends(require_role(["admin", "manager"]))
):
    """
    Trigger router training with accumulated feedback.
    
    Requires admin or manager role.
    
    The router model will be retrained using feedback data.
    A new model version will be saved with rollback capability.
    """
    service = get_feedback_service(db)
    
    result = service.train_router(force=request.force)
    
    if result is None:
        readiness = service.get_training_readiness()
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Not enough feedback for training",
                "available_samples": readiness["available_samples"],
                "min_samples_required": readiness["min_samples_required"],
                "hint": "Use force=true to train anyway"
            }
        )
    
    return {
        "success": True,
        "training_result": result
    }


@router.get("/history")
async def get_feedback_history(
    hours: int = 24,
    limit: int = 100,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get recent feedback history.
    
    Args:
        hours: How far back to look (default 24)
        limit: Maximum number of records (default 100)
    """
    service = get_feedback_service(db)
    history = service.get_feedback_history(hours=hours, limit=limit)
    
    return {
        "total": len(history),
        "feedback": history
    }


@router.get("/training-history")
async def get_training_history(
    limit: int = 10,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get training history.
    
    Shows past training sessions with their results.
    """
    service = get_feedback_service(db)
    history = service.get_training_history(limit=limit)
    
    return {
        "total": len(history),
        "trainings": history
    }


@router.get("/stats")
async def get_feedback_stats(
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get comprehensive feedback and training statistics.
    """
    service = get_feedback_service(db)
    return service.get_stats()


@router.delete("/reset")
async def reset_unused_feedback(
    db=Depends(get_db),
    current_user=Depends(require_role(["admin"]))
):
    """
    Reset unused feedback (admin only).
    
    Marks all unused feedback as used without training.
    Use with caution - this discards training data.
    """
    service = get_feedback_service(db)
    
    # Get unused feedback
    unused = service.feedback_repo.get_unused_for_training()
    
    if not unused:
        return {"success": True, "message": "No unused feedback to reset"}
    
    # Mark as used
    service.feedback_repo.mark_as_used_for_training(
        [f.id for f in unused],
        batch_id="manual_reset"
    )
    
    return {
        "success": True,
        "message": f"Reset {len(unused)} feedback entries",
        "count": len(unused)
    }
