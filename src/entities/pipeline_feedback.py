"""
Pipeline Feedback Entity - Persistent Storage for ML Pipeline Feedback.

Stores feedback about model decisions for continuous learning.
"""

from infrastructure.db.mysql import mysql as db
from sqlalchemy import Column, String, Float, JSON, Text, Boolean, Integer, DateTime
from sqlalchemy.sql import func
import uuid


class PipelineFeedback(db.Base):
    """
    Stores feedback about ML pipeline decisions.
    
    Used by the FeedbackLoopService for continuous model improvement.
    """
    __tablename__ = "pipeline_feedback"
    
    id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    
    # What decision this feedback is about
    delta_id = Column(String(36), nullable=False, index=True)
    strategy = Column(String(50), nullable=False)  # full, incremental, partial, skip
    
    # The predicted vs actual outcomes
    predicted_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    predicted_benefit = Column(Float, nullable=True)
    actual_benefit = Column(Float, nullable=True)
    
    # Quality metrics
    predicted_accuracy = Column(Float, nullable=True)
    actual_accuracy = Column(Float, nullable=True)
    
    # Decision context
    delta_size = Column(Integer, nullable=True)
    delta_significance = Column(Float, nullable=True)
    affected_tables = Column(JSON, nullable=True)  # List of affected tables
    
    # Outcome
    was_correct = Column(Boolean, nullable=True)  # Did the strategy work well?
    improvement_ratio = Column(Float, nullable=True)  # actual_benefit / predicted_benefit
    
    # User feedback (if any)
    user_rating = Column(Integer, nullable=True)  # 1-5 rating
    user_comment = Column(Text, nullable=True)
    
    # Training status
    used_for_training = Column(Boolean, default=False, index=True)
    training_batch_id = Column(String(36), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<PipelineFeedback {self.id} delta={self.delta_id} strategy={self.strategy}>"


class RouterTrainingRecord(db.Base):
    """
    Records when the learned router was trained.
    
    Provides audit trail for model training events.
    """
    __tablename__ = "router_training_records"
    
    id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Training batch info
    batch_id = Column(String(36), nullable=False, unique=True, index=True)
    samples_count = Column(Integer, nullable=False)
    feedback_ids = Column(JSON, nullable=True)  # List of feedback IDs used
    
    # Training outcome
    model_version = Column(Integer, nullable=True)
    training_accuracy = Column(Float, nullable=True)
    validation_accuracy = Column(Float, nullable=True)
    training_time_seconds = Column(Float, nullable=True)
    
    # Model metrics before training
    previous_accuracy = Column(Float, nullable=True)
    accuracy_improvement = Column(Float, nullable=True)
    
    # Training configuration
    training_strategy = Column(String(50), nullable=True)  # full, incremental
    hyperparameters = Column(JSON, nullable=True)
    
    # Status
    status = Column(String(20), default="completed")  # completed, failed, rolled_back
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"<RouterTrainingRecord {self.batch_id} samples={self.samples_count}>"
