"""
Unit Tests for Incremental ML Pipeline Components.

Tests the core components of the IVM-inspired ML pipeline:
- Change Detection Service
- Learned Router
- Cost Optimizer
- Incremental Model
- Feedback Loop Service
- Pipeline Orchestrator

Run with: pytest tests/test_incremental_pipeline.py -v
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

# Import pipeline components
from entities.data_delta import (
    DataDelta, 
    DeltaType, 
    ProcessingStrategy,
    ChangeVector,
    DeltaMetrics
)
from infrastructure.learned_router import LearnedRouter, RouterDecision
from infrastructure.cost_optimizer import CostOptimizer, CostEstimate
from infrastructure.incremental_model import IncrementalModel
from services.change_detection_service import ChangeDetectionService
from services.feedback_loop_service import FeedbackLoopService


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_delta():
    """Create a sample DataDelta for testing."""
    return DataDelta(
        id="test-delta-001",
        source_file_id=1,
        delta_type=DeltaType.INSERT,
        created_at=datetime.utcnow(),
        rows_affected=100,
        change_magnitude=0.15,
        change_vector=ChangeVector(
            inserts=80,
            updates=15,
            deletes=5,
            columns_added=[],
            columns_removed=[],
            columns_modified=[]
        ),
        metrics=DeltaMetrics(
            rows_before=1000,
            rows_after=1100,
            size_before_bytes=50000,
            size_after_bytes=55000,
            entropy_before=0.7,
            entropy_after=0.72,
            feature_drift_scores={"col1": 0.05, "col2": 0.03}
        )
    )

@pytest.fixture
def small_delta():
    """Create a small delta that should be skipped."""
    return DataDelta(
        id="test-delta-small",
        source_file_id=1,
        delta_type=DeltaType.UPDATE,
        created_at=datetime.utcnow(),
        rows_affected=5,
        change_magnitude=0.005,
        change_vector=ChangeVector(
            inserts=0,
            updates=5,
            deletes=0,
            columns_added=[],
            columns_removed=[],
            columns_modified=[]
        ),
        metrics=DeltaMetrics(
            rows_before=1000,
            rows_after=1000,
            size_before_bytes=50000,
            size_after_bytes=50100,
            entropy_before=0.7,
            entropy_after=0.7,
            feature_drift_scores={}
        )
    )

@pytest.fixture
def large_delta():
    """Create a large delta that should trigger full retrain."""
    return DataDelta(
        id="test-delta-large",
        source_file_id=1,
        delta_type=DeltaType.MIXED,
        created_at=datetime.utcnow(),
        rows_affected=800,
        change_magnitude=0.6,
        change_vector=ChangeVector(
            inserts=400,
            updates=200,
            deletes=200,
            columns_added=["new_col1", "new_col2"],
            columns_removed=["old_col"],
            columns_modified=["modified_col"]
        ),
        metrics=DeltaMetrics(
            rows_before=1000,
            rows_after=1200,
            size_before_bytes=50000,
            size_after_bytes=65000,
            entropy_before=0.7,
            entropy_after=0.85,
            feature_drift_scores={"col1": 0.35, "col2": 0.28}
        )
    )

@pytest.fixture
def learned_router():
    """Create a LearnedRouter instance for testing."""
    return LearnedRouter(model_path="/tmp/test_router.pkl")

@pytest.fixture
def cost_optimizer():
    """Create a CostOptimizer instance for testing."""
    return CostOptimizer()

@pytest.fixture
def incremental_model():
    """Create an IncrementalModel instance for testing."""
    return IncrementalModel(model_path="/tmp/test_model.pkl")

@pytest.fixture
def feedback_service():
    """Create a FeedbackLoopService instance for testing."""
    return FeedbackLoopService()


# ============================================================================
# DATA DELTA TESTS
# ============================================================================

class TestDataDelta:
    """Tests for DataDelta entity."""
    
    def test_delta_creation(self, sample_delta):
        """Test basic delta creation."""
        assert sample_delta.id == "test-delta-001"
        assert sample_delta.delta_type == DeltaType.INSERT
        assert sample_delta.rows_affected == 100
        assert sample_delta.change_magnitude == 0.15
    
    def test_change_vector_totals(self, sample_delta):
        """Test change vector calculations."""
        cv = sample_delta.change_vector
        total_changes = cv.inserts + cv.updates + cv.deletes
        assert total_changes == 100
    
    def test_metrics_size_change(self, sample_delta):
        """Test metrics size calculations."""
        metrics = sample_delta.metrics
        size_change = metrics.size_after_bytes - metrics.size_before_bytes
        assert size_change == 5000
    
    def test_delta_type_values(self):
        """Test all delta type enum values exist."""
        assert DeltaType.INSERT.value == "insert"
        assert DeltaType.UPDATE.value == "update"
        assert DeltaType.DELETE.value == "delete"
        assert DeltaType.MIXED.value == "mixed"
        assert DeltaType.SCHEMA_CHANGE.value == "schema_change"
    
    def test_processing_strategy_values(self):
        """Test all processing strategy enum values exist."""
        assert ProcessingStrategy.SKIP.value == "skip"
        assert ProcessingStrategy.INCREMENTAL.value == "incremental"
        assert ProcessingStrategy.PARTIAL_RETRAIN.value == "partial_retrain"
        assert ProcessingStrategy.FULL_RETRAIN.value == "full_retrain"


# ============================================================================
# LEARNED ROUTER TESTS
# ============================================================================

class TestLearnedRouter:
    """Tests for LearnedRouter component."""
    
    def test_router_initialization(self, learned_router):
        """Test router initializes correctly."""
        assert learned_router is not None
        assert len(learned_router.feature_names) == 13
        assert 'change_magnitude' in learned_router.feature_names
    
    def test_default_thresholds(self, learned_router):
        """Test default thresholds are set."""
        thresholds = learned_router.default_thresholds
        assert thresholds['skip_magnitude'] == 0.01
        assert thresholds['incremental_magnitude'] == 0.15
        assert thresholds['partial_magnitude'] == 0.40
    
    @pytest.mark.asyncio
    async def test_route_small_delta_skipped(self, learned_router, small_delta):
        """Test that small deltas are routed to SKIP."""
        decision = await learned_router.route(small_delta)
        assert isinstance(decision, RouterDecision)
        assert decision.strategy == ProcessingStrategy.SKIP
        assert decision.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_route_large_delta_full_retrain(self, learned_router, large_delta):
        """Test that large deltas are routed to FULL_RETRAIN."""
        decision = await learned_router.route(large_delta)
        assert isinstance(decision, RouterDecision)
        assert decision.strategy in [ProcessingStrategy.FULL_RETRAIN, ProcessingStrategy.PARTIAL_RETRAIN]
    
    @pytest.mark.asyncio
    async def test_route_medium_delta_incremental(self, learned_router, sample_delta):
        """Test that medium deltas use incremental strategy."""
        decision = await learned_router.route(sample_delta)
        assert isinstance(decision, RouterDecision)
        assert decision.strategy in [ProcessingStrategy.INCREMENTAL, ProcessingStrategy.PARTIAL_RETRAIN]
    
    def test_extract_features(self, learned_router, sample_delta):
        """Test feature extraction from delta."""
        features = learned_router._extract_features(sample_delta)
        assert isinstance(features, np.ndarray)
        assert len(features) == len(learned_router.feature_names)
    
    def test_train_from_synthetic_data(self, learned_router):
        """Test training router with synthetic data."""
        result = learned_router.train_from_synthetic_data(n_samples=100)
        assert result['status'] == 'success'
        assert result['samples_used'] == 100
        assert 'cv_accuracy_mean' in result
        assert result['cv_accuracy_mean'] > 0.5  # Should perform better than random
    
    def test_router_status(self, learned_router):
        """Test getting router status."""
        # First train it
        learned_router.train_from_synthetic_data(n_samples=50)
        status = learned_router.get_status()
        
        assert 'mode' in status
        assert 'trained' in status
        assert status['trained'] == True


# ============================================================================
# COST OPTIMIZER TESTS
# ============================================================================

class TestCostOptimizer:
    """Tests for CostOptimizer component."""
    
    def test_optimizer_initialization(self, cost_optimizer):
        """Test cost optimizer initializes correctly."""
        assert cost_optimizer is not None
        assert hasattr(cost_optimizer, 'coefficients')
    
    @pytest.mark.asyncio
    async def test_estimate_costs(self, cost_optimizer, sample_delta):
        """Test cost estimation for all strategies."""
        estimates = await cost_optimizer.estimate_costs(sample_delta)
        
        assert ProcessingStrategy.SKIP in estimates
        assert ProcessingStrategy.INCREMENTAL in estimates
        assert ProcessingStrategy.PARTIAL_RETRAIN in estimates
        assert ProcessingStrategy.FULL_RETRAIN in estimates
        
        # Skip should always have lowest cost
        assert estimates[ProcessingStrategy.SKIP].total_cost == 0
        
        # Full retrain should have highest cost
        assert estimates[ProcessingStrategy.FULL_RETRAIN].total_cost > estimates[ProcessingStrategy.INCREMENTAL].total_cost
    
    @pytest.mark.asyncio
    async def test_recommend_strategy(self, cost_optimizer, sample_delta):
        """Test strategy recommendation."""
        router_decision = RouterDecision(
            strategy=ProcessingStrategy.INCREMENTAL,
            confidence=0.8,
            reasoning="Test",
            estimated_cost=1.0,
            estimated_accuracy_impact=0.02,
            feature_importance={}
        )
        
        recommendation = await cost_optimizer.recommend_strategy(
            sample_delta, router_decision
        )
        
        assert recommendation.recommended_strategy is not None
        assert 0 <= recommendation.confidence <= 1
    
    def test_calibrate_from_benchmark(self, cost_optimizer):
        """Test calibration from benchmark data."""
        result = cost_optimizer.calibrate_from_benchmark()
        
        assert result['status'] == 'success'
        assert 'updated_coefficients' in result
        assert 'benchmark_results' in result
    
    def test_get_calibration_stats(self, cost_optimizer):
        """Test getting calibration statistics."""
        # First calibrate
        cost_optimizer.calibrate_from_benchmark()
        stats = cost_optimizer.get_calibration_stats()
        
        assert 'total_calibrations' in stats
        assert 'last_calibration' in stats
        assert 'coefficient_history' in stats


# ============================================================================
# INCREMENTAL MODEL TESTS
# ============================================================================

class TestIncrementalModel:
    """Tests for IncrementalModel component."""
    
    def test_model_initialization(self, incremental_model):
        """Test incremental model initializes correctly."""
        assert incremental_model is not None
        assert incremental_model.model is None  # Not trained yet
    
    def test_train_model(self, incremental_model):
        """Test full model training."""
        # Create sample training data
        X = np.random.randn(100, 5)
        y = (X[:, 0] + X[:, 1] > 0).astype(int)
        
        result = incremental_model.train(X, y)
        
        assert result['status'] == 'success'
        assert incremental_model.model is not None
        assert result['samples'] == 100
        assert 'accuracy' in result
    
    def test_incremental_update(self, incremental_model):
        """Test incremental model update."""
        # First train
        X_train = np.random.randn(100, 5)
        y_train = (X_train[:, 0] + X_train[:, 1] > 0).astype(int)
        incremental_model.train(X_train, y_train)
        
        # Then incremental update
        X_new = np.random.randn(20, 5)
        y_new = (X_new[:, 0] + X_new[:, 1] > 0).astype(int)
        
        result = incremental_model.incremental_update(X_new, y_new)
        
        assert result['status'] == 'success'
        assert result['method'] == 'partial_fit'
        assert result['samples_added'] == 20
    
    def test_partial_retrain(self, incremental_model):
        """Test partial model retraining."""
        # First train
        X_train = np.random.randn(100, 5)
        y_train = (X_train[:, 0] + X_train[:, 1] > 0).astype(int)
        incremental_model.train(X_train, y_train)
        
        # Partial retrain with new data
        X_new = np.random.randn(50, 5)
        y_new = (X_new[:, 0] + X_new[:, 1] > 0).astype(int)
        
        result = incremental_model.partial_retrain(X_new, y_new, retain_ratio=0.5)
        
        assert result['status'] == 'success'
        assert 'retained_samples' in result
    
    def test_predict(self, incremental_model):
        """Test model prediction."""
        # Train first
        X_train = np.random.randn(100, 5)
        y_train = (X_train[:, 0] + X_train[:, 1] > 0).astype(int)
        incremental_model.train(X_train, y_train)
        
        # Predict
        X_test = np.random.randn(10, 5)
        predictions = incremental_model.predict(X_test)
        
        assert predictions is not None
        assert len(predictions) == 10
        assert all(p in [0, 1] for p in predictions)
    
    def test_get_status(self, incremental_model):
        """Test getting model status."""
        # Train first
        X = np.random.randn(50, 5)
        y = (X[:, 0] > 0).astype(int)
        incremental_model.train(X, y)
        
        status = incremental_model.get_status()
        
        assert status['trained'] == True
        assert 'total_samples' in status
        assert 'update_count' in status


# ============================================================================
# FEEDBACK LOOP SERVICE TESTS
# ============================================================================

class TestFeedbackLoopService:
    """Tests for FeedbackLoopService component."""
    
    def test_service_initialization(self, feedback_service):
        """Test feedback service initializes correctly."""
        assert feedback_service is not None
        assert len(feedback_service.outcome_history) == 0
    
    @pytest.mark.asyncio
    async def test_record_outcome(self, feedback_service, sample_delta):
        """Test recording an outcome."""
        await feedback_service.record_outcome(
            delta=sample_delta,
            strategy_used=ProcessingStrategy.INCREMENTAL,
            estimated_cost=1.0,
            actual_cost=1.2,
            estimated_accuracy_impact=0.02,
            actual_accuracy_impact=0.025
        )
        
        assert len(feedback_service.outcome_history) == 1
        outcome = feedback_service.outcome_history[0]
        assert outcome['strategy'] == 'incremental'
        assert outcome['cost_error'] == pytest.approx(0.2, abs=0.01)
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, feedback_service, sample_delta):
        """Test getting feedback statistics."""
        # Record some outcomes
        for i in range(5):
            await feedback_service.record_outcome(
                delta=sample_delta,
                strategy_used=ProcessingStrategy.INCREMENTAL,
                estimated_cost=1.0 + i * 0.1,
                actual_cost=1.1 + i * 0.1,
                estimated_accuracy_impact=0.02,
                actual_accuracy_impact=0.022
            )
        
        stats = await feedback_service.get_statistics()
        
        assert stats['total_decisions'] == 5
        assert 'avg_cost_error' in stats
        assert 'strategy_distribution' in stats
    
    @pytest.mark.asyncio
    async def test_get_recommendations(self, feedback_service, sample_delta):
        """Test getting system recommendations."""
        # Record outcomes
        for i in range(10):
            await feedback_service.record_outcome(
                delta=sample_delta,
                strategy_used=ProcessingStrategy.INCREMENTAL,
                estimated_cost=1.0,
                actual_cost=1.5,  # High error
                estimated_accuracy_impact=0.02,
                actual_accuracy_impact=0.025
            )
        
        recommendations = await feedback_service.get_recommendations()
        
        assert isinstance(recommendations, list)
        # Should recommend calibration due to high cost error
        assert any('calibrat' in r.lower() for r in recommendations)


# ============================================================================
# CHANGE DETECTION SERVICE TESTS
# ============================================================================

class TestChangeDetectionService:
    """Tests for ChangeDetectionService component."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock()
    
    @pytest.fixture
    def change_detection_service(self, mock_db):
        """Create a ChangeDetectionService instance."""
        return ChangeDetectionService(mock_db)
    
    def test_service_initialization(self, change_detection_service):
        """Test change detection service initializes correctly."""
        assert change_detection_service is not None
    
    @pytest.mark.asyncio
    async def test_calculate_change_magnitude(self, change_detection_service):
        """Test change magnitude calculation."""
        old_data = {"rows": 1000, "checksum": "abc123"}
        new_data = {"rows": 1100, "checksum": "def456"}
        
        magnitude = change_detection_service._calculate_change_magnitude(
            old_data, new_data
        )
        
        assert 0 <= magnitude <= 1
    
    @pytest.mark.asyncio  
    async def test_detect_delta_type(self, change_detection_service):
        """Test delta type detection."""
        # Test insert detection
        change_vector = ChangeVector(
            inserts=100, updates=0, deletes=0,
            columns_added=[], columns_removed=[], columns_modified=[]
        )
        delta_type = change_detection_service._detect_delta_type(change_vector)
        assert delta_type == DeltaType.INSERT
        
        # Test mixed detection
        change_vector = ChangeVector(
            inserts=50, updates=30, deletes=20,
            columns_added=[], columns_removed=[], columns_modified=[]
        )
        delta_type = change_detection_service._detect_delta_type(change_vector)
        assert delta_type == DeltaType.MIXED


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestPipelineIntegration:
    """Integration tests for the complete pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_flow_small_delta(
        self, learned_router, cost_optimizer, feedback_service, small_delta
    ):
        """Test complete pipeline flow for a small delta."""
        # Step 1: Route the delta
        decision = await learned_router.route(small_delta)
        assert decision.strategy == ProcessingStrategy.SKIP
        
        # Step 2: Get cost estimate
        costs = await cost_optimizer.estimate_costs(small_delta)
        assert costs[ProcessingStrategy.SKIP].total_cost == 0
        
        # Step 3: Record outcome
        await feedback_service.record_outcome(
            delta=small_delta,
            strategy_used=decision.strategy,
            estimated_cost=0,
            actual_cost=0,
            estimated_accuracy_impact=0,
            actual_accuracy_impact=0
        )
        
        stats = await feedback_service.get_statistics()
        assert stats['total_decisions'] >= 1
    
    @pytest.mark.asyncio
    async def test_full_pipeline_flow_large_delta(
        self, learned_router, cost_optimizer, incremental_model, feedback_service, large_delta
    ):
        """Test complete pipeline flow for a large delta."""
        # Step 1: Route the delta
        decision = await learned_router.route(large_delta)
        
        # Step 2: Get cost estimate
        costs = await cost_optimizer.estimate_costs(large_delta)
        
        # Step 3: Train/update model based on decision
        X = np.random.randn(100, 5)
        y = (X[:, 0] > 0).astype(int)
        
        if decision.strategy == ProcessingStrategy.FULL_RETRAIN:
            result = incremental_model.train(X, y)
        elif decision.strategy == ProcessingStrategy.INCREMENTAL:
            incremental_model.train(X[:50], y[:50])  # Initial train
            result = incremental_model.incremental_update(X[50:], y[50:])
        else:
            result = incremental_model.train(X, y)
        
        assert result['status'] == 'success'
        
        # Step 4: Record outcome
        actual_cost = result.get('training_time_ms', 100) / 1000
        await feedback_service.record_outcome(
            delta=large_delta,
            strategy_used=decision.strategy,
            estimated_cost=decision.estimated_cost,
            actual_cost=actual_cost,
            estimated_accuracy_impact=decision.estimated_accuracy_impact,
            actual_accuracy_impact=0.03
        )
    
    @pytest.mark.asyncio
    async def test_router_learns_from_feedback(self, learned_router, feedback_service):
        """Test that router can be retrained based on feedback."""
        # Train router initially
        result1 = learned_router.train_from_synthetic_data(n_samples=100)
        initial_accuracy = result1['cv_accuracy_mean']
        
        # Train again with more samples (simulating learning from feedback)
        result2 = learned_router.train_from_synthetic_data(n_samples=200)
        
        # Model should still work after retraining
        assert result2['status'] == 'success'
        assert result2['samples_used'] == 200


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance tests for pipeline components."""
    
    def test_router_inference_speed(self, learned_router, sample_delta):
        """Test that router inference is fast enough."""
        import time
        
        # Train first
        learned_router.train_from_synthetic_data(n_samples=100)
        
        # Measure inference time
        start = time.time()
        for _ in range(100):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                learned_router.route(sample_delta)
            )
        elapsed = time.time() - start
        
        # Should process 100 decisions in under 1 second
        assert elapsed < 1.0, f"Router too slow: {elapsed}s for 100 decisions"
    
    def test_cost_estimation_speed(self, cost_optimizer, sample_delta):
        """Test that cost estimation is fast."""
        import time
        
        start = time.time()
        for _ in range(100):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                cost_optimizer.estimate_costs(sample_delta)
            )
        elapsed = time.time() - start
        
        # Should estimate costs 100 times in under 0.5 seconds
        assert elapsed < 0.5, f"Cost optimizer too slow: {elapsed}s for 100 estimates"
    
    def test_incremental_vs_full_retrain_speed(self, incremental_model):
        """Test that incremental updates are faster than full retraining."""
        import time
        
        # Generate data
        X_initial = np.random.randn(1000, 10)
        y_initial = (X_initial[:, 0] > 0).astype(int)
        X_new = np.random.randn(100, 10)
        y_new = (X_new[:, 0] > 0).astype(int)
        
        # Measure full retrain time
        start = time.time()
        incremental_model.train(X_initial, y_initial)
        full_retrain_time = time.time() - start
        
        # Measure incremental update time
        start = time.time()
        incremental_model.incremental_update(X_new, y_new)
        incremental_time = time.time() - start
        
        # Incremental should be faster
        assert incremental_time < full_retrain_time, \
            f"Incremental ({incremental_time}s) should be faster than full retrain ({full_retrain_time}s)"


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Edge case tests for robustness."""
    
    def test_router_with_untrained_model(self, learned_router, sample_delta):
        """Test router behavior with untrained model (uses rules)."""
        import asyncio
        # Should fall back to rule-based routing
        decision = asyncio.get_event_loop().run_until_complete(
            learned_router.route(sample_delta)
        )
        assert decision is not None
        assert decision.strategy in list(ProcessingStrategy)
    
    def test_model_predict_before_training(self, incremental_model):
        """Test prediction before training returns None."""
        X = np.random.randn(10, 5)
        predictions = incremental_model.predict(X)
        assert predictions is None
    
    def test_empty_delta(self):
        """Test handling of delta with no changes."""
        empty_delta = DataDelta(
            id="empty-delta",
            source_file_id=1,
            delta_type=DeltaType.UPDATE,
            created_at=datetime.utcnow(),
            rows_affected=0,
            change_magnitude=0.0,
            change_vector=ChangeVector(
                inserts=0, updates=0, deletes=0,
                columns_added=[], columns_removed=[], columns_modified=[]
            ),
            metrics=DeltaMetrics(
                rows_before=1000,
                rows_after=1000,
                size_before_bytes=50000,
                size_after_bytes=50000,
                entropy_before=0.7,
                entropy_after=0.7,
                feature_drift_scores={}
            )
        )
        
        router = LearnedRouter(model_path="/tmp/test.pkl")
        import asyncio
        decision = asyncio.get_event_loop().run_until_complete(
            router.route(empty_delta)
        )
        
        # Should skip empty delta
        assert decision.strategy == ProcessingStrategy.SKIP
    
    def test_extreme_values(self, cost_optimizer):
        """Test handling of extreme delta values."""
        extreme_delta = DataDelta(
            id="extreme-delta",
            source_file_id=1,
            delta_type=DeltaType.MIXED,
            created_at=datetime.utcnow(),
            rows_affected=1000000,
            change_magnitude=1.0,  # Maximum magnitude
            change_vector=ChangeVector(
                inserts=500000, updates=300000, deletes=200000,
                columns_added=["c" + str(i) for i in range(100)],
                columns_removed=["d" + str(i) for i in range(50)],
                columns_modified=["m" + str(i) for i in range(200)]
            ),
            metrics=DeltaMetrics(
                rows_before=1000000,
                rows_after=1300000,
                size_before_bytes=1000000000,
                size_after_bytes=1500000000,
                entropy_before=0.9,
                entropy_after=0.95,
                feature_drift_scores={f"col{i}": 0.5 for i in range(100)}
            )
        )
        
        import asyncio
        costs = asyncio.get_event_loop().run_until_complete(
            cost_optimizer.estimate_costs(extreme_delta)
        )
        
        # All costs should be finite
        for strategy, estimate in costs.items():
            assert np.isfinite(estimate.total_cost)
            assert estimate.total_cost >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
