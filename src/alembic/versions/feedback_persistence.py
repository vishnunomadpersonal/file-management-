"""
Add pipeline feedback tables.

Revision ID: feedback_persistence
Revises: auth_and_organizations
Create Date: 2024-01-15

Creates:
- pipeline_feedback table for storing prediction/outcome data
- router_training_records table for training audit trail
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = 'feedback_persistence'
down_revision = 'auth_and_organizations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create feedback and training tables."""
    
    # Pipeline feedback table
    op.create_table(
        'pipeline_feedback',
        sa.Column('id', sa.String(36), primary_key=True),
        
        # Decision context
        sa.Column('delta_id', sa.String(36), nullable=False, index=True),
        sa.Column('strategy', sa.String(50), nullable=False),
        
        # Predictions
        sa.Column('predicted_cost', sa.Float, nullable=True),
        sa.Column('actual_cost', sa.Float, nullable=True),
        sa.Column('predicted_benefit', sa.Float, nullable=True),
        sa.Column('actual_benefit', sa.Float, nullable=True),
        sa.Column('predicted_accuracy', sa.Float, nullable=True),
        sa.Column('actual_accuracy', sa.Float, nullable=True),
        
        # Delta context
        sa.Column('delta_size', sa.Integer, nullable=True),
        sa.Column('delta_significance', sa.Float, nullable=True),
        sa.Column('affected_tables', sa.JSON, nullable=True),
        
        # Outcome
        sa.Column('was_correct', sa.Boolean, nullable=True),
        sa.Column('improvement_ratio', sa.Float, nullable=True),
        
        # User feedback
        sa.Column('user_rating', sa.Integer, nullable=True),
        sa.Column('user_comment', sa.Text, nullable=True),
        
        # Training status
        sa.Column('used_for_training', sa.Boolean, default=False, index=True),
        sa.Column('training_batch_id', sa.String(36), nullable=True, index=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create indexes for common queries
    op.create_index(
        'ix_pipeline_feedback_strategy', 
        'pipeline_feedback', 
        ['strategy']
    )
    op.create_index(
        'ix_pipeline_feedback_was_correct', 
        'pipeline_feedback', 
        ['was_correct']
    )
    
    # Router training records table
    op.create_table(
        'router_training_records',
        sa.Column('id', sa.String(36), primary_key=True),
        
        # Batch info
        sa.Column('batch_id', sa.String(36), nullable=False, unique=True, index=True),
        sa.Column('samples_count', sa.Integer, nullable=False),
        sa.Column('feedback_ids', sa.JSON, nullable=True),
        
        # Training outcome
        sa.Column('model_version', sa.Integer, nullable=True),
        sa.Column('training_accuracy', sa.Float, nullable=True),
        sa.Column('validation_accuracy', sa.Float, nullable=True),
        sa.Column('training_time_seconds', sa.Float, nullable=True),
        
        # Accuracy tracking
        sa.Column('previous_accuracy', sa.Float, nullable=True),
        sa.Column('accuracy_improvement', sa.Float, nullable=True),
        
        # Configuration
        sa.Column('training_strategy', sa.String(50), nullable=True),
        sa.Column('hyperparameters', sa.JSON, nullable=True),
        
        # Status
        sa.Column('status', sa.String(20), default='completed'),
        sa.Column('error_message', sa.Text, nullable=True),
        
        # Timestamps
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Create index for status queries
    op.create_index(
        'ix_router_training_records_status',
        'router_training_records',
        ['status']
    )


def downgrade() -> None:
    """Drop feedback and training tables."""
    
    op.drop_index('ix_router_training_records_status', 'router_training_records')
    op.drop_table('router_training_records')
    
    op.drop_index('ix_pipeline_feedback_was_correct', 'pipeline_feedback')
    op.drop_index('ix_pipeline_feedback_strategy', 'pipeline_feedback')
    op.drop_table('pipeline_feedback')
