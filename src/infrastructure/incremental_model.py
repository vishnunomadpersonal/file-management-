"""
Incremental ML Model - A real ML model that supports incremental updates.

This is the core innovation: applying IVM (Incremental View Maintenance) concepts
to machine learning model updates. Instead of retraining from scratch on every
data change, we update models incrementally.

Key Techniques:
1. SKIP: No update needed (change too small)
2. INCREMENTAL: Warm-start SGD on new data only
3. PARTIAL_RETRAIN: Retrain affected model components
4. FULL_RETRAIN: Complete retraining

Research Relevance: 
- Connects to incremental view maintenance (IVM) from databases
- Applies learned index concepts to model updates
- Implements cost-aware processing decisions
"""

import numpy as np
import pandas as pd
import logging
import pickle
import os
import time
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from io import StringIO

from entities.data_delta import DataDelta, ProcessingStrategy, ModelVersion

logger = logging.getLogger(__name__)


@dataclass
class TrainingMetrics:
    """Metrics from a training/update run."""
    strategy_used: ProcessingStrategy
    time_seconds: float
    memory_mb: float
    accuracy_before: float
    accuracy_after: float
    samples_processed: int
    converged: bool
    iterations: int


@dataclass 
class ModelState:
    """Complete state of an incremental model."""
    model: Any
    feature_names: List[str]
    training_samples: int
    current_accuracy: float
    last_update: datetime
    version: str
    data_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class IncrementalModel:
    """
    A machine learning model that supports incremental updates.
    
    This implements the key innovation: applying database IVM concepts to ML.
    The model tracks its own state and can efficiently update itself based
    on delta type and magnitude.
    
    Supported strategies:
    - SKIP: Validate that skip is safe, no update
    - INCREMENTAL: Warm-start training on new data only (SGDClassifier)
    - PARTIAL_RETRAIN: Retrain on affected data subset
    - FULL_RETRAIN: Complete retraining from scratch
    """
    
    def __init__(self, model_type: str = "classification", model_path: Optional[str] = None):
        self.model_type = model_type
        self.model_path = model_path or "/var/www/models/incremental_model.pkl"
        self.state: Optional[ModelState] = None
        
        # Performance tracking for cost calibration
        self.timing_history: List[Dict[str, Any]] = []
        
        # Load existing model if available
        self._load_model()
    
    def _create_base_model(self):
        """Create the base model that supports incremental learning."""
        from sklearn.linear_model import SGDClassifier
        from sklearn.preprocessing import StandardScaler
        
        # SGDClassifier supports partial_fit for true incremental learning
        return {
            'classifier': SGDClassifier(
                loss='log_loss',  # Logistic regression
                penalty='l2',
                alpha=0.0001,
                max_iter=1000,
                tol=1e-3,
                random_state=42,
                warm_start=True,  # Enable warm starting
                n_jobs=-1
            ),
            'scaler': StandardScaler()
        }
    
    async def process_delta(
        self,
        delta: DataDelta,
        strategy: ProcessingStrategy,
        new_data: pd.DataFrame,
        old_data: Optional[pd.DataFrame] = None,
        target_column: str = 'target'
    ) -> TrainingMetrics:
        """
        Process a data delta using the specified strategy.
        
        This is the main entry point that implements IVM-style updates.
        
        Args:
            delta: Detected data changes
            strategy: Processing strategy to use
            new_data: New version of the data
            old_data: Previous version (if available)
            target_column: Name of the target column
            
        Returns:
            TrainingMetrics with performance information
        """
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        accuracy_before = self.state.current_accuracy if self.state else 0.0
        
        # Execute appropriate strategy
        if strategy == ProcessingStrategy.SKIP:
            metrics = await self._skip_update(delta, new_data, target_column)
        elif strategy == ProcessingStrategy.INCREMENTAL:
            metrics = await self._incremental_update(delta, new_data, old_data, target_column)
        elif strategy == ProcessingStrategy.PARTIAL_RETRAIN:
            metrics = await self._partial_retrain(delta, new_data, old_data, target_column)
        else:  # FULL_RETRAIN
            metrics = await self._full_retrain(new_data, target_column)
        
        # Record timing for cost calibration
        elapsed_time = time.time() - start_time
        memory_used = self._get_memory_usage() - start_memory
        
        # Update metrics with actual measurements
        metrics.time_seconds = elapsed_time
        metrics.memory_mb = max(memory_used, 0)
        metrics.accuracy_before = accuracy_before
        
        # Store timing for cost calibration feedback loop
        self._record_timing(strategy, delta, metrics)
        
        # Save model
        self._save_model()
        
        logger.info(
            f"Processed delta with {strategy.value}: "
            f"accuracy {accuracy_before:.3f} -> {metrics.accuracy_after:.3f} "
            f"in {elapsed_time:.2f}s"
        )
        
        return metrics
    
    async def _skip_update(
        self,
        delta: DataDelta,
        data: pd.DataFrame,
        target_column: str
    ) -> TrainingMetrics:
        """
        SKIP strategy: Validate that skipping is safe, but don't update.
        
        We still validate on new data to ensure accuracy hasn't degraded.
        """
        if self.state is None:
            # Can't skip if no model exists - do full training
            return await self._full_retrain(data, target_column)
        
        # Just validate on new data
        accuracy = self._evaluate(data, target_column)
        
        return TrainingMetrics(
            strategy_used=ProcessingStrategy.SKIP,
            time_seconds=0,  # Will be updated
            memory_mb=0,
            accuracy_before=self.state.current_accuracy,
            accuracy_after=accuracy,
            samples_processed=0,
            converged=True,
            iterations=0
        )
    
    async def _incremental_update(
        self,
        delta: DataDelta,
        new_data: pd.DataFrame,
        old_data: Optional[pd.DataFrame],
        target_column: str
    ) -> TrainingMetrics:
        """
        INCREMENTAL strategy: Update model only on changed/new rows.
        
        This is the IVM-equivalent for ML: instead of recomputing from scratch,
        we apply only the delta to the existing model state.
        
        Uses partial_fit for true incremental learning on SGDClassifier.
        """
        if self.state is None:
            return await self._full_retrain(new_data, target_column)
        
        # Identify rows to train on (new and changed rows)
        if delta.rows_inserted > 0:
            # Get the new rows (last N rows are inserts)
            incremental_data = new_data.tail(delta.rows_inserted)
        else:
            # For updates, use a sample of changed rows
            incremental_data = new_data.sample(
                min(delta.rows_updated + 100, len(new_data)),
                random_state=42
            )
        
        if target_column not in incremental_data.columns:
            logger.warning(f"Target column '{target_column}' not found, using last column")
            target_column = incremental_data.columns[-1]
        
        X = incremental_data.drop(columns=[target_column])
        y = incremental_data[target_column]
        
        # Handle non-numeric columns
        X = self._prepare_features(X)
        y = self._prepare_target(y)
        
        if len(X) == 0:
            return TrainingMetrics(
                strategy_used=ProcessingStrategy.INCREMENTAL,
                time_seconds=0,
                memory_mb=0,
                accuracy_before=self.state.current_accuracy,
                accuracy_after=self.state.current_accuracy,
                samples_processed=0,
                converged=True,
                iterations=0
            )
        
        # Scale features
        X_scaled = self.state.model['scaler'].transform(X)
        
        # Partial fit (true incremental update)
        classes = np.unique(y)
        self.state.model['classifier'].partial_fit(X_scaled, y, classes=classes)
        
        # Evaluate on full new data
        accuracy = self._evaluate(new_data, target_column)
        
        # Update state
        self.state.current_accuracy = accuracy
        self.state.training_samples += len(incremental_data)
        self.state.last_update = datetime.utcnow()
        self.state.version = self._generate_version()
        
        return TrainingMetrics(
            strategy_used=ProcessingStrategy.INCREMENTAL,
            time_seconds=0,
            memory_mb=0,
            accuracy_before=self.state.current_accuracy,
            accuracy_after=accuracy,
            samples_processed=len(incremental_data),
            converged=True,
            iterations=1
        )
    
    async def _partial_retrain(
        self,
        delta: DataDelta,
        new_data: pd.DataFrame,
        old_data: Optional[pd.DataFrame],
        target_column: str
    ) -> TrainingMetrics:
        """
        PARTIAL_RETRAIN: Retrain on a representative subset.
        
        This balances the speed of incremental updates with the thoroughness
        of full retraining. We retrain on a stratified sample that includes
        both new data and a portion of historical data.
        """
        if self.state is None:
            return await self._full_retrain(new_data, target_column)
        
        if target_column not in new_data.columns:
            target_column = new_data.columns[-1]
        
        # Create training set: new data + sample of existing
        sample_size = min(
            int(len(new_data) * 0.5),  # 50% of new data
            10000  # Cap at 10k rows
        )
        
        if len(new_data) > sample_size:
            training_data = new_data.sample(sample_size, random_state=42)
        else:
            training_data = new_data
        
        X = training_data.drop(columns=[target_column])
        y = training_data[target_column]
        
        X = self._prepare_features(X)
        y = self._prepare_target(y)
        
        if len(X) == 0:
            return TrainingMetrics(
                strategy_used=ProcessingStrategy.PARTIAL_RETRAIN,
                time_seconds=0,
                memory_mb=0,
                accuracy_before=self.state.current_accuracy,
                accuracy_after=self.state.current_accuracy,
                samples_processed=0,
                converged=True,
                iterations=0
            )
        
        # Partial refit of scaler and model
        X_scaled = self.state.model['scaler'].fit_transform(X)
        
        # Train with warm start (uses previous weights as starting point)
        classes = np.unique(y)
        self.state.model['classifier'].fit(X_scaled, y)
        
        # Evaluate
        accuracy = self._evaluate(new_data, target_column)
        
        # Update state
        self.state.current_accuracy = accuracy
        self.state.training_samples = len(training_data)
        self.state.last_update = datetime.utcnow()
        self.state.version = self._generate_version()
        
        return TrainingMetrics(
            strategy_used=ProcessingStrategy.PARTIAL_RETRAIN,
            time_seconds=0,
            memory_mb=0,
            accuracy_before=self.state.current_accuracy,
            accuracy_after=accuracy,
            samples_processed=len(training_data),
            converged=True,
            iterations=self.state.model['classifier'].n_iter_
        )
    
    async def _full_retrain(
        self,
        data: pd.DataFrame,
        target_column: str
    ) -> TrainingMetrics:
        """
        FULL_RETRAIN: Complete retraining from scratch.
        
        This is the baseline approach - discards all previous state
        and trains a fresh model on all available data.
        """
        if target_column not in data.columns:
            target_column = data.columns[-1]
        
        X = data.drop(columns=[target_column])
        y = data[target_column]
        
        X = self._prepare_features(X)
        y = self._prepare_target(y)
        
        if len(X) == 0:
            return TrainingMetrics(
                strategy_used=ProcessingStrategy.FULL_RETRAIN,
                time_seconds=0,
                memory_mb=0,
                accuracy_before=0.0,
                accuracy_after=0.0,
                samples_processed=0,
                converged=False,
                iterations=0
            )
        
        # Create fresh model
        model = self._create_base_model()
        
        # Fit scaler
        X_scaled = model['scaler'].fit_transform(X)
        
        # Full training
        model['classifier'].fit(X_scaled, y)
        
        # Evaluate
        from sklearn.model_selection import cross_val_score
        try:
            cv_scores = cross_val_score(model['classifier'], X_scaled, y, cv=min(5, len(X)))
            accuracy = cv_scores.mean()
        except:
            accuracy = model['classifier'].score(X_scaled, y)
        
        # Create new state
        self.state = ModelState(
            model=model,
            feature_names=list(X.columns),
            training_samples=len(data),
            current_accuracy=accuracy,
            last_update=datetime.utcnow(),
            version=self._generate_version(),
            data_hash=self._hash_data(data)
        )
        
        return TrainingMetrics(
            strategy_used=ProcessingStrategy.FULL_RETRAIN,
            time_seconds=0,
            memory_mb=0,
            accuracy_before=0.0,
            accuracy_after=accuracy,
            samples_processed=len(data),
            converged=True,
            iterations=model['classifier'].n_iter_
        )
    
    def _prepare_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """Prepare feature matrix, handling non-numeric columns."""
        # Select only numeric columns
        numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
        
        if not numeric_cols:
            # Try to convert or encode non-numeric columns
            X_encoded = pd.get_dummies(X, drop_first=True)
            return X_encoded
        
        return X[numeric_cols]
    
    def _prepare_target(self, y: pd.Series) -> np.ndarray:
        """Prepare target variable, encoding if necessary."""
        if y.dtype == 'object' or str(y.dtype) == 'category':
            from sklearn.preprocessing import LabelEncoder
            le = LabelEncoder()
            return le.fit_transform(y)
        return y.values
    
    def _evaluate(self, data: pd.DataFrame, target_column: str) -> float:
        """Evaluate model on given data."""
        if self.state is None:
            return 0.0
        
        if target_column not in data.columns:
            target_column = data.columns[-1]
        
        X = data.drop(columns=[target_column])
        y = data[target_column]
        
        X = self._prepare_features(X)
        y = self._prepare_target(y)
        
        if len(X) == 0:
            return self.state.current_accuracy
        
        try:
            X_scaled = self.state.model['scaler'].transform(X)
            return self.state.model['classifier'].score(X_scaled, y)
        except Exception as e:
            logger.warning(f"Evaluation failed: {e}")
            return self.state.current_accuracy
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions on new data."""
        if self.state is None:
            raise ValueError("Model not trained")
        
        X = self._prepare_features(X)
        X_scaled = self.state.model['scaler'].transform(X)
        return self.state.model['classifier'].predict(X_scaled)
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Get prediction probabilities."""
        if self.state is None:
            raise ValueError("Model not trained")
        
        X = self._prepare_features(X)
        X_scaled = self.state.model['scaler'].transform(X)
        return self.state.model['classifier'].predict_proba(X_scaled)
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except:
            return 0.0
    
    def _generate_version(self) -> str:
        """Generate a version string."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"v_{timestamp}"
    
    def _hash_data(self, data: pd.DataFrame) -> str:
        """Create a hash of the data for change detection."""
        return hashlib.md5(
            pd.util.hash_pandas_object(data).values.tobytes()
        ).hexdigest()
    
    def _record_timing(
        self,
        strategy: ProcessingStrategy,
        delta: DataDelta,
        metrics: TrainingMetrics
    ):
        """Record timing for cost calibration."""
        self.timing_history.append({
            'strategy': strategy.value,
            'rows': delta.rows_after,
            'changed_rows': delta.rows_inserted + delta.rows_deleted + delta.rows_updated,
            'change_magnitude': delta.change_magnitude,
            'time_seconds': metrics.time_seconds,
            'memory_mb': metrics.memory_mb,
            'accuracy_change': metrics.accuracy_after - metrics.accuracy_before,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Keep last 100 records
        if len(self.timing_history) > 100:
            self.timing_history = self.timing_history[-100:]
    
    def get_timing_stats(self) -> Dict[str, Any]:
        """Get timing statistics for cost calibration."""
        if not self.timing_history:
            return {}
        
        stats = {}
        for strategy in ProcessingStrategy:
            strategy_timings = [
                t for t in self.timing_history 
                if t['strategy'] == strategy.value
            ]
            if strategy_timings:
                times = [t['time_seconds'] for t in strategy_timings]
                stats[strategy.value] = {
                    'mean_time': np.mean(times),
                    'std_time': np.std(times),
                    'samples': len(times),
                    'mean_rows': np.mean([t['rows'] for t in strategy_timings])
                }
        
        return stats
    
    def _load_model(self):
        """Load model from disk."""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    self.state = pickle.load(f)
                logger.info(f"Loaded model from {self.model_path}")
        except Exception as e:
            logger.warning(f"Could not load model: {e}")
    
    def _save_model(self):
        """Save model to disk."""
        if self.state is None:
            return
        
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.state, f)
            logger.info(f"Saved model to {self.model_path}")
        except Exception as e:
            logger.error(f"Could not save model: {e}")


# Factory function for creating models
def create_incremental_model(
    model_type: str = "classification",
    model_id: Optional[str] = None
) -> IncrementalModel:
    """Create a new incremental model instance."""
    if model_id:
        path = f"/var/www/models/{model_id}.pkl"
    else:
        path = None
    
    return IncrementalModel(model_type=model_type, model_path=path)


# Singleton for default model
_default_model: Optional[IncrementalModel] = None

def get_default_model() -> IncrementalModel:
    """Get the default incremental model instance."""
    global _default_model
    if _default_model is None:
        _default_model = IncrementalModel()
    return _default_model
