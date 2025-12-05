"""
Learned Router - ML-based decision maker for incremental update strategies.

This component uses machine learning to decide the optimal processing strategy
for each detected data delta:
- SKIP: Change too small, no update needed
- INCREMENTAL: Apply incremental update to existing model
- PARTIAL_RETRAIN: Retrain only affected model components
- FULL_RETRAIN: Complete model retraining required

Research relevance: Learned Query Optimization, Adaptive Processing
"""

import numpy as np
import logging
import pickle
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from entities.data_delta import DataDelta, ProcessingStrategy

logger = logging.getLogger(__name__)


@dataclass
class RouterDecision:
    """Represents a routing decision with confidence and reasoning."""
    strategy: ProcessingStrategy
    confidence: float
    reasoning: str
    estimated_cost: float
    estimated_accuracy_impact: float
    feature_importance: Dict[str, float]


class LearnedRouter:
    """
    ML-based router that learns optimal processing strategies from historical data.
    
    Key innovations:
    1. Uses historical delta→outcome pairs to learn decision boundaries
    2. Considers both cost and accuracy impact
    3. Provides interpretable decisions with feature importance
    4. Adapts thresholds based on feedback loop
    
    The router uses a gradient boosting model trained on:
    - Delta features (change magnitude, type, size, etc.)
    - Historical outcomes (accuracy, cost, time)
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or "/var/www/models/learned_router.pkl"
        self.model = None
        self.feature_names = [
            'insert_ratio',
            'delete_ratio', 
            'update_ratio',
            'change_magnitude',
            'entropy_delta',
            'feature_drift_score',
            'columns_added_count',
            'columns_removed_count',
            'columns_modified_count',
            'is_schema_change',
            'rows_before_log',
            'rows_after_log',
            'time_since_last_update_hours'
        ]
        
        # Default thresholds (used before model is trained)
        self.default_thresholds = {
            'skip_magnitude': 0.01,
            'incremental_magnitude': 0.15,
            'partial_magnitude': 0.40,
            'drift_threshold': 0.20,
            'schema_always_full': True
        }
        
        # Strategy cost estimates (relative units)
        self.strategy_costs = {
            ProcessingStrategy.SKIP: 0.0,
            ProcessingStrategy.INCREMENTAL: 1.0,
            ProcessingStrategy.PARTIAL_RETRAIN: 5.0,
            ProcessingStrategy.FULL_RETRAIN: 10.0
        }
        
        # Load model if exists
        self._load_model()
    
    async def route(
        self, 
        delta: DataDelta,
        context: Optional[Dict[str, Any]] = None
    ) -> RouterDecision:
        """
        Make a routing decision for the given delta.
        
        Args:
            delta: The detected data delta
            context: Optional context (model info, deadlines, etc.)
            
        Returns:
            RouterDecision with strategy, confidence, and reasoning
        """
        context = context or {}
        
        # Extract features from delta
        features = self._extract_features(delta, context)
        
        # Use ML model if trained, otherwise rule-based
        if self.model is not None:
            decision = await self._ml_route(features, delta)
        else:
            decision = await self._rule_based_route(features, delta)
        
        logger.info(
            f"Router decision for delta {delta.id[:8]}: "
            f"{decision.strategy.value} (confidence={decision.confidence:.2f})"
        )
        
        return decision
    
    async def _ml_route(
        self, 
        features: np.ndarray, 
        delta: DataDelta
    ) -> RouterDecision:
        """Use trained ML model to make routing decision."""
        try:
            # Get prediction probabilities
            probas = self.model.predict_proba(features.reshape(1, -1))[0]
            predicted_class = self.model.predict(features.reshape(1, -1))[0]
            
            # Map class to strategy
            strategy_map = {
                0: ProcessingStrategy.SKIP,
                1: ProcessingStrategy.INCREMENTAL,
                2: ProcessingStrategy.PARTIAL_RETRAIN,
                3: ProcessingStrategy.FULL_RETRAIN
            }
            
            strategy = strategy_map.get(predicted_class, ProcessingStrategy.FULL_RETRAIN)
            confidence = float(probas[predicted_class])
            
            # Get feature importance
            feature_importance = dict(zip(
                self.feature_names,
                self.model.feature_importances_.tolist()
            ))
            
            # Generate reasoning
            top_features = sorted(
                feature_importance.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
            reasoning = f"ML decision based on: {', '.join([f'{k}={features[i]:.3f}' for i, (k, _) in enumerate(top_features)])}"
            
            return RouterDecision(
                strategy=strategy,
                confidence=confidence,
                reasoning=reasoning,
                estimated_cost=self.strategy_costs[strategy] * delta.rows_after / 1000,
                estimated_accuracy_impact=self._estimate_accuracy_impact(strategy, delta),
                feature_importance=feature_importance
            )
            
        except Exception as e:
            logger.error(f"ML routing failed, falling back to rules: {e}")
            return await self._rule_based_route(features, delta)
    
    async def _rule_based_route(
        self, 
        features: np.ndarray, 
        delta: DataDelta
    ) -> RouterDecision:
        """Rule-based routing when ML model is not available."""
        
        thresholds = self.default_thresholds
        
        # Extract key metrics
        change_magnitude = delta.change_magnitude
        drift_score = delta.feature_drift_score
        is_schema_change = bool(delta.columns_added or delta.columns_removed)
        
        # Decision logic
        reasoning_parts = []
        
        # Rule 1: Schema changes require full retrain
        if is_schema_change and thresholds['schema_always_full']:
            strategy = ProcessingStrategy.FULL_RETRAIN
            confidence = 0.95
            reasoning_parts.append("Schema change detected")
        
        # Rule 2: Very small changes can be skipped
        elif change_magnitude < thresholds['skip_magnitude'] and drift_score < 0.05:
            strategy = ProcessingStrategy.SKIP
            confidence = 0.90
            reasoning_parts.append(f"Change magnitude ({change_magnitude:.3f}) below skip threshold")
        
        # Rule 3: Small changes with low drift → incremental
        elif change_magnitude < thresholds['incremental_magnitude'] and drift_score < thresholds['drift_threshold']:
            strategy = ProcessingStrategy.INCREMENTAL
            confidence = 0.75
            reasoning_parts.append(f"Low change magnitude ({change_magnitude:.3f}) and drift ({drift_score:.3f})")
        
        # Rule 4: Medium changes or moderate drift → partial retrain
        elif change_magnitude < thresholds['partial_magnitude'] and drift_score < thresholds['drift_threshold'] * 2:
            strategy = ProcessingStrategy.PARTIAL_RETRAIN
            confidence = 0.70
            reasoning_parts.append(f"Moderate change magnitude ({change_magnitude:.3f})")
        
        # Rule 5: Large changes or high drift → full retrain
        else:
            strategy = ProcessingStrategy.FULL_RETRAIN
            confidence = 0.85
            reasoning_parts.append(f"High change magnitude ({change_magnitude:.3f}) or drift ({drift_score:.3f})")
        
        return RouterDecision(
            strategy=strategy,
            confidence=confidence,
            reasoning=" | ".join(reasoning_parts),
            estimated_cost=self.strategy_costs[strategy] * delta.rows_after / 1000,
            estimated_accuracy_impact=self._estimate_accuracy_impact(strategy, delta),
            feature_importance={f: 0.0 for f in self.feature_names}  # No feature importance for rules
        )
    
    def _extract_features(
        self, 
        delta: DataDelta, 
        context: Dict[str, Any]
    ) -> np.ndarray:
        """Extract feature vector from delta for ML model."""
        
        rows_before = max(delta.rows_before, 1)
        rows_after = max(delta.rows_after, 1)
        
        features = [
            delta.rows_inserted / rows_after,                    # insert_ratio
            delta.rows_deleted / rows_before,                    # delete_ratio
            delta.rows_updated / rows_before,                    # update_ratio
            delta.change_magnitude,                              # change_magnitude
            delta.entropy_delta,                                 # entropy_delta
            delta.feature_drift_score,                           # feature_drift_score
            len(delta.columns_added or []),                      # columns_added_count
            len(delta.columns_removed or []),                    # columns_removed_count
            len(delta.columns_modified or []),                   # columns_modified_count
            1.0 if (delta.columns_added or delta.columns_removed) else 0.0,  # is_schema_change
            np.log1p(rows_before),                               # rows_before_log
            np.log1p(rows_after),                                # rows_after_log
            context.get('hours_since_last_update', 24.0)         # time_since_last_update_hours
        ]
        
        return np.array(features)
    
    def _estimate_accuracy_impact(
        self, 
        strategy: ProcessingStrategy, 
        delta: DataDelta
    ) -> float:
        """Estimate the impact on model accuracy for given strategy."""
        
        # Higher drift = higher potential accuracy impact if not retrained
        drift_impact = delta.feature_drift_score * 0.5
        magnitude_impact = delta.change_magnitude * 0.3
        
        base_impact = drift_impact + magnitude_impact
        
        # Strategy-based multiplier (how much the strategy mitigates the impact)
        mitigation = {
            ProcessingStrategy.SKIP: 0.0,          # No mitigation, full impact
            ProcessingStrategy.INCREMENTAL: 0.5,  # Partial mitigation
            ProcessingStrategy.PARTIAL_RETRAIN: 0.8,  # Good mitigation
            ProcessingStrategy.FULL_RETRAIN: 1.0   # Full mitigation
        }
        
        # Resulting impact (lower is better)
        mitigated_impact = base_impact * (1 - mitigation[strategy])
        
        return mitigated_impact
    
    async def train(
        self, 
        historical_deltas: List[DataDelta],
        outcomes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Train the router model on historical data.
        
        Args:
            historical_deltas: List of past deltas
            outcomes: List of outcomes with actual strategy used and results
            
        Returns:
            Training metrics
        """
        try:
            from sklearn.ensemble import GradientBoostingClassifier
            from sklearn.model_selection import cross_val_score
            
            # Prepare training data
            X = np.array([self._extract_features(d, {}) for d in historical_deltas])
            
            # Labels: what strategy was optimal based on outcomes
            y = np.array([self._determine_optimal_strategy(o) for o in outcomes])
            
            # Train model
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
            
            # Cross-validation
            cv_scores = cross_val_score(self.model, X, y, cv=5)
            
            # Final fit
            self.model.fit(X, y)
            
            # Save model
            self._save_model()
            
            metrics = {
                'cv_accuracy_mean': float(cv_scores.mean()),
                'cv_accuracy_std': float(cv_scores.std()),
                'n_samples': len(historical_deltas),
                'feature_importance': dict(zip(
                    self.feature_names,
                    self.model.feature_importances_.tolist()
                )),
                'trained_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Router model trained: accuracy={metrics['cv_accuracy_mean']:.3f}")
            return metrics
            
        except ImportError:
            logger.warning("scikit-learn not installed, using rule-based routing")
            return {'error': 'scikit-learn not available'}
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {'error': str(e)}
    
    def _determine_optimal_strategy(self, outcome: Dict[str, Any]) -> int:
        """Determine optimal strategy from outcome data."""
        # Use actual cost and accuracy to determine what would have been optimal
        
        accuracy_drop = outcome.get('accuracy_drop', 0)
        cost = outcome.get('actual_cost', 0)
        used_strategy = outcome.get('strategy_used', 'full')
        
        # If skip resulted in < 2% accuracy drop, skip was optimal
        if used_strategy == 'skip' and accuracy_drop < 0.02:
            return 0
        # If incremental gave good results, it was optimal
        elif used_strategy == 'incremental' and accuracy_drop < 0.05:
            return 1
        # Partial retrain for moderate cases
        elif used_strategy == 'partial' and accuracy_drop < 0.03:
            return 2
        # Otherwise full retrain
        else:
            return 3
    
    def _load_model(self):
        """Load trained model from disk if exists."""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                logger.info(f"Loaded router model from {self.model_path}")
        except Exception as e:
            logger.warning(f"Could not load router model: {e}")
            self.model = None
    
    def _save_model(self):
        """Save trained model to disk."""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            logger.info(f"Saved router model to {self.model_path}")
        except Exception as e:
            logger.error(f"Could not save router model: {e}")


# Singleton instance
learned_router = LearnedRouter()
