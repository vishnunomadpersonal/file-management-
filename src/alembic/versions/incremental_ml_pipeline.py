"""Add incremental ML pipeline tables

Revision ID: incremental_ml_pipeline
Revises: de84cb899fc5
Create Date: 2024-12-05

This migration adds tables for the incremental ML pipeline:
- data_deltas: Tracks changes between file versions
- model_versions: Tracks ML model versions
- pipeline_runs: Tracks pipeline executions
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'incremental_ml_pipeline'
down_revision = 'd3b2a1c4f789'  # Updated to latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create data_deltas table
    op.create_table(
        'data_deltas',
        sa.Column('id', sa.VARCHAR(36), primary_key=True),
        sa.Column('file_id', sa.VARCHAR(36), sa.ForeignKey('files.id'), nullable=False, index=True),
        
        # Version tracking
        sa.Column('version_before', sa.Integer, nullable=False, default=0),
        sa.Column('version_after', sa.Integer, nullable=False, default=1),
        
        # Delta characteristics
        sa.Column('delta_type', sa.String(20), nullable=False, default='full'),
        
        # Row-level metrics
        sa.Column('rows_before', sa.Integer, default=0),
        sa.Column('rows_after', sa.Integer, default=0),
        sa.Column('rows_inserted', sa.Integer, default=0),
        sa.Column('rows_deleted', sa.Integer, default=0),
        sa.Column('rows_updated', sa.Integer, default=0),
        
        # Column-level tracking
        sa.Column('columns_added', sa.JSON(none_as_null=True)),
        sa.Column('columns_removed', sa.JSON(none_as_null=True)),
        sa.Column('columns_modified', sa.JSON(none_as_null=True)),
        
        # Statistical metrics
        sa.Column('change_magnitude', sa.Float, default=0.0),
        sa.Column('entropy_delta', sa.Float, default=0.0),
        sa.Column('feature_drift_score', sa.Float, default=0.0),
        
        # Delta representation
        sa.Column('delta_summary', sa.JSON(none_as_null=True)),
        sa.Column('delta_hash', sa.String(64), index=True),
        
        # Processing decision
        sa.Column('processing_strategy', sa.String(20), default='full'),
        sa.Column('strategy_confidence', sa.Float, default=0.0),
        
        # Cost tracking
        sa.Column('estimated_cost', sa.Float, default=0.0),
        sa.Column('actual_cost', sa.Float),
        sa.Column('cost_savings', sa.Float),
        
        # Performance
        sa.Column('detection_time_ms', sa.Integer),
        sa.Column('processing_time_ms', sa.Integer),
        
        # Timestamps
        sa.Column('detected_at', sa.DateTime, nullable=False),
        sa.Column('processed_at', sa.DateTime),
        
        # Status
        sa.Column('is_processed', sa.Boolean, default=False),
        sa.Column('processing_error', sa.Text),
    )
    
    # Create model_versions table
    op.create_table(
        'model_versions',
        sa.Column('id', sa.VARCHAR(36), primary_key=True),
        
        # Model identification
        sa.Column('model_name', sa.String(255), nullable=False, index=True),
        sa.Column('version', sa.Integer, nullable=False, default=1),
        
        # Link to triggering delta
        sa.Column('triggered_by_delta_id', sa.VARCHAR(36), sa.ForeignKey('data_deltas.id')),
        
        # Training metadata
        sa.Column('training_strategy', sa.String(20)),
        sa.Column('training_data_hash', sa.String(64)),
        sa.Column('training_time_seconds', sa.Float),
        
        # Model artifacts
        sa.Column('model_path', sa.String(255)),
        sa.Column('model_size_bytes', sa.Integer),
        
        # Performance metrics
        sa.Column('accuracy', sa.Float),
        sa.Column('precision_score', sa.Float),
        sa.Column('recall', sa.Float),
        sa.Column('f1_score', sa.Float),
        sa.Column('custom_metrics', sa.JSON(none_as_null=True)),
        
        # Comparison
        sa.Column('performance_delta', sa.Float),
        
        # Status
        sa.Column('is_active', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    
    # Create pipeline_runs table
    op.create_table(
        'pipeline_runs',
        sa.Column('id', sa.VARCHAR(36), primary_key=True),
        
        # Pipeline identification
        sa.Column('pipeline_name', sa.String(255), nullable=False, index=True),
        sa.Column('run_number', sa.Integer, nullable=False, default=1),
        
        # Trigger info
        sa.Column('trigger_type', sa.String(50)),
        sa.Column('trigger_file_id', sa.VARCHAR(36), sa.ForeignKey('files.id')),
        
        # Timing
        sa.Column('started_at', sa.DateTime, nullable=False),
        sa.Column('completed_at', sa.DateTime),
        
        # Stage timings
        sa.Column('stage_timings', sa.JSON(none_as_null=True)),
        
        # Resource usage
        sa.Column('peak_memory_mb', sa.Float),
        sa.Column('total_cpu_seconds', sa.Float),
        
        # Outcome
        sa.Column('status', sa.String(20), default='running'),
        sa.Column('error_message', sa.Text),
        
        # Processing stats
        sa.Column('deltas_processed', sa.Integer, default=0),
        sa.Column('models_updated', sa.Integer, default=0),
        
        # Cost
        sa.Column('estimated_cost', sa.Float),
        sa.Column('actual_cost', sa.Float),
    )
    
    # Create indexes for common queries
    op.create_index('ix_data_deltas_processed', 'data_deltas', ['is_processed'])
    op.create_index('ix_data_deltas_detected_at', 'data_deltas', ['detected_at'])
    op.create_index('ix_model_versions_active', 'model_versions', ['model_name', 'is_active'])
    op.create_index('ix_pipeline_runs_status', 'pipeline_runs', ['status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_pipeline_runs_status', 'pipeline_runs')
    op.drop_index('ix_model_versions_active', 'model_versions')
    op.drop_index('ix_data_deltas_detected_at', 'data_deltas')
    op.drop_index('ix_data_deltas_processed', 'data_deltas')
    
    # Drop tables
    op.drop_table('pipeline_runs')
    op.drop_table('model_versions')
    op.drop_table('data_deltas')
