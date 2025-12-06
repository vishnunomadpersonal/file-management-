"""
Persistent Feedback Loop Service - Database-Backed Continuous Learning.

Replaces the in-memory feedback storage with database persistence.
Enables continuous improvement of the learned router through real feedback.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from src.entities.pipeline_feedback import PipelineFeedback, RouterTrainingRecord
from src.repositories.feedback_repository import FeedbackRepository, TrainingRecordRepository
from src.infrastructure.model_versioning import get_router_model_manager

logger = logging.getLogger(__name__)


class PersistentFeedbackService:
    """
    Manages feedback collection and model retraining with database persistence.
    
    This service:
    1. Records predictions before execution
    2. Updates with actual outcomes after execution
    3. Triggers retraining when enough feedback accumulates
    4. Integrates with model versioning for rollback capability
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.feedback_repo = FeedbackRepository(db)
        self.training_repo = TrainingRecordRepository(db)
        
        # Configuration
        self.min_samples_for_training = 50  # Minimum feedback before retraining
        self.training_batch_size = 100  # Max samples per training batch
    
    def record_prediction(
        self,
        delta_id: str,
        strategy: str,
        predicted_cost: float,
        predicted_benefit: float,
        delta_size: int,
        delta_significance: float,
        affected_tables: Optional[List[str]] = None,
        predicted_accuracy: Optional[float] = None
    ) -> str:
        """
        Record a prediction before execution.
        
        Call this when a routing decision is made, before executing the strategy.
        
        Returns:
            Feedback ID for later updating with actual outcomes.
        """
        feedback = PipelineFeedback(
            id=str(uuid.uuid4()),
            delta_id=delta_id,
            strategy=strategy,
            predicted_cost=predicted_cost,
            predicted_benefit=predicted_benefit,
            predicted_accuracy=predicted_accuracy,
            delta_size=delta_size,
            delta_significance=delta_significance,
            affected_tables=affected_tables or []
        )
        
        self.feedback_repo.add(feedback)
        
        logger.info(f"Recorded prediction for delta {delta_id}: {strategy}")
        
        return feedback.id
    
    def record_outcome(
        self,
        feedback_id: str,
        actual_cost: float,
        actual_benefit: float,
        actual_accuracy: Optional[float] = None,
        user_rating: Optional[int] = None,
        user_comment: Optional[str] = None
    ) -> Optional[PipelineFeedback]:
        """
        Update feedback with actual outcomes after execution.
        
        Call this after the strategy has been executed with real results.
        """
        feedback = self.feedback_repo.find_by_id(feedback_id)
        
        if not feedback:
            logger.warning(f"Feedback {feedback_id} not found")
            return None
        
        # Update with actual outcomes
        feedback.actual_cost = actual_cost
        feedback.actual_benefit = actual_benefit
        feedback.actual_accuracy = actual_accuracy
        feedback.user_rating = user_rating
        feedback.user_comment = user_comment
        
        # Calculate derived metrics
        if feedback.predicted_benefit and actual_benefit:
            feedback.improvement_ratio = actual_benefit / feedback.predicted_benefit
        
        # Determine if decision was correct
        # A decision is "correct" if actual benefit > actual cost
        # and the ratio of actual to predicted is reasonable (> 0.7)
        if actual_benefit > actual_cost:
            if feedback.improvement_ratio and feedback.improvement_ratio > 0.7:
                feedback.was_correct = True
            elif feedback.improvement_ratio and feedback.improvement_ratio <= 0.7:
                feedback.was_correct = False
            else:
                feedback.was_correct = True  # Default if no improvement ratio
        else:
            feedback.was_correct = False
        
        self.feedback_repo.update(feedback)
        
        logger.info(
            f"Recorded outcome for {feedback_id}: "
            f"cost={actual_cost}, benefit={actual_benefit}, "
            f"correct={feedback.was_correct}"
        )
        
        # Check if we should trigger retraining
        self._check_training_trigger()
        
        return feedback
    
    def record_complete_feedback(
        self,
        delta_id: str,
        strategy: str,
        predicted_cost: float,
        actual_cost: float,
        predicted_benefit: float,
        actual_benefit: float,
        delta_size: int,
        delta_significance: float,
        affected_tables: Optional[List[str]] = None,
        predicted_accuracy: Optional[float] = None,
        actual_accuracy: Optional[float] = None
    ) -> str:
        """
        Record complete feedback in one call (prediction + outcome).
        
        Use this when you have both prediction and outcome available together.
        """
        feedback_id = self.record_prediction(
            delta_id=delta_id,
            strategy=strategy,
            predicted_cost=predicted_cost,
            predicted_benefit=predicted_benefit,
            delta_size=delta_size,
            delta_significance=delta_significance,
            affected_tables=affected_tables,
            predicted_accuracy=predicted_accuracy
        )
        
        self.record_outcome(
            feedback_id=feedback_id,
            actual_cost=actual_cost,
            actual_benefit=actual_benefit,
            actual_accuracy=actual_accuracy
        )
        
        return feedback_id
    
    def _check_training_trigger(self):
        """Check if we have enough feedback to trigger retraining."""
        unused_feedback = self.feedback_repo.get_unused_for_training()
        
        if len(unused_feedback) >= self.min_samples_for_training:
            logger.info(
                f"Training threshold reached: {len(unused_feedback)} samples. "
                f"Consider calling train_router()"
            )
            # Note: We don't auto-trigger training here to keep it controlled
            # The orchestrator or scheduler should call train_router() explicitly
    
    def get_training_readiness(self) -> Dict[str, Any]:
        """Check if we're ready to train and how much data is available."""
        unused_feedback = self.feedback_repo.get_unused_for_training()
        stats = self.feedback_repo.get_feedback_stats()
        
        return {
            "ready_for_training": len(unused_feedback) >= self.min_samples_for_training,
            "available_samples": len(unused_feedback),
            "min_samples_required": self.min_samples_for_training,
            "total_feedback": stats["total_feedback"],
            "accuracy_rate": stats["accuracy_rate"],
            "strategy_distribution": stats["strategies"]
        }
    
    def train_router(
        self,
        force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Train the router model with accumulated feedback.
        
        Args:
            force: Train even if we don't have enough samples
            
        Returns:
            Training results, or None if training was skipped
        """
        unused_feedback = self.feedback_repo.get_unused_for_training()
        
        if len(unused_feedback) < self.min_samples_for_training and not force:
            logger.info(
                f"Not enough feedback for training: "
                f"{len(unused_feedback)} < {self.min_samples_for_training}"
            )
            return None
        
        # Limit batch size
        training_feedback = unused_feedback[:self.training_batch_size]
        
        # Create training record
        batch_id = str(uuid.uuid4())
        training_record = RouterTrainingRecord(
            batch_id=batch_id,
            samples_count=len(training_feedback),
            feedback_ids=[f.id for f in training_feedback],
            started_at=datetime.utcnow(),
            status="in_progress"
        )
        self.training_repo.add(training_record)
        
        try:
            # Prepare training data
            X, y = self._prepare_training_data(training_feedback)
            
            # Get current accuracy (before training)
            current_accuracy = self._get_current_router_accuracy()
            training_record.previous_accuracy = current_accuracy
            
            # Import and train the router
            from src.ml_pipeline.learned_router import learned_router
            
            import time
            start_time = time.time()
            
            # Train the router
            training_result = learned_router.train(X, y)
            
            training_time = time.time() - start_time
            
            # Save model version
            model_manager = get_router_model_manager()
            model_version = model_manager.save_version(
                model=learned_router.model,
                training_strategy="feedback_retrain",
                samples_used=len(training_feedback),
                accuracy=training_result.get("accuracy"),
                training_time_seconds=training_time,
                custom_metrics={
                    "batch_id": batch_id,
                    "previous_accuracy": current_accuracy
                }
            )
            
            # Update training record
            training_record.model_version = model_version.version
            training_record.training_accuracy = training_result.get("accuracy")
            training_record.validation_accuracy = training_result.get("validation_accuracy")
            training_record.training_time_seconds = training_time
            training_record.accuracy_improvement = (
                (training_result.get("accuracy", 0) - (current_accuracy or 0))
                if current_accuracy else None
            )
            training_record.status = "completed"
            training_record.completed_at = datetime.utcnow()
            
            # Mark feedback as used
            self.feedback_repo.mark_as_used_for_training(
                [f.id for f in training_feedback],
                batch_id
            )
            
            self.training_repo.update(training_record)
            
            logger.info(
                f"Router training completed: batch={batch_id}, "
                f"samples={len(training_feedback)}, "
                f"accuracy={training_result.get('accuracy')}"
            )
            
            return {
                "batch_id": batch_id,
                "samples_used": len(training_feedback),
                "model_version": model_version.version,
                "training_accuracy": training_result.get("accuracy"),
                "previous_accuracy": current_accuracy,
                "accuracy_improvement": training_record.accuracy_improvement,
                "training_time_seconds": training_time
            }
            
        except Exception as e:
            training_record.status = "failed"
            training_record.error_message = str(e)
            training_record.completed_at = datetime.utcnow()
            self.training_repo.update(training_record)
            
            logger.error(f"Router training failed: {e}")
            raise
    
    def _prepare_training_data(
        self, 
        feedback_list: List[PipelineFeedback]
    ) -> tuple:
        """Prepare training data from feedback."""
        import numpy as np
        
        X = []
        y = []
        
        strategy_map = {
            "full": 0,
            "incremental": 1,
            "partial": 2,
            "skip": 3
        }
        
        for f in feedback_list:
            features = [
                f.delta_size or 0,
                f.delta_significance or 0,
                1 if f.was_correct else 0,
                f.improvement_ratio or 1.0
            ]
            X.append(features)
            y.append(strategy_map.get(f.strategy, 0))
        
        return np.array(X), np.array(y)
    
    def _get_current_router_accuracy(self) -> Optional[float]:
        """Get the current router model's accuracy."""
        try:
            from src.ml_pipeline.learned_router import learned_router
            if hasattr(learned_router, 'model') and learned_router.model:
                return learned_router.model_accuracy
        except:
            pass
        return None
    
    def get_feedback_history(
        self, 
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent feedback history."""
        feedback_list = self.feedback_repo.get_recent_feedback(hours, limit)
        
        return [
            {
                "id": f.id,
                "delta_id": f.delta_id,
                "strategy": f.strategy,
                "predicted_cost": f.predicted_cost,
                "actual_cost": f.actual_cost,
                "predicted_benefit": f.predicted_benefit,
                "actual_benefit": f.actual_benefit,
                "was_correct": f.was_correct,
                "improvement_ratio": f.improvement_ratio,
                "user_rating": f.user_rating,
                "used_for_training": f.used_for_training,
                "created_at": f.created_at.isoformat() if f.created_at else None
            }
            for f in feedback_list
        ]
    
    def get_training_history(
        self, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get training history."""
        records = self.training_repo.get_recent_trainings(limit)
        
        return [
            {
                "batch_id": r.batch_id,
                "samples_count": r.samples_count,
                "model_version": r.model_version,
                "training_accuracy": r.training_accuracy,
                "previous_accuracy": r.previous_accuracy,
                "accuracy_improvement": r.accuracy_improvement,
                "training_time_seconds": r.training_time_seconds,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in records
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive feedback and training statistics."""
        feedback_stats = self.feedback_repo.get_feedback_stats()
        training_stats = self.training_repo.get_training_history_stats()
        readiness = self.get_training_readiness()
        
        return {
            "feedback": feedback_stats,
            "training": training_stats,
            "readiness": readiness
        }


# Factory function
def get_feedback_service(db: Session) -> PersistentFeedbackService:
    """Get a feedback service instance."""
    return PersistentFeedbackService(db)
