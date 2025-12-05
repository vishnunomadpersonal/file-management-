"""
Pipeline Orchestrator - Coordinates the entire incremental ML pipeline.

This is the central coordinator that:
1. Auto-triggers on file upload completion
2. Orchestrates delta detection → routing → optimization → execution
3. Records outcomes for the feedback loop
4. Updates cost models and router based on actual results

This ties together all the components into a cohesive system that
demonstrates IVM concepts applied to ML pipelines.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from io import BytesIO
import pandas as pd

from sqlalchemy.orm import Session

from entities.data_delta import DataDelta, ProcessingStrategy, ModelVersion, PipelineRun
from entities.file import File
from repositories.delta_repository import DeltaRepo, ModelVersionRepo, PipelineRunRepo
from repositories.file_repository import FileRepo
from services.change_detection_service import ChangeDetectionService
from infrastructure.learned_router import learned_router, RouterDecision
from infrastructure.cost_optimizer import cost_optimizer, OptimizationConstraints
from infrastructure.incremental_model import get_default_model, IncrementalModel
from infrastructure.minio import minioStorage

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the incremental ML pipeline from trigger to completion.
    
    The pipeline flow:
    1. TRIGGER: Called when a file upload completes (CSV/data files)
    2. DETECT: Analyze changes vs previous version
    3. ROUTE: ML-based decision on processing strategy
    4. OPTIMIZE: Cost-based refinement of strategy
    5. EXECUTE: Apply the chosen strategy to update the model
    6. RECORD: Store outcomes for feedback loop
    7. LEARN: Update router and cost models based on actual results
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.delta_repo = DeltaRepo(db)
        self.model_repo = ModelVersionRepo(db)
        self.run_repo = PipelineRunRepo(db)
        self.file_repo = FileRepo(db)
        self.change_service = ChangeDetectionService(self.delta_repo)
        
        # Initialize feedback service
        from services.feedback_loop_service import FeedbackLoopService
        self.feedback_service = FeedbackLoopService(db)
    
    async def on_file_uploaded(
        self,
        file: File,
        constraints: Optional[OptimizationConstraints] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Auto-trigger entry point - called when a file upload completes.
        
        Only processes CSV and data files that could be training data.
        
        Args:
            file: The uploaded File entity
            constraints: Optional optimization constraints
            
        Returns:
            Pipeline execution result or None if not applicable
        """
        # Only process data files (CSV, JSON, Parquet)
        content_type = file.content_type or ""
        filename = file.filename or ""
        
        supported_types = [
            'text/csv',
            'application/json',
            'application/x-parquet',
            'text/plain'  # Often used for CSV
        ]
        
        supported_extensions = ['.csv', '.json', '.parquet', '.tsv']
        
        is_data_file = (
            any(ct in content_type.lower() for ct in supported_types) or
            any(filename.lower().endswith(ext) for ext in supported_extensions)
        )
        
        if not is_data_file:
            logger.debug(f"Skipping non-data file: {filename} ({content_type})")
            return None
        
        logger.info(f"Pipeline auto-triggered for file: {filename} (id={file.id})")
        
        try:
            result = await self.run_pipeline(
                file_id=file.id,
                constraints=constraints
            )
            return result
        except Exception as e:
            logger.error(f"Pipeline failed for file {file.id}: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'file_id': file.id
            }
    
    async def run_pipeline(
        self,
        file_id: str,
        constraints: Optional[OptimizationConstraints] = None,
        target_column: str = 'target'
    ) -> Dict[str, Any]:
        """
        Execute the full pipeline for a file.
        
        Args:
            file_id: ID of the file to process
            constraints: Optimization constraints
            target_column: Name of target column for ML
            
        Returns:
            Comprehensive result dictionary
        """
        pipeline_start = datetime.utcnow()
        
        # Create pipeline run record
        run = PipelineRun(
            pipeline_name=f"incremental_ml_{file_id[:8]}",
            status='running',
            started_at=pipeline_start
        )
        self.db.add(run)
        self.db.commit()
        
        result = {
            'run_id': run.id,
            'file_id': file_id,
            'status': 'running',
            'stages': {}
        }
        
        try:
            # ===== STAGE 1: Load Data =====
            logger.info(f"[Stage 1] Loading data for file {file_id}")
            new_content, old_content, file = await self._load_file_versions(file_id)
            
            result['stages']['load'] = {
                'status': 'completed',
                'new_size': len(new_content) if new_content else 0,
                'old_size': len(old_content) if old_content else 0
            }
            
            # ===== STAGE 2: Detect Changes =====
            logger.info(f"[Stage 2] Detecting changes")
            delta = await self.change_service.detect_changes(
                file_id=file_id,
                new_content=new_content,
                old_content=old_content,
                content_type=file.content_type or 'text/csv'
            )
            
            result['stages']['detect'] = {
                'status': 'completed',
                'delta_id': delta.id,
                'delta_type': delta.delta_type,
                'change_magnitude': delta.change_magnitude,
                'is_significant': delta.is_significant_change,
                'rows_inserted': delta.rows_inserted,
                'rows_deleted': delta.rows_deleted,
                'rows_updated': delta.rows_updated,
                'feature_drift': delta.feature_drift_score
            }
            
            # ===== STAGE 3: Route (ML Decision) =====
            logger.info(f"[Stage 3] Routing decision")
            router_decision = await learned_router.route(delta)
            
            result['stages']['route'] = {
                'status': 'completed',
                'strategy': router_decision.strategy.value,
                'confidence': router_decision.confidence,
                'reasoning': router_decision.reasoning
            }
            
            # ===== STAGE 4: Optimize (Cost-Based Refinement) =====
            logger.info(f"[Stage 4] Cost optimization")
            constraints = constraints or OptimizationConstraints(priority="balanced")
            
            final_strategy, cost_estimate, opt_reasoning = await cost_optimizer.optimize(
                delta=delta,
                router_decision=router_decision,
                constraints=constraints
            )
            
            result['stages']['optimize'] = {
                'status': 'completed',
                'final_strategy': final_strategy.value,
                'estimated_time': cost_estimate.estimated_time_seconds,
                'estimated_cost': cost_estimate.estimated_cost_dollars,
                'expected_accuracy': cost_estimate.expected_accuracy,
                'reasoning': opt_reasoning
            }
            
            # ===== STAGE 5: Execute ML Update =====
            logger.info(f"[Stage 5] Executing {final_strategy.value}")
            
            # Parse data into DataFrame
            new_df = self._parse_to_dataframe(new_content, file.content_type)
            old_df = self._parse_to_dataframe(old_content, file.content_type) if old_content else None
            
            # Detect target column if not specified
            target_column = self._detect_target_column(new_df, target_column)
            
            # Get model and execute
            model = get_default_model()
            metrics = await model.process_delta(
                delta=delta,
                strategy=final_strategy,
                new_data=new_df,
                old_data=old_df,
                target_column=target_column
            )
            
            result['stages']['execute'] = {
                'status': 'completed',
                'strategy_used': metrics.strategy_used.value,
                'time_seconds': metrics.time_seconds,
                'memory_mb': metrics.memory_mb,
                'accuracy_before': metrics.accuracy_before,
                'accuracy_after': metrics.accuracy_after,
                'samples_processed': metrics.samples_processed
            }
            
            # ===== STAGE 6: Record Outcome =====
            logger.info(f"[Stage 6] Recording outcome")
            
            # Update delta with processing results
            delta.processed_at = datetime.utcnow()
            delta.processing_strategy = final_strategy.value
            
            # Create model version record
            if model.state:
                model_version = ModelVersion(
                    model_name="incremental_ml_model",
                    version_number=model.state.version,
                    accuracy=metrics.accuracy_after,
                    training_samples=metrics.samples_processed,
                    delta_id=delta.id
                )
                self.db.add(model_version)
            
            # Update pipeline run
            run.status = 'completed'
            run.completed_at = datetime.utcnow()
            run.result_summary = {
                'strategy': final_strategy.value,
                'accuracy_change': metrics.accuracy_after - metrics.accuracy_before,
                'time_seconds': metrics.time_seconds
            }
            
            self.db.commit()
            
            result['stages']['record'] = {'status': 'completed'}
            
            # ===== STAGE 7: Feedback Loop =====
            logger.info(f"[Stage 7] Updating cost models")
            
            await self._update_feedback_loop(
                delta=delta,
                strategy=final_strategy,
                cost_estimate=cost_estimate,
                actual_metrics=metrics
            )
            
            result['stages']['feedback'] = {'status': 'completed'}
            
            # Final result
            result['status'] = 'completed'
            result['completed_at'] = datetime.utcnow().isoformat()
            result['summary'] = {
                'strategy': final_strategy.value,
                'accuracy_before': metrics.accuracy_before,
                'accuracy_after': metrics.accuracy_after,
                'accuracy_change': metrics.accuracy_after - metrics.accuracy_before,
                'time_seconds': metrics.time_seconds,
                'cost_dollars': cost_estimate.estimated_cost_dollars
            }
            
            logger.info(f"Pipeline completed: {final_strategy.value}, accuracy {metrics.accuracy_before:.3f} -> {metrics.accuracy_after:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            
            # Update run status
            run.status = 'failed'
            run.completed_at = datetime.utcnow()
            run.result_summary = {'error': str(e)}
            self.db.commit()
            
            result['status'] = 'failed'
            result['error'] = str(e)
            return result
    
    async def _load_file_versions(
        self,
        file_id: str
    ) -> tuple[Optional[bytes], Optional[bytes], File]:
        """Load current and previous versions of a file."""
        
        # Get file record
        file = self.file_repo.get_file(file_id)
        if not file:
            raise ValueError(f"File not found: {file_id}")
        
        # Load new content from MinIO
        new_content = None
        try:
            bucket_name = file.path.split("/")[0]
            object_name = "/".join(file.path.split("/")[1:])
            
            response = minioStorage.get_object(bucket_name, object_name)
            new_content = response.read()
            response.close()
            response.release_conn()
        except Exception as e:
            logger.error(f"Failed to load file from MinIO: {e}")
            raise
        
        # Try to get previous version
        old_content = None
        previous_deltas = self.delta_repo.get_deltas_for_file(file_id)
        if previous_deltas:
            # We could store snapshots, but for now we mark as new file
            pass
        
        return new_content, old_content, file
    
    def _parse_to_dataframe(
        self,
        content: Optional[bytes],
        content_type: Optional[str]
    ) -> Optional[pd.DataFrame]:
        """Parse file content to DataFrame."""
        if content is None:
            return None
        
        try:
            content_type = content_type or 'text/csv'
            
            if 'csv' in content_type.lower() or content_type == 'text/plain':
                return pd.read_csv(BytesIO(content))
            elif 'json' in content_type.lower():
                return pd.read_json(BytesIO(content))
            elif 'parquet' in content_type.lower():
                return pd.read_parquet(BytesIO(content))
            else:
                # Try CSV as default
                return pd.read_csv(BytesIO(content))
        except Exception as e:
            logger.error(f"Failed to parse content: {e}")
            raise
    
    def _detect_target_column(
        self,
        df: pd.DataFrame,
        default: str = 'target'
    ) -> str:
        """Auto-detect the target column in a DataFrame."""
        
        # If specified column exists, use it
        if default in df.columns:
            return default
        
        # Common target column names
        common_names = ['target', 'label', 'class', 'y', 'outcome', 'result']
        for name in common_names:
            if name in df.columns:
                return name
            if name.lower() in [c.lower() for c in df.columns]:
                # Find the actual case-matched column
                for col in df.columns:
                    if col.lower() == name.lower():
                        return col
        
        # Use last column as fallback
        return df.columns[-1]
    
    async def _update_feedback_loop(
        self,
        delta: DataDelta,
        strategy: ProcessingStrategy,
        cost_estimate,
        actual_metrics
    ):
        """Update cost models and router based on actual results."""
        
        # Update cost optimizer with actual measurements
        await cost_optimizer.update_from_feedback(
            strategy=strategy,
            estimated=cost_estimate,
            actual={
                'time_seconds': actual_metrics.time_seconds,
                'memory_mb': actual_metrics.memory_mb,
                'accuracy_after': actual_metrics.accuracy_after
            }
        )
        
        # Record outcome in feedback service
        await self.feedback_service.record_outcome(
            delta=delta,
            strategy=strategy,
            estimated_time=cost_estimate.estimated_time_seconds,
            estimated_memory=cost_estimate.estimated_memory_mb,
            estimated_accuracy=cost_estimate.expected_accuracy,
            actual_time=actual_metrics.time_seconds,
            actual_memory=actual_metrics.memory_mb,
            actual_accuracy=actual_metrics.accuracy_after,
            accuracy_before=actual_metrics.accuracy_before
        )
        
        logger.info(
            f"Feedback recorded: estimated_time={cost_estimate.estimated_time_seconds:.1f}s, "
            f"actual_time={actual_metrics.time_seconds:.1f}s"
        )


# Factory function
def create_orchestrator(db: Session) -> PipelineOrchestrator:
    """Create a pipeline orchestrator instance."""
    return PipelineOrchestrator(db)
