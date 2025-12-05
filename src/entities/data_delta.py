"""
Data Delta Entity - Tracks incremental changes in uploaded data files.

This is a core component for incremental ML pipelines, enabling:
1. Change detection without full file comparison
2. Delta-based feature extraction
3. Cost estimation for update strategies

Research relevance: Incremental View Maintenance (IVM) concepts applied to ML pipelines.
"""

from infrastructure.db.mysql import mysql as db
from sqlalchemy import Column, String, JSON, Integer, VARCHAR, ForeignKey, Boolean, DateTime, Float, Text, Enum
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum


class DeltaType(enum.Enum):
    """Type of change detected in the data"""
    INSERT = "insert"      # New rows/records added
    DELETE = "delete"      # Rows/records removed
    UPDATE = "update"      # Existing rows modified
    SCHEMA = "schema"      # Structure change (columns added/removed)
    FULL = "full"          # Complete replacement (fallback)


class ProcessingStrategy(enum.Enum):
    """Strategy chosen by the learned router for processing this delta"""
    SKIP = "skip"                    # Change too small, skip processing
    INCREMENTAL = "incremental"      # Apply incremental update to model
    PARTIAL_RETRAIN = "partial"      # Retrain affected model components
    FULL_RETRAIN = "full"            # Complete model retraining required


class DataDelta(db.Base):
    """
    Represents a detected change (delta) between file versions.
    
    This entity enables incremental processing by capturing:
    - What changed (delta_type, affected_rows, affected_columns)
    - How significant the change is (change_magnitude, entropy_delta)
    - What processing strategy was selected (processing_strategy)
    - Performance metrics (processing_time_ms, cost_estimate)
    """
    __tablename__ = "data_deltas"
    
    id = Column(VARCHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Link to the file that changed
    file_id = Column(VARCHAR(36), ForeignKey("files.id"), nullable=False, index=True)
    
    # Version tracking
    version_before = Column(Integer, nullable=False, default=0)
    version_after = Column(Integer, nullable=False, default=1)
    
    # Delta characteristics
    delta_type = Column(String(20), nullable=False, default=DeltaType.FULL.value)
    
    # Quantitative change metrics
    rows_before = Column(Integer, default=0)
    rows_after = Column(Integer, default=0)
    rows_inserted = Column(Integer, default=0)
    rows_deleted = Column(Integer, default=0)
    rows_updated = Column(Integer, default=0)
    
    # Column-level tracking (for tabular data)
    columns_added = Column(JSON(none_as_null=True))      # List of new column names
    columns_removed = Column(JSON(none_as_null=True))    # List of removed column names
    columns_modified = Column(JSON(none_as_null=True))   # List of columns with value changes
    
    # Statistical change metrics (for learned router)
    change_magnitude = Column(Float, default=0.0)        # 0-1 scale of how much changed
    entropy_delta = Column(Float, default=0.0)           # Change in data distribution
    feature_drift_score = Column(Float, default=0.0)     # ML feature distribution shift
    
    # Compact delta representation (factorized)
    delta_summary = Column(JSON(none_as_null=True))      # Compressed change representation
    delta_hash = Column(String(64), index=True)          # Hash of the delta for deduplication
    
    # Processing decision (from learned router)
    processing_strategy = Column(String(20), default=ProcessingStrategy.FULL_RETRAIN.value)
    strategy_confidence = Column(Float, default=0.0)     # Router's confidence in decision
    
    # Cost estimation (for optimizer)
    estimated_cost = Column(Float, default=0.0)          # Predicted computational cost
    actual_cost = Column(Float)                          # Actual cost (for learning)
    cost_savings = Column(Float)                         # Savings vs full retraining
    
    # Performance tracking
    detection_time_ms = Column(Integer)                  # Time to detect delta
    processing_time_ms = Column(Integer)                 # Time to process delta
    
    # Timestamps
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime)
    
    # Status
    is_processed = Column(Boolean, default=False)
    processing_error = Column(Text)
    
    # Relationship to file
    file = relationship("File", backref="deltas")
    
    def __repr__(self):
        id_str = self.id[:8] if self.id else "NEW"
        file_str = self.file_id[:8] if self.file_id else "NONE"
        return f"<DataDelta {id_str} file={file_str} type={self.delta_type}>"
    
    @property
    def change_ratio(self) -> float:
        """Calculate the ratio of changed rows to total rows"""
        total = max(self.rows_before, self.rows_after, 1)
        changed = self.rows_inserted + self.rows_deleted + self.rows_updated
        return min(changed / total, 1.0)
    
    @property
    def is_significant_change(self) -> bool:
        """Determine if change warrants model update (threshold-based)"""
        return self.change_magnitude > 0.1 or self.feature_drift_score > 0.15
    
    def to_feature_vector(self) -> list:
        """
        Convert delta to feature vector for the learned router.
        This enables ML-based decision making on processing strategy.
        """
        return [
            self.rows_inserted / max(self.rows_after, 1),
            self.rows_deleted / max(self.rows_before, 1),
            self.rows_updated / max(self.rows_before, 1),
            self.change_magnitude,
            self.entropy_delta,
            self.feature_drift_score,
            len(self.columns_added or []),
            len(self.columns_removed or []),
            len(self.columns_modified or []),
            1 if self.delta_type == DeltaType.SCHEMA.value else 0
        ]


class ModelVersion(db.Base):
    """
    Tracks ML model versions and their relationship to data deltas.
    
    Enables:
    - Model lineage tracking
    - Rollback capabilities
    - Performance comparison across versions
    """
    __tablename__ = "model_versions"
    
    id = Column(VARCHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Model identification
    model_name = Column(String(255), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    
    # Link to delta that triggered this version
    triggered_by_delta_id = Column(VARCHAR(36), ForeignKey("data_deltas.id"))
    
    # Training metadata
    training_strategy = Column(String(20))               # How model was trained
    training_data_hash = Column(String(64))              # Hash of training data
    training_time_seconds = Column(Float)
    
    # Model artifacts (stored in MinIO)
    model_path = Column(String(255))                     # Path to model file
    model_size_bytes = Column(Integer)
    
    # Performance metrics
    accuracy = Column(Float)
    precision_score = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    custom_metrics = Column(JSON(none_as_null=True))
    
    # Comparison to previous version
    performance_delta = Column(Float)                    # Change in primary metric
    
    # Status
    is_active = Column(Boolean, default=False)           # Currently deployed version
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship
    triggered_by_delta = relationship("DataDelta", backref="model_versions")
    
    def __repr__(self):
        return f"<ModelVersion {self.model_name} v{self.version}>"


class PipelineRun(db.Base):
    """
    Tracks end-to-end pipeline executions for analysis and optimization.
    
    Enables:
    - Pipeline performance monitoring
    - Bottleneck identification
    - Cost analysis
    """
    __tablename__ = "pipeline_runs"
    
    id = Column(VARCHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Pipeline identification
    pipeline_name = Column(String(255), nullable=False, index=True)
    run_number = Column(Integer, nullable=False, default=1)
    
    # Trigger information
    trigger_type = Column(String(50))                    # "file_upload", "scheduled", "manual"
    trigger_file_id = Column(VARCHAR(36), ForeignKey("files.id"))
    
    # Timing
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Stage timings (for bottleneck analysis)
    stage_timings = Column(JSON(none_as_null=True))      # {"detection": 100, "extraction": 500, ...}
    
    # Resource usage
    peak_memory_mb = Column(Float)
    total_cpu_seconds = Column(Float)
    
    # Outcome
    status = Column(String(20), default="running")       # running, completed, failed
    error_message = Column(Text)
    
    # Deltas processed in this run
    deltas_processed = Column(Integer, default=0)
    models_updated = Column(Integer, default=0)
    
    # Cost tracking
    estimated_cost = Column(Float)
    actual_cost = Column(Float)
    
    def __repr__(self):
        return f"<PipelineRun {self.pipeline_name} #{self.run_number}>"
