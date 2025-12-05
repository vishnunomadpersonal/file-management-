"""
Delta Repository - Data access layer for DataDelta and related entities.
"""

from repositories.base_repository import BaseRepo
from entities.data_delta import DataDelta, ModelVersion, PipelineRun
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta


class DeltaRepo(BaseRepo[DataDelta]):
    """Repository for DataDelta entity operations."""
    
    def __init__(self, db: Session) -> None:
        super().__init__(DataDelta, db)
    
    def get_deltas_for_file(self, file_id: str) -> List[DataDelta]:
        """Get all deltas for a specific file, ordered by detection time."""
        return (
            self.db
            .query(self.model)
            .filter(self.model.file_id == file_id)
            .order_by(desc(self.model.detected_at))
            .all()
        )
    
    def get_latest_delta(self, file_id: str) -> Optional[DataDelta]:
        """Get the most recent delta for a file."""
        return (
            self.db
            .query(self.model)
            .filter(self.model.file_id == file_id)
            .order_by(desc(self.model.detected_at))
            .first()
        )
    
    def get_unprocessed_deltas(self) -> List[DataDelta]:
        """Get all deltas that haven't been processed yet."""
        return (
            self.db
            .query(self.model)
            .filter(self.model.is_processed == False)
            .order_by(self.model.detected_at)
            .all()
        )
    
    def get_deltas_by_strategy(self, strategy: str) -> List[DataDelta]:
        """Get all deltas processed with a specific strategy."""
        return (
            self.db
            .query(self.model)
            .filter(self.model.processing_strategy == strategy)
            .all()
        )
    
    def get_recent_deltas(self, hours: int = 24) -> List[DataDelta]:
        """Get deltas detected in the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return (
            self.db
            .query(self.model)
            .filter(self.model.detected_at >= cutoff)
            .order_by(desc(self.model.detected_at))
            .all()
        )
    
    def get_high_drift_deltas(self, threshold: float = 0.2) -> List[DataDelta]:
        """Get deltas with high feature drift."""
        return (
            self.db
            .query(self.model)
            .filter(self.model.feature_drift_score >= threshold)
            .order_by(desc(self.model.feature_drift_score))
            .all()
        )
    
    def mark_processed(
        self, 
        delta_id: str, 
        processing_time_ms: int,
        error: Optional[str] = None
    ) -> DataDelta:
        """Mark a delta as processed."""
        delta = self.get(id=delta_id)
        if delta:
            delta.is_processed = True
            delta.processed_at = datetime.utcnow()
            delta.processing_time_ms = processing_time_ms
            if error:
                delta.processing_error = error
            self.db.commit()
            self.db.refresh(delta)
        return delta
    
    def get_training_data(self, limit: int = 1000) -> List[DataDelta]:
        """Get processed deltas for training the learned router."""
        return (
            self.db
            .query(self.model)
            .filter(
                self.model.is_processed == True,
                self.model.processing_error == None
            )
            .order_by(desc(self.model.processed_at))
            .limit(limit)
            .all()
        )


class ModelVersionRepo(BaseRepo[ModelVersion]):
    """Repository for ModelVersion entity operations."""
    
    def __init__(self, db: Session) -> None:
        super().__init__(ModelVersion, db)
    
    def get_active_version(self, model_name: str) -> Optional[ModelVersion]:
        """Get the currently active version of a model."""
        return (
            self.db
            .query(self.model)
            .filter(
                self.model.model_name == model_name,
                self.model.is_active == True
            )
            .first()
        )
    
    def get_all_versions(self, model_name: str) -> List[ModelVersion]:
        """Get all versions of a model, ordered by version number."""
        return (
            self.db
            .query(self.model)
            .filter(self.model.model_name == model_name)
            .order_by(desc(self.model.version))
            .all()
        )
    
    def set_active(self, model_id: str) -> ModelVersion:
        """Set a specific version as active, deactivating others."""
        version = self.get(id=model_id)
        if version:
            # Deactivate all other versions of this model
            self.db.query(self.model).filter(
                self.model.model_name == version.model_name,
                self.model.id != model_id
            ).update({'is_active': False})
            
            version.is_active = True
            self.db.commit()
            self.db.refresh(version)
        return version
    
    def get_latest_version_number(self, model_name: str) -> int:
        """Get the latest version number for a model."""
        latest = (
            self.db
            .query(self.model)
            .filter(self.model.model_name == model_name)
            .order_by(desc(self.model.version))
            .first()
        )
        return latest.version if latest else 0


class PipelineRunRepo(BaseRepo[PipelineRun]):
    """Repository for PipelineRun entity operations."""
    
    def __init__(self, db: Session) -> None:
        super().__init__(PipelineRun, db)
    
    def get_running_pipelines(self) -> List[PipelineRun]:
        """Get all currently running pipelines."""
        return (
            self.db
            .query(self.model)
            .filter(self.model.status == 'running')
            .all()
        )
    
    def get_recent_runs(self, pipeline_name: str, limit: int = 10) -> List[PipelineRun]:
        """Get recent runs for a specific pipeline."""
        return (
            self.db
            .query(self.model)
            .filter(self.model.pipeline_name == pipeline_name)
            .order_by(desc(self.model.started_at))
            .limit(limit)
            .all()
        )
    
    def complete_run(
        self, 
        run_id: str, 
        status: str = 'completed',
        error_message: Optional[str] = None,
        metrics: Optional[dict] = None
    ) -> PipelineRun:
        """Mark a pipeline run as complete."""
        run = self.get(id=run_id)
        if run:
            run.completed_at = datetime.utcnow()
            run.status = status
            if error_message:
                run.error_message = error_message
            if metrics:
                run.peak_memory_mb = metrics.get('peak_memory_mb')
                run.total_cpu_seconds = metrics.get('cpu_seconds')
                run.actual_cost = metrics.get('actual_cost')
            self.db.commit()
            self.db.refresh(run)
        return run
    
    def get_average_metrics(self, pipeline_name: str, last_n: int = 10) -> dict:
        """Calculate average metrics from recent runs."""
        runs = self.get_recent_runs(pipeline_name, last_n)
        
        if not runs:
            return {}
        
        completed_runs = [r for r in runs if r.status == 'completed' and r.completed_at]
        if not completed_runs:
            return {}
        
        durations = [
            (r.completed_at - r.started_at).total_seconds() 
            for r in completed_runs
        ]
        
        return {
            'avg_duration_seconds': sum(durations) / len(durations),
            'avg_memory_mb': sum(r.peak_memory_mb or 0 for r in completed_runs) / len(completed_runs),
            'avg_cost': sum(r.actual_cost or 0 for r in completed_runs) / len(completed_runs),
            'success_rate': len(completed_runs) / len(runs)
        }
