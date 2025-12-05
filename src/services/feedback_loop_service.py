"""
Feedback Loop Service - Continuous improvement through outcome tracking.

This service implements the critical feedback loop that makes the system
learn and improve over time:

1. RECORD: Store actual outcomes from pipeline executions
2. ANALYZE: Detect patterns in estimation accuracy
3. RETRAIN: Periodically retrain router with real outcomes
4. ADAPT: Adjust cost models based on actual measurements

Research Relevance:
- Self-tuning database systems
- Adaptive query optimization
- Online learning for systems
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import func

from entities.data_delta import DataDelta, ProcessingStrategy, PipelineRun, ModelVersion
from repositories.delta_repository import DeltaRepo, PipelineRunRepo, ModelVersionRepo
from infrastructure.learned_router import learned_router
from infrastructure.cost_optimizer import cost_optimizer
from infrastructure.incremental_model import get_default_model

logger = logging.getLogger(__name__)


@dataclass
class OutcomeRecord:
    """A recorded outcome from a pipeline execution."""
    delta_id: str
    strategy_used: ProcessingStrategy
    
    # Estimated values
    estimated_time: float
    estimated_memory: float
    estimated_accuracy: float
    
    # Actual values
    actual_time: float
    actual_memory: float
    actual_accuracy: float
    accuracy_change: float
    
    # Metadata
    recorded_at: datetime
    
    @property
    def time_error(self) -> float:
        """Error in time estimation (positive = underestimate)."""
        return (self.actual_time - self.estimated_time) / max(self.estimated_time, 0.1)
    
    @property
    def was_good_decision(self) -> bool:
        """Whether the routing decision was optimal in hindsight."""
        # Good if accuracy improved or stayed stable
        return self.accuracy_change >= -0.02


class FeedbackLoopService:
    """
    Service for recording outcomes and triggering adaptive improvements.
    
    The feedback loop is the key to making this system "real" - it learns
    from actual outcomes rather than relying on fixed rules.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.delta_repo = DeltaRepo(db)
        self.run_repo = PipelineRunRepo(db)
        self.model_repo = ModelVersionRepo(db)
        
        # Thresholds for triggering retraining
        self.min_samples_for_retrain = 50
        self.max_error_before_recalibrate = 0.3  # 30% average error
        self.retrain_interval_hours = 24
        
        # In-memory outcome buffer (for fast access)
        self.outcome_buffer: List[OutcomeRecord] = []
    
    async def record_outcome(
        self,
        delta: DataDelta,
        strategy: ProcessingStrategy,
        estimated_time: float,
        estimated_memory: float,
        estimated_accuracy: float,
        actual_time: float,
        actual_memory: float,
        actual_accuracy: float,
        accuracy_before: float
    ) -> OutcomeRecord:
        """
        Record an outcome from a pipeline execution.
        
        This is called after every pipeline run to build the feedback dataset.
        """
        outcome = OutcomeRecord(
            delta_id=delta.id,
            strategy_used=strategy,
            estimated_time=estimated_time,
            estimated_memory=estimated_memory,
            estimated_accuracy=estimated_accuracy,
            actual_time=actual_time,
            actual_memory=actual_memory,
            actual_accuracy=actual_accuracy,
            accuracy_change=actual_accuracy - accuracy_before,
            recorded_at=datetime.utcnow()
        )
        
        # Add to buffer
        self.outcome_buffer.append(outcome)
        
        # Keep buffer bounded
        if len(self.outcome_buffer) > 1000:
            self.outcome_buffer = self.outcome_buffer[-1000:]
        
        # Update delta record in database
        delta.processing_time_ms = int(actual_time * 1000)
        delta.actual_cost = actual_time * 0.001  # Simple cost model
        
        # Check if we should trigger auto-improvements
        await self._check_auto_improvements()
        
        logger.info(
            f"Recorded outcome for delta {delta.id[:8]}: "
            f"time_error={outcome.time_error:.1%}, "
            f"accuracy_change={outcome.accuracy_change:+.3f}"
        )
        
        return outcome
    
    async def _check_auto_improvements(self):
        """Check if we should trigger automatic improvements."""
        
        # Check if we have enough recent outcomes
        recent_outcomes = [
            o for o in self.outcome_buffer
            if (datetime.utcnow() - o.recorded_at) < timedelta(hours=self.retrain_interval_hours)
        ]
        
        if len(recent_outcomes) < 10:
            return
        
        # Check average estimation error
        avg_time_error = abs(np.mean([o.time_error for o in recent_outcomes]))
        
        if avg_time_error > self.max_error_before_recalibrate:
            logger.warning(
                f"High estimation error detected ({avg_time_error:.1%}), "
                f"triggering cost recalibration"
            )
            # Trigger recalibration (async)
            await self._auto_recalibrate_costs()
        
        # Check if we should retrain router
        if len(recent_outcomes) >= self.min_samples_for_retrain:
            bad_decisions = [o for o in recent_outcomes if not o.was_good_decision]
            bad_rate = len(bad_decisions) / len(recent_outcomes)
            
            if bad_rate > 0.2:  # >20% bad decisions
                logger.warning(
                    f"High bad decision rate ({bad_rate:.1%}), "
                    f"triggering router retraining"
                )
                await self._auto_retrain_router()
    
    async def _auto_recalibrate_costs(self):
        """Automatically recalibrate cost models based on recent outcomes."""
        
        # Group outcomes by strategy
        by_strategy: Dict[ProcessingStrategy, List[OutcomeRecord]] = {}
        for outcome in self.outcome_buffer:
            if outcome.strategy_used not in by_strategy:
                by_strategy[outcome.strategy_used] = []
            by_strategy[outcome.strategy_used].append(outcome)
        
        # Update cost models for each strategy
        for strategy, outcomes in by_strategy.items():
            if len(outcomes) < 5:
                continue
            
            # Calculate average actual times
            avg_actual_time = np.mean([o.actual_time for o in outcomes])
            avg_estimated_time = np.mean([o.estimated_time for o in outcomes])
            
            # Adjust base coefficient
            if avg_estimated_time > 0:
                adjustment = avg_actual_time / avg_estimated_time
                current_base = cost_optimizer.time_coefficients[strategy]['base']
                
                # Smooth adjustment
                new_base = current_base * (0.7 + 0.3 * adjustment)
                cost_optimizer.time_coefficients[strategy]['base'] = new_base
                
                logger.info(
                    f"Auto-calibrated {strategy.value}: "
                    f"base {current_base:.2f} -> {new_base:.2f}"
                )
    
    async def _auto_retrain_router(self):
        """Automatically retrain the router based on recorded outcomes."""
        
        if len(self.outcome_buffer) < self.min_samples_for_retrain:
            logger.info("Not enough samples for router retraining")
            return
        
        # Get deltas from database
        delta_ids = [o.delta_id for o in self.outcome_buffer[-200:]]
        deltas = [self.delta_repo.get_delta(did) for did in delta_ids if did]
        deltas = [d for d in deltas if d is not None]
        
        if len(deltas) < 50:
            logger.info("Not enough valid deltas for router retraining")
            return
        
        # Build outcomes
        outcomes = []
        for outcome in self.outcome_buffer[-200:]:
            # Determine optimal strategy based on actual results
            if outcome.was_good_decision:
                optimal = outcome.strategy_used
            else:
                # If accuracy dropped, should have used more aggressive strategy
                if outcome.accuracy_change < -0.05:
                    optimal = ProcessingStrategy.FULL_RETRAIN
                elif outcome.accuracy_change < -0.02:
                    optimal = ProcessingStrategy.PARTIAL_RETRAIN
                else:
                    optimal = outcome.strategy_used
            
            outcomes.append({
                'strategy_used': optimal.value,
                'accuracy_drop': -outcome.accuracy_change,
                'actual_cost': outcome.actual_time
            })
        
        # Train router
        try:
            metrics = await learned_router.train(deltas[:len(outcomes)], outcomes)
            logger.info(f"Auto-retrained router: accuracy={metrics.get('cv_accuracy_mean', 0):.3f}")
        except Exception as e:
            logger.error(f"Auto-retrain failed: {e}")
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get statistics about the feedback loop."""
        
        if not self.outcome_buffer:
            return {'message': 'No outcomes recorded yet'}
        
        recent = [
            o for o in self.outcome_buffer
            if (datetime.utcnow() - o.recorded_at) < timedelta(hours=24)
        ]
        
        if not recent:
            return {'message': 'No recent outcomes'}
        
        # Calculate statistics
        time_errors = [o.time_error for o in recent]
        accuracy_changes = [o.accuracy_change for o in recent]
        good_decisions = [o for o in recent if o.was_good_decision]
        
        # Strategy distribution
        strategy_counts = {}
        for o in recent:
            s = o.strategy_used.value
            strategy_counts[s] = strategy_counts.get(s, 0) + 1
        
        return {
            'total_outcomes': len(self.outcome_buffer),
            'recent_outcomes_24h': len(recent),
            'average_time_error': float(np.mean(time_errors)),
            'average_accuracy_change': float(np.mean(accuracy_changes)),
            'good_decision_rate': len(good_decisions) / len(recent),
            'strategy_distribution': strategy_counts,
            'last_outcome': recent[-1].recorded_at.isoformat() if recent else None
        }
    
    async def get_improvement_recommendations(self) -> List[str]:
        """Get recommendations for improving the pipeline."""
        
        recommendations = []
        
        if not self.outcome_buffer:
            recommendations.append("Upload more files to gather training data")
            return recommendations
        
        recent = [
            o for o in self.outcome_buffer
            if (datetime.utcnow() - o.recorded_at) < timedelta(hours=24)
        ]
        
        if len(recent) < 10:
            recommendations.append("Process more files to improve model accuracy")
        
        # Check estimation accuracy
        if recent:
            avg_time_error = abs(np.mean([o.time_error for o in recent]))
            if avg_time_error > 0.3:
                recommendations.append(
                    f"Cost estimates are {avg_time_error:.0%} off - "
                    "consider running /cost/calibrate"
                )
            
            # Check decision quality
            good_rate = len([o for o in recent if o.was_good_decision]) / len(recent)
            if good_rate < 0.8:
                recommendations.append(
                    f"Only {good_rate:.0%} of routing decisions were optimal - "
                    "consider retraining router with /router/train-synthetic"
                )
            
            # Check if using learned router
            if learned_router.model is None:
                recommendations.append(
                    "Router is using rule-based fallback - "
                    "train the ML model with /router/train-synthetic"
                )
        
        # Check model accuracy
        model = get_default_model()
        if model.state:
            if model.state.current_accuracy < 0.7:
                recommendations.append(
                    f"Model accuracy is low ({model.state.current_accuracy:.1%}) - "
                    "consider uploading more diverse training data"
                )
        else:
            recommendations.append(
                "No ML model trained yet - upload a CSV file to start"
            )
        
        if not recommendations:
            recommendations.append("System is performing well! No improvements needed.")
        
        return recommendations


# Factory function
def create_feedback_service(db: Session) -> FeedbackLoopService:
    """Create a feedback loop service instance."""
    return FeedbackLoopService(db)
