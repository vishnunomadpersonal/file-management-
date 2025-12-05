"""
Incremental ML Pipeline API Routes

Endpoints for the intelligent incremental ML pipeline system:
- Delta detection and analysis
- Processing strategy routing
- Pipeline execution and monitoring
- Cost estimation and optimization
"""

from fastapi import APIRouter, Depends, Form, UploadFile, Query, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import logging

from infrastructure.db.mysql import mysql
from repositories.delta_repository import DeltaRepo, ModelVersionRepo, PipelineRunRepo
from services.change_detection_service import ChangeDetectionService
from infrastructure.learned_router import learned_router, RouterDecision
from infrastructure.cost_optimizer import cost_optimizer, CostEstimate, OptimizationConstraints
from entities.data_delta import DataDelta, ProcessingStrategy, ModelVersion, PipelineRun
from api.responses.response import SuccessResponse, ErrorResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/pipeline",
    tags=["incremental-ml-pipeline"]
)


# ============== Pydantic Models ==============

class DeltaResponse(BaseModel):
    """Response model for delta detection results."""
    id: str
    file_id: str
    delta_type: str
    change_magnitude: float
    rows_inserted: int
    rows_deleted: int
    rows_updated: int
    entropy_delta: float
    feature_drift_score: float
    is_significant: bool
    detected_at: datetime
    
    class Config:
        from_attributes = True


class RoutingDecisionResponse(BaseModel):
    """Response model for routing decisions."""
    delta_id: str
    strategy: str
    confidence: float
    reasoning: str
    estimated_cost: float
    estimated_accuracy_impact: float


class CostEstimateResponse(BaseModel):
    """Response model for cost estimates."""
    strategy: str
    estimated_time_seconds: float
    estimated_memory_mb: float
    estimated_cost_dollars: float
    expected_accuracy: float
    bottleneck_stage: str
    optimization_suggestions: List[str]


class PipelineStatusResponse(BaseModel):
    """Response model for pipeline status."""
    run_id: str
    pipeline_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    deltas_processed: int
    models_updated: int


class OptimizationRequest(BaseModel):
    """Request model for optimization constraints."""
    max_time_seconds: Optional[float] = None
    max_memory_mb: Optional[float] = None
    max_cost_dollars: Optional[float] = None
    min_accuracy: Optional[float] = None
    priority: str = "balanced"  # speed, accuracy, cost, balanced


# ============== Dependencies ==============

def get_delta_repo(db: Session = Depends(mysql.get_db)) -> DeltaRepo:
    return DeltaRepo(db=db)

def get_model_version_repo(db: Session = Depends(mysql.get_db)) -> ModelVersionRepo:
    return ModelVersionRepo(db=db)

def get_pipeline_run_repo(db: Session = Depends(mysql.get_db)) -> PipelineRunRepo:
    return PipelineRunRepo(db=db)

def get_change_detection_service(db: Session = Depends(mysql.get_db)) -> ChangeDetectionService:
    return ChangeDetectionService(repo=DeltaRepo(db=db))


# ============== Delta Detection Endpoints ==============

@router.post("/detect-changes/{file_id}", response_model=SuccessResponse[DeltaResponse])
async def detect_file_changes(
    file_id: str,
    new_content: UploadFile,
    content_type: str = Form(default="text/csv"),
    service: ChangeDetectionService = Depends(get_change_detection_service)
):
    """
    Detect changes in a file compared to its previous version.
    
    This endpoint:
    1. Reads the new file content
    2. Compares with previous version (if exists)
    3. Calculates delta metrics (change magnitude, drift, etc.)
    4. Stores the delta for processing
    """
    try:
        content = await new_content.read()
        
        # TODO: Get old content from storage
        old_content = None  # For now, treat as new file
        
        delta = await service.detect_changes(
            file_id=file_id,
            new_content=content,
            old_content=old_content,
            content_type=content_type
        )
        
        response = DeltaResponse(
            id=delta.id,
            file_id=delta.file_id,
            delta_type=delta.delta_type,
            change_magnitude=delta.change_magnitude,
            rows_inserted=delta.rows_inserted,
            rows_deleted=delta.rows_deleted,
            rows_updated=delta.rows_updated,
            entropy_delta=delta.entropy_delta,
            feature_drift_score=delta.feature_drift_score,
            is_significant=delta.is_significant_change,
            detected_at=delta.detected_at
        )
        
        return SuccessResponse(data=response, message="Delta detected successfully")
        
    except Exception as e:
        logger.error(f"Error detecting changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deltas/{file_id}", response_model=SuccessResponse[List[DeltaResponse]])
async def get_file_deltas(
    file_id: str,
    repo: DeltaRepo = Depends(get_delta_repo)
):
    """Get all detected deltas for a file."""
    deltas = repo.get_deltas_for_file(file_id)
    
    responses = [
        DeltaResponse(
            id=d.id,
            file_id=d.file_id,
            delta_type=d.delta_type,
            change_magnitude=d.change_magnitude,
            rows_inserted=d.rows_inserted,
            rows_deleted=d.rows_deleted,
            rows_updated=d.rows_updated,
            entropy_delta=d.entropy_delta,
            feature_drift_score=d.feature_drift_score,
            is_significant=d.is_significant_change,
            detected_at=d.detected_at
        )
        for d in deltas
    ]
    
    return SuccessResponse(data=responses)


@router.get("/deltas/unprocessed", response_model=SuccessResponse[List[DeltaResponse]])
async def get_unprocessed_deltas(
    repo: DeltaRepo = Depends(get_delta_repo)
):
    """Get all deltas awaiting processing."""
    deltas = repo.get_unprocessed_deltas()
    
    responses = [
        DeltaResponse(
            id=d.id,
            file_id=d.file_id,
            delta_type=d.delta_type,
            change_magnitude=d.change_magnitude,
            rows_inserted=d.rows_inserted,
            rows_deleted=d.rows_deleted,
            rows_updated=d.rows_updated,
            entropy_delta=d.entropy_delta,
            feature_drift_score=d.feature_drift_score,
            is_significant=d.is_significant_change,
            detected_at=d.detected_at
        )
        for d in deltas
    ]
    
    return SuccessResponse(data=responses)


# ============== Routing Endpoints ==============

@router.post("/route/{delta_id}", response_model=SuccessResponse[RoutingDecisionResponse])
async def route_delta(
    delta_id: str,
    repo: DeltaRepo = Depends(get_delta_repo)
):
    """
    Get processing strategy recommendation for a delta.
    
    Uses the learned router to determine optimal processing:
    - SKIP: Change too small
    - INCREMENTAL: Apply incremental update
    - PARTIAL_RETRAIN: Retrain affected components
    - FULL_RETRAIN: Complete model retraining
    """
    delta = repo.get(id=delta_id)
    if not delta:
        raise HTTPException(status_code=404, detail="Delta not found")
    
    decision = await learned_router.route(delta)
    
    # Update delta with routing decision
    delta.processing_strategy = decision.strategy.value
    delta.strategy_confidence = decision.confidence
    delta.estimated_cost = decision.estimated_cost
    repo.db.commit()
    
    return SuccessResponse(
        data=RoutingDecisionResponse(
            delta_id=delta_id,
            strategy=decision.strategy.value,
            confidence=decision.confidence,
            reasoning=decision.reasoning,
            estimated_cost=decision.estimated_cost,
            estimated_accuracy_impact=decision.estimated_accuracy_impact
        ),
        message="Routing decision made"
    )


# ============== Cost Optimization Endpoints ==============

@router.post("/estimate-cost/{delta_id}", response_model=SuccessResponse[List[CostEstimateResponse]])
async def estimate_processing_costs(
    delta_id: str,
    repo: DeltaRepo = Depends(get_delta_repo)
):
    """
    Estimate processing costs for all strategies.
    
    Returns detailed cost breakdown for each strategy including:
    - Time and memory estimates
    - Monetary cost
    - Expected accuracy impact
    - Optimization suggestions
    """
    delta = repo.get(id=delta_id)
    if not delta:
        raise HTTPException(status_code=404, detail="Delta not found")
    
    strategies = [
        ProcessingStrategy.SKIP,
        ProcessingStrategy.INCREMENTAL,
        ProcessingStrategy.PARTIAL_RETRAIN,
        ProcessingStrategy.FULL_RETRAIN
    ]
    
    estimates = []
    for strategy in strategies:
        estimate = await cost_optimizer.estimate_cost(delta, strategy)
        estimates.append(CostEstimateResponse(
            strategy=strategy.value,
            estimated_time_seconds=estimate.estimated_time_seconds,
            estimated_memory_mb=estimate.estimated_memory_mb,
            estimated_cost_dollars=estimate.estimated_cost_dollars,
            expected_accuracy=estimate.expected_accuracy,
            bottleneck_stage=estimate.bottleneck_stage,
            optimization_suggestions=estimate.optimization_suggestions
        ))
    
    return SuccessResponse(data=estimates)


@router.post("/optimize/{delta_id}", response_model=SuccessResponse[CostEstimateResponse])
async def optimize_strategy(
    delta_id: str,
    constraints: OptimizationRequest,
    repo: DeltaRepo = Depends(get_delta_repo)
):
    """
    Find optimal processing strategy given constraints.
    
    Considers:
    - Time limits
    - Memory limits
    - Cost budget
    - Minimum accuracy requirements
    - Priority preference (speed, accuracy, cost, balanced)
    """
    delta = repo.get(id=delta_id)
    if not delta:
        raise HTTPException(status_code=404, detail="Delta not found")
    
    # Get router decision first
    router_decision = await learned_router.route(delta)
    
    # Build constraints
    opt_constraints = OptimizationConstraints(
        max_time_seconds=constraints.max_time_seconds,
        max_memory_mb=constraints.max_memory_mb,
        max_cost_dollars=constraints.max_cost_dollars,
        min_accuracy=constraints.min_accuracy,
        priority=constraints.priority
    )
    
    # Optimize
    optimal_strategy, estimate, reasoning = await cost_optimizer.optimize(
        delta, router_decision, opt_constraints
    )
    
    return SuccessResponse(
        data=CostEstimateResponse(
            strategy=optimal_strategy.value,
            estimated_time_seconds=estimate.estimated_time_seconds,
            estimated_memory_mb=estimate.estimated_memory_mb,
            estimated_cost_dollars=estimate.estimated_cost_dollars,
            expected_accuracy=estimate.expected_accuracy,
            bottleneck_stage=estimate.bottleneck_stage,
            optimization_suggestions=[reasoning] + estimate.optimization_suggestions
        ),
        message=f"Optimal strategy: {optimal_strategy.value}"
    )


# ============== Pipeline Execution Endpoints ==============

@router.post("/execute/{delta_id}", response_model=SuccessResponse[PipelineStatusResponse])
async def execute_pipeline(
    delta_id: str,
    strategy: Optional[str] = Query(None, description="Override strategy (skip, incremental, partial, full)"),
    repo: DeltaRepo = Depends(get_delta_repo),
    run_repo: PipelineRunRepo = Depends(get_pipeline_run_repo)
):
    """
    Execute the ML pipeline for a delta.
    
    If no strategy specified, uses the learned router's recommendation.
    """
    delta = repo.get(id=delta_id)
    if not delta:
        raise HTTPException(status_code=404, detail="Delta not found")
    
    # Determine strategy
    if strategy:
        processing_strategy = ProcessingStrategy(strategy)
    elif delta.processing_strategy:
        processing_strategy = ProcessingStrategy(delta.processing_strategy)
    else:
        decision = await learned_router.route(delta)
        processing_strategy = decision.strategy
    
    # Create pipeline run
    run = PipelineRun(
        pipeline_name="incremental_ml_pipeline",
        trigger_type="api_call",
        trigger_file_id=delta.file_id,
        status="running"
    )
    run_repo.create(run)
    
    # TODO: Actually execute pipeline based on strategy
    # For now, simulate execution
    logger.info(f"Executing pipeline for delta {delta_id} with strategy {processing_strategy.value}")
    
    # Mark delta as processed
    delta.is_processed = True
    delta.processed_at = datetime.utcnow()
    delta.processing_strategy = processing_strategy.value
    repo.db.commit()
    
    # Complete run
    run.status = "completed"
    run.completed_at = datetime.utcnow()
    run.deltas_processed = 1
    run_repo.db.commit()
    
    return SuccessResponse(
        data=PipelineStatusResponse(
            run_id=run.id,
            pipeline_name=run.pipeline_name,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            deltas_processed=run.deltas_processed,
            models_updated=run.models_updated
        ),
        message=f"Pipeline executed with strategy: {processing_strategy.value}"
    )


@router.get("/runs", response_model=SuccessResponse[List[PipelineStatusResponse]])
async def get_pipeline_runs(
    pipeline_name: str = Query(default="incremental_ml_pipeline"),
    limit: int = Query(default=10, le=100),
    repo: PipelineRunRepo = Depends(get_pipeline_run_repo)
):
    """Get recent pipeline runs."""
    runs = repo.get_recent_runs(pipeline_name, limit)
    
    responses = [
        PipelineStatusResponse(
            run_id=r.id,
            pipeline_name=r.pipeline_name,
            status=r.status,
            started_at=r.started_at,
            completed_at=r.completed_at,
            deltas_processed=r.deltas_processed,
            models_updated=r.models_updated
        )
        for r in runs
    ]
    
    return SuccessResponse(data=responses)


# ============== Analytics Endpoints ==============

@router.get("/analytics/drift-summary")
async def get_drift_summary(
    hours: int = Query(default=24, description="Look back period in hours"),
    repo: DeltaRepo = Depends(get_delta_repo)
):
    """Get summary of feature drift over recent period."""
    deltas = repo.get_recent_deltas(hours)
    
    if not deltas:
        return SuccessResponse(data={
            "period_hours": hours,
            "total_deltas": 0,
            "avg_drift": 0,
            "max_drift": 0,
            "high_drift_count": 0
        })
    
    drift_scores = [d.feature_drift_score for d in deltas]
    
    return SuccessResponse(data={
        "period_hours": hours,
        "total_deltas": len(deltas),
        "avg_drift": sum(drift_scores) / len(drift_scores),
        "max_drift": max(drift_scores),
        "min_drift": min(drift_scores),
        "high_drift_count": len([d for d in drift_scores if d > 0.2]),
        "strategy_distribution": {
            "skip": len([d for d in deltas if d.processing_strategy == "skip"]),
            "incremental": len([d for d in deltas if d.processing_strategy == "incremental"]),
            "partial": len([d for d in deltas if d.processing_strategy == "partial"]),
            "full": len([d for d in deltas if d.processing_strategy == "full"])
        }
    })


@router.get("/analytics/cost-savings")
async def get_cost_savings(
    hours: int = Query(default=24),
    repo: DeltaRepo = Depends(get_delta_repo)
):
    """Calculate cost savings from incremental processing."""
    deltas = repo.get_recent_deltas(hours)
    processed_deltas = [d for d in deltas if d.is_processed]
    
    if not processed_deltas:
        return SuccessResponse(data={
            "period_hours": hours,
            "total_processed": 0,
            "estimated_savings": 0
        })
    
    # Estimate savings (what full retrain would have cost vs what was used)
    total_savings = sum(d.cost_savings or 0 for d in processed_deltas)
    
    return SuccessResponse(data={
        "period_hours": hours,
        "total_processed": len(processed_deltas),
        "estimated_savings_dollars": total_savings,
        "avg_processing_time_ms": sum(d.processing_time_ms or 0 for d in processed_deltas) / len(processed_deltas)
    })


@router.post("/router/train")
async def train_router(
    repo: DeltaRepo = Depends(get_delta_repo)
):
    """
    Train the learned router on historical data.
    
    Uses processed deltas and their outcomes to improve
    the router's decision making.
    """
    # Get training data
    deltas = repo.get_training_data(limit=1000)
    
    if len(deltas) < 50:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient training data. Need at least 50 processed deltas, have {len(deltas)}"
        )
    
    # Build outcomes from historical data
    outcomes = [
        {
            'strategy_used': d.processing_strategy,
            'accuracy_drop': 0.01,  # Would come from model evaluation
            'actual_cost': d.actual_cost or 0
        }
        for d in deltas
    ]
    
    # Train
    metrics = await learned_router.train(deltas, outcomes)
    
    return SuccessResponse(
        data=metrics,
        message=f"Router trained on {len(deltas)} samples"
    )
