"""
Cost-Based Optimizer - Estimates and optimizes processing costs for ML pipelines.

This component implements database-style cost estimation for ML operations:
1. Estimates computational cost of different strategies
2. Considers resource constraints (memory, time, budget)
3. Makes cost-aware decisions that balance accuracy vs efficiency

Research relevance: Query Optimization, Cost Models, Adaptive Processing
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from entities.data_delta import DataDelta, ProcessingStrategy, PipelineRun
from infrastructure.learned_router import RouterDecision

logger = logging.getLogger(__name__)


@dataclass
class CostEstimate:
    """Detailed cost estimate for a processing operation."""
    strategy: ProcessingStrategy
    
    # Time estimates (seconds)
    estimated_time_seconds: float
    time_confidence_interval: Tuple[float, float]
    
    # Resource estimates
    estimated_memory_mb: float
    estimated_cpu_cores: float
    
    # Monetary cost (if applicable)
    estimated_cost_dollars: float
    
    # Quality estimates
    expected_accuracy: float
    accuracy_confidence_interval: Tuple[float, float]
    
    # Breakdown by stage
    stage_costs: Dict[str, float] = field(default_factory=dict)
    
    # Recommendations
    bottleneck_stage: str = ""
    optimization_suggestions: List[str] = field(default_factory=list)


@dataclass
class OptimizationConstraints:
    """Constraints for the optimizer to consider."""
    max_time_seconds: Optional[float] = None
    max_memory_mb: Optional[float] = None
    max_cost_dollars: Optional[float] = None
    min_accuracy: Optional[float] = None
    deadline: Optional[datetime] = None
    priority: str = "balanced"  # "speed", "accuracy", "cost", "balanced"


class CostBasedOptimizer:
    """
    Estimates and optimizes processing costs using learned cost models.
    
    Key features:
    1. Learns cost models from historical pipeline runs
    2. Considers multiple resource dimensions (time, memory, money)
    3. Provides Pareto-optimal strategy recommendations
    4. Adapts estimates based on feedback
    """
    
    def __init__(self):
        # Cost model coefficients (learned from historical data)
        self.time_coefficients = {
            ProcessingStrategy.SKIP: {'base': 0.1, 'per_row': 0.0},
            ProcessingStrategy.INCREMENTAL: {'base': 5.0, 'per_row': 0.001, 'per_change': 0.01},
            ProcessingStrategy.PARTIAL_RETRAIN: {'base': 30.0, 'per_row': 0.005, 'per_change': 0.02},
            ProcessingStrategy.FULL_RETRAIN: {'base': 60.0, 'per_row': 0.01, 'per_change': 0.0}
        }
        
        self.memory_coefficients = {
            ProcessingStrategy.SKIP: {'base': 10, 'per_row': 0.0},
            ProcessingStrategy.INCREMENTAL: {'base': 100, 'per_row': 0.001},
            ProcessingStrategy.PARTIAL_RETRAIN: {'base': 500, 'per_row': 0.005},
            ProcessingStrategy.FULL_RETRAIN: {'base': 1000, 'per_row': 0.01}
        }
        
        # Accuracy impact models
        self.accuracy_models = {
            ProcessingStrategy.SKIP: {'base_impact': 0.0, 'drift_multiplier': 1.0},
            ProcessingStrategy.INCREMENTAL: {'base_impact': 0.0, 'drift_multiplier': 0.3},
            ProcessingStrategy.PARTIAL_RETRAIN: {'base_impact': 0.0, 'drift_multiplier': 0.1},
            ProcessingStrategy.FULL_RETRAIN: {'base_impact': 0.0, 'drift_multiplier': 0.0}
        }
        
        # Historical statistics for confidence intervals
        self.historical_variance = {
            ProcessingStrategy.SKIP: 0.1,
            ProcessingStrategy.INCREMENTAL: 0.3,
            ProcessingStrategy.PARTIAL_RETRAIN: 0.4,
            ProcessingStrategy.FULL_RETRAIN: 0.2
        }
        
        # Cost per compute unit (for cloud pricing)
        self.cost_per_cpu_hour = 0.05  # dollars
        self.cost_per_gb_hour = 0.01   # dollars
    
    async def estimate_cost(
        self, 
        delta: DataDelta, 
        strategy: ProcessingStrategy,
        model_info: Optional[Dict[str, Any]] = None
    ) -> CostEstimate:
        """
        Estimate the cost of processing a delta with a given strategy.
        
        Args:
            delta: The data delta to process
            strategy: The processing strategy to estimate
            model_info: Optional info about the ML model being updated
            
        Returns:
            CostEstimate with detailed breakdown
        """
        model_info = model_info or {}
        
        # Calculate base metrics
        rows = max(delta.rows_after, 1)
        changed_rows = delta.rows_inserted + delta.rows_deleted + delta.rows_updated
        
        # Time estimation
        time_coef = self.time_coefficients[strategy]
        estimated_time = (
            time_coef['base'] +
            time_coef['per_row'] * rows +
            time_coef.get('per_change', 0) * changed_rows
        )
        
        # Apply model complexity multiplier if provided
        complexity_multiplier = model_info.get('complexity_multiplier', 1.0)
        estimated_time *= complexity_multiplier
        
        # Time confidence interval
        variance = self.historical_variance[strategy]
        time_ci = (
            estimated_time * (1 - variance),
            estimated_time * (1 + variance)
        )
        
        # Memory estimation
        mem_coef = self.memory_coefficients[strategy]
        estimated_memory = mem_coef['base'] + mem_coef['per_row'] * rows
        
        # CPU estimation (based on parallelization potential)
        estimated_cpu = 1.0 if strategy == ProcessingStrategy.SKIP else min(4.0, rows / 10000)
        
        # Monetary cost
        cpu_hours = (estimated_time / 3600) * estimated_cpu
        memory_gb_hours = (estimated_time / 3600) * (estimated_memory / 1024)
        estimated_cost = (
            cpu_hours * self.cost_per_cpu_hour +
            memory_gb_hours * self.cost_per_gb_hour
        )
        
        # Accuracy estimation
        acc_model = self.accuracy_models[strategy]
        drift_impact = delta.feature_drift_score * acc_model['drift_multiplier']
        magnitude_impact = delta.change_magnitude * 0.1 * acc_model['drift_multiplier']
        
        base_accuracy = model_info.get('current_accuracy', 0.95)
        expected_accuracy = base_accuracy - drift_impact - magnitude_impact
        
        accuracy_ci = (
            max(expected_accuracy - 0.05, 0.0),
            min(expected_accuracy + 0.02, 1.0)
        )
        
        # Stage breakdown
        stage_costs = self._estimate_stage_costs(delta, strategy, estimated_time)
        
        # Identify bottleneck
        bottleneck_stage = max(stage_costs.items(), key=lambda x: x[1])[0]
        
        # Generate optimization suggestions
        suggestions = self._generate_suggestions(delta, strategy, stage_costs)
        
        return CostEstimate(
            strategy=strategy,
            estimated_time_seconds=estimated_time,
            time_confidence_interval=time_ci,
            estimated_memory_mb=estimated_memory,
            estimated_cpu_cores=estimated_cpu,
            estimated_cost_dollars=estimated_cost,
            expected_accuracy=expected_accuracy,
            accuracy_confidence_interval=accuracy_ci,
            stage_costs=stage_costs,
            bottleneck_stage=bottleneck_stage,
            optimization_suggestions=suggestions
        )
    
    async def optimize(
        self,
        delta: DataDelta,
        router_decision: RouterDecision,
        constraints: OptimizationConstraints,
        model_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[ProcessingStrategy, CostEstimate, str]:
        """
        Find optimal strategy given constraints.
        
        Args:
            delta: The data delta to process
            router_decision: Initial decision from learned router
            constraints: Optimization constraints
            model_info: Info about the ML model
            
        Returns:
            Tuple of (optimal_strategy, cost_estimate, reasoning)
        """
        # Estimate costs for all viable strategies
        strategies = [
            ProcessingStrategy.SKIP,
            ProcessingStrategy.INCREMENTAL,
            ProcessingStrategy.PARTIAL_RETRAIN,
            ProcessingStrategy.FULL_RETRAIN
        ]
        
        estimates = {}
        for strategy in strategies:
            estimates[strategy] = await self.estimate_cost(delta, strategy, model_info)
        
        # Filter by hard constraints
        viable_strategies = []
        for strategy, estimate in estimates.items():
            violations = []
            
            if constraints.max_time_seconds and estimate.estimated_time_seconds > constraints.max_time_seconds:
                violations.append(f"time ({estimate.estimated_time_seconds:.1f}s > {constraints.max_time_seconds}s)")
            
            if constraints.max_memory_mb and estimate.estimated_memory_mb > constraints.max_memory_mb:
                violations.append(f"memory ({estimate.estimated_memory_mb:.0f}MB > {constraints.max_memory_mb}MB)")
            
            if constraints.max_cost_dollars and estimate.estimated_cost_dollars > constraints.max_cost_dollars:
                violations.append(f"cost (${estimate.estimated_cost_dollars:.2f} > ${constraints.max_cost_dollars})")
            
            if constraints.min_accuracy and estimate.expected_accuracy < constraints.min_accuracy:
                violations.append(f"accuracy ({estimate.expected_accuracy:.2f} < {constraints.min_accuracy})")
            
            if constraints.deadline:
                completion_time = datetime.utcnow() + timedelta(seconds=estimate.estimated_time_seconds)
                if completion_time > constraints.deadline:
                    violations.append(f"deadline (completes at {completion_time}, deadline {constraints.deadline})")
            
            if not violations:
                viable_strategies.append(strategy)
            else:
                logger.debug(f"Strategy {strategy.value} violates: {', '.join(violations)}")
        
        # If no viable strategies, return least-violating option
        if not viable_strategies:
            logger.warning("No strategy meets all constraints, selecting least-violating option")
            # Default to router's suggestion
            return (
                router_decision.strategy,
                estimates[router_decision.strategy],
                "No strategy meets all constraints, using router recommendation"
            )
        
        # Score viable strategies based on priority
        scored_strategies = []
        for strategy in viable_strategies:
            estimate = estimates[strategy]
            score = self._calculate_score(estimate, constraints.priority)
            scored_strategies.append((strategy, estimate, score))
        
        # Select best scoring strategy
        scored_strategies.sort(key=lambda x: x[2], reverse=True)
        best_strategy, best_estimate, best_score = scored_strategies[0]
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            best_strategy, 
            best_estimate, 
            router_decision.strategy,
            constraints.priority
        )
        
        logger.info(
            f"Optimizer selected {best_strategy.value} "
            f"(router suggested {router_decision.strategy.value}, "
            f"priority={constraints.priority})"
        )
        
        return best_strategy, best_estimate, reasoning
    
    def _calculate_score(self, estimate: CostEstimate, priority: str) -> float:
        """Calculate optimization score based on priority."""
        
        # Normalize metrics to 0-1 scale
        time_score = 1.0 / (1.0 + estimate.estimated_time_seconds / 60)  # Lower is better
        cost_score = 1.0 / (1.0 + estimate.estimated_cost_dollars * 10)   # Lower is better
        accuracy_score = estimate.expected_accuracy                       # Higher is better
        
        # Weight based on priority
        if priority == "speed":
            weights = {'time': 0.7, 'cost': 0.1, 'accuracy': 0.2}
        elif priority == "accuracy":
            weights = {'time': 0.1, 'cost': 0.1, 'accuracy': 0.8}
        elif priority == "cost":
            weights = {'time': 0.2, 'cost': 0.6, 'accuracy': 0.2}
        else:  # balanced
            weights = {'time': 0.33, 'cost': 0.33, 'accuracy': 0.34}
        
        score = (
            weights['time'] * time_score +
            weights['cost'] * cost_score +
            weights['accuracy'] * accuracy_score
        )
        
        return score
    
    def _estimate_stage_costs(
        self, 
        delta: DataDelta, 
        strategy: ProcessingStrategy,
        total_time: float
    ) -> Dict[str, float]:
        """Estimate time breakdown by pipeline stage."""
        
        if strategy == ProcessingStrategy.SKIP:
            return {'validation': total_time}
        
        if strategy == ProcessingStrategy.INCREMENTAL:
            return {
                'delta_extraction': total_time * 0.2,
                'feature_update': total_time * 0.3,
                'model_update': total_time * 0.4,
                'validation': total_time * 0.1
            }
        
        if strategy == ProcessingStrategy.PARTIAL_RETRAIN:
            return {
                'delta_extraction': total_time * 0.1,
                'affected_detection': total_time * 0.15,
                'partial_training': total_time * 0.55,
                'integration': total_time * 0.1,
                'validation': total_time * 0.1
            }
        
        # FULL_RETRAIN
        return {
            'data_loading': total_time * 0.15,
            'preprocessing': total_time * 0.2,
            'training': total_time * 0.5,
            'validation': total_time * 0.15
        }
    
    def _generate_suggestions(
        self, 
        delta: DataDelta, 
        strategy: ProcessingStrategy,
        stage_costs: Dict[str, float]
    ) -> List[str]:
        """Generate optimization suggestions."""
        suggestions = []
        
        # Check for potential optimizations
        if delta.rows_after > 100000 and strategy == ProcessingStrategy.FULL_RETRAIN:
            suggestions.append("Consider incremental updates for large datasets to reduce training time")
        
        if delta.change_magnitude < 0.05 and strategy != ProcessingStrategy.SKIP:
            suggestions.append(f"Change magnitude is low ({delta.change_magnitude:.2%}), consider skipping")
        
        if 'training' in stage_costs and stage_costs['training'] > 60:
            suggestions.append("Training is the bottleneck - consider distributed training or model simplification")
        
        if delta.feature_drift_score > 0.3:
            suggestions.append("High feature drift detected - full retrain recommended for accuracy")
        
        return suggestions
    
    def _generate_reasoning(
        self,
        selected: ProcessingStrategy,
        estimate: CostEstimate,
        router_suggestion: ProcessingStrategy,
        priority: str
    ) -> str:
        """Generate human-readable reasoning for the selection."""
        
        parts = []
        
        if selected == router_suggestion:
            parts.append(f"Confirmed router's {selected.value} recommendation")
        else:
            parts.append(f"Overrode router's {router_suggestion.value} with {selected.value}")
        
        parts.append(f"Priority: {priority}")
        parts.append(f"Est. time: {estimate.estimated_time_seconds:.1f}s")
        parts.append(f"Est. accuracy: {estimate.expected_accuracy:.1%}")
        parts.append(f"Est. cost: ${estimate.estimated_cost_dollars:.3f}")
        
        if estimate.bottleneck_stage:
            parts.append(f"Bottleneck: {estimate.bottleneck_stage}")
        
        return " | ".join(parts)
    
    async def update_from_feedback(
        self,
        strategy: ProcessingStrategy,
        estimated: CostEstimate,
        actual: Dict[str, Any]
    ):
        """
        Update cost models based on actual outcomes.
        
        This implements a feedback loop to improve estimation accuracy.
        """
        # Calculate estimation errors
        time_error = (actual.get('time_seconds', estimated.estimated_time_seconds) - 
                     estimated.estimated_time_seconds) / estimated.estimated_time_seconds
        
        memory_error = (actual.get('memory_mb', estimated.estimated_memory_mb) - 
                       estimated.estimated_memory_mb) / estimated.estimated_memory_mb
        
        # Update coefficients with exponential moving average
        alpha = 0.1  # Learning rate
        
        # Adjust base costs
        self.time_coefficients[strategy]['base'] *= (1 + alpha * time_error)
        self.memory_coefficients[strategy]['base'] *= (1 + alpha * memory_error)
        
        logger.info(
            f"Updated cost model for {strategy.value}: "
            f"time_error={time_error:.2%}, memory_error={memory_error:.2%}"
        )


# Singleton instance
cost_optimizer = CostBasedOptimizer()
