"""
Repository for Pipeline Feedback - Database Operations.

Handles CRUD operations for pipeline feedback and training records.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from src.entities.pipeline_feedback import PipelineFeedback, RouterTrainingRecord
from src.repositories.base_repository import BaseRepository


class FeedbackRepository(BaseRepository[PipelineFeedback]):
    """Repository for pipeline feedback operations."""
    
    def __init__(self, db: Session):
        super().__init__(PipelineFeedback, db)
    
    def find_by_delta_id(self, delta_id: str) -> Optional[PipelineFeedback]:
        """Find feedback for a specific delta."""
        return self.db.query(PipelineFeedback).filter(
            PipelineFeedback.delta_id == delta_id
        ).first()
    
    def find_by_strategy(
        self, 
        strategy: str, 
        limit: int = 100
    ) -> List[PipelineFeedback]:
        """Find feedback entries for a specific strategy."""
        return self.db.query(PipelineFeedback).filter(
            PipelineFeedback.strategy == strategy
        ).order_by(desc(PipelineFeedback.created_at)).limit(limit).all()
    
    def get_unused_for_training(
        self, 
        min_count: int = 10
    ) -> List[PipelineFeedback]:
        """Get feedback entries not yet used for training."""
        return self.db.query(PipelineFeedback).filter(
            PipelineFeedback.used_for_training == False,
            PipelineFeedback.actual_cost.isnot(None)  # Only completed feedback
        ).order_by(PipelineFeedback.created_at).all()
    
    def mark_as_used_for_training(
        self, 
        feedback_ids: List[str],
        batch_id: str
    ) -> int:
        """Mark feedback entries as used for training."""
        result = self.db.query(PipelineFeedback).filter(
            PipelineFeedback.id.in_(feedback_ids)
        ).update(
            {
                PipelineFeedback.used_for_training: True,
                PipelineFeedback.training_batch_id: batch_id
            },
            synchronize_session=False
        )
        self.db.commit()
        return result
    
    def get_recent_feedback(
        self, 
        hours: int = 24,
        limit: int = 100
    ) -> List[PipelineFeedback]:
        """Get feedback from the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return self.db.query(PipelineFeedback).filter(
            PipelineFeedback.created_at >= cutoff
        ).order_by(desc(PipelineFeedback.created_at)).limit(limit).all()
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get statistics about feedback."""
        total = self.db.query(PipelineFeedback).count()
        unused = self.db.query(PipelineFeedback).filter(
            PipelineFeedback.used_for_training == False
        ).count()
        
        # Strategy distribution
        strategies = {}
        for strategy in ["full", "incremental", "partial", "skip"]:
            count = self.db.query(PipelineFeedback).filter(
                PipelineFeedback.strategy == strategy
            ).count()
            strategies[strategy] = count
        
        # Accuracy stats
        correct_count = self.db.query(PipelineFeedback).filter(
            PipelineFeedback.was_correct == True
        ).count()
        
        return {
            "total_feedback": total,
            "unused_for_training": unused,
            "strategies": strategies,
            "correct_decisions": correct_count,
            "accuracy_rate": correct_count / total if total > 0 else 0
        }
    
    def get_training_data(
        self, 
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get feedback formatted as training data.
        
        Returns list of dicts with features and labels.
        """
        feedback_list = self.db.query(PipelineFeedback).filter(
            PipelineFeedback.actual_cost.isnot(None)
        ).order_by(desc(PipelineFeedback.created_at)).limit(limit).all()
        
        training_data = []
        for f in feedback_list:
            training_data.append({
                "features": {
                    "delta_size": f.delta_size or 0,
                    "delta_significance": f.delta_significance or 0,
                    "predicted_cost": f.predicted_cost or 0,
                    "predicted_benefit": f.predicted_benefit or 0,
                },
                "label": f.strategy,
                "outcome": {
                    "was_correct": f.was_correct,
                    "improvement_ratio": f.improvement_ratio
                },
                "feedback_id": f.id
            })
        
        return training_data


class TrainingRecordRepository(BaseRepository[RouterTrainingRecord]):
    """Repository for router training records."""
    
    def __init__(self, db: Session):
        super().__init__(RouterTrainingRecord, db)
    
    def find_by_batch_id(self, batch_id: str) -> Optional[RouterTrainingRecord]:
        """Find a training record by batch ID."""
        return self.db.query(RouterTrainingRecord).filter(
            RouterTrainingRecord.batch_id == batch_id
        ).first()
    
    def get_recent_trainings(
        self, 
        limit: int = 10
    ) -> List[RouterTrainingRecord]:
        """Get recent training records."""
        return self.db.query(RouterTrainingRecord).order_by(
            desc(RouterTrainingRecord.created_at)
        ).limit(limit).all()
    
    def get_latest_successful(self) -> Optional[RouterTrainingRecord]:
        """Get the most recent successful training."""
        return self.db.query(RouterTrainingRecord).filter(
            RouterTrainingRecord.status == "completed"
        ).order_by(desc(RouterTrainingRecord.completed_at)).first()
    
    def get_training_history_stats(self) -> Dict[str, Any]:
        """Get statistics about training history."""
        total = self.db.query(RouterTrainingRecord).count()
        successful = self.db.query(RouterTrainingRecord).filter(
            RouterTrainingRecord.status == "completed"
        ).count()
        
        # Average improvement
        improvements = self.db.query(RouterTrainingRecord.accuracy_improvement).filter(
            RouterTrainingRecord.accuracy_improvement.isnot(None)
        ).all()
        
        avg_improvement = 0
        if improvements:
            avg_improvement = sum(i[0] for i in improvements) / len(improvements)
        
        return {
            "total_trainings": total,
            "successful_trainings": successful,
            "failed_trainings": total - successful,
            "average_accuracy_improvement": avg_improvement
        }
