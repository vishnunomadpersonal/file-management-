"""Add authentication and organization tables

Revision ID: auth_and_organizations
Revises: incremental_ml_pipeline
Create Date: 2024-12-05

This migration adds:
- organizations table for multi-tenant support
- Updated users table with authentication fields
- audit_logs table for compliance
- api_keys table for service authentication
- refresh_tokens table for session management
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'auth_and_organizations'
down_revision = 'incremental_ml_pipeline'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create organizations table first (users will reference it)
    op.create_table(
        'organizations',
        sa.Column('id', sa.VARCHAR(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('email', sa.String(255)),
        sa.Column('phone', sa.String(50)),
        sa.Column('website', sa.String(255)),
        sa.Column('plan', sa.String(50), default='free'),
        sa.Column('plan_expires_at', sa.DateTime),
        sa.Column('storage_quota_bytes', sa.BigInteger, default=1073741824),
        sa.Column('storage_used_bytes', sa.BigInteger, default=0),
        sa.Column('max_users', sa.Integer, default=5),
        sa.Column('max_files', sa.Integer, default=1000),
        sa.Column('features', sa.JSON(none_as_null=True)),
        sa.Column('settings', sa.JSON(none_as_null=True)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_organizations_name', 'organizations', ['name'])
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)
    
    # Add new columns to users table
    # First check if columns exist (for idempotency)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_columns = [c['name'] for c in inspector.get_columns('users')]
    
    columns_to_add = {
        'email': sa.Column('email', sa.String(255), nullable=True),
        'password_hash': sa.Column('password_hash', sa.String(255)),
        'organization_id': sa.Column('organization_id', sa.VARCHAR(36)),
        'role': sa.Column('role', sa.String(50), default='user'),
        'is_active': sa.Column('is_active', sa.Boolean, default=True),
        'is_verified': sa.Column('is_verified', sa.Boolean, default=False),
        'oauth_provider': sa.Column('oauth_provider', sa.String(50)),
        'oauth_id': sa.Column('oauth_id', sa.String(255)),
        'avatar_url': sa.Column('avatar_url', sa.String(500)),
        'bio': sa.Column('bio', sa.Text),
        'failed_login_attempts': sa.Column('failed_login_attempts', sa.VARCHAR(5), default='0'),
        'locked_until': sa.Column('locked_until', sa.DateTime),
        'last_login_at': sa.Column('last_login_at', sa.DateTime),
        'last_login_ip': sa.Column('last_login_ip', sa.String(45)),
        'password_changed_at': sa.Column('password_changed_at', sa.DateTime),
        'email_verified_at': sa.Column('email_verified_at', sa.DateTime),
        'verification_token': sa.Column('verification_token', sa.String(255)),
        'reset_token': sa.Column('reset_token', sa.String(255)),
        'reset_token_expires_at': sa.Column('reset_token_expires_at', sa.DateTime),
    }
    
    for col_name, col_def in columns_to_add.items():
        if col_name not in existing_columns:
            op.add_column('users', col_def)
    
    # Add email index if not exists
    if 'email' not in existing_columns:
        op.create_index('ix_users_email', 'users', ['email'], unique=True)
    
    # Add organization foreign key if column was added
    if 'organization_id' not in existing_columns:
        op.create_foreign_key(
            'fk_users_organization_id', 
            'users', 'organizations', 
            ['organization_id'], ['id']
        )
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.VARCHAR(36), primary_key=True),
        sa.Column('user_id', sa.VARCHAR(36)),
        sa.Column('user_email', sa.String(255)),
        sa.Column('organization_id', sa.VARCHAR(36)),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50)),
        sa.Column('resource_id', sa.VARCHAR(36)),
        sa.Column('details', sa.JSON(none_as_null=True)),
        sa.Column('changes', sa.JSON(none_as_null=True)),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('request_id', sa.String(36)),
        sa.Column('status', sa.String(20), default='success'),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_organization_id', 'audit_logs', ['organization_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    
    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.VARCHAR(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('key_prefix', sa.String(10), nullable=False),
        sa.Column('user_id', sa.VARCHAR(36), nullable=False),
        sa.Column('organization_id', sa.VARCHAR(36), nullable=False),
        sa.Column('role', sa.String(50), default='api_service'),
        sa.Column('scopes', sa.JSON(none_as_null=True)),
        sa.Column('allowed_ips', sa.JSON(none_as_null=True)),
        sa.Column('rate_limit', sa.Integer, default=1000),
        sa.Column('last_used_at', sa.DateTime),
        sa.Column('usage_count', sa.Integer, default=0),
        sa.Column('expires_at', sa.DateTime),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])
    op.create_index('ix_api_keys_organization_id', 'api_keys', ['organization_id'])
    
    # Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.VARCHAR(36), primary_key=True),
        sa.Column('token_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('user_id', sa.VARCHAR(36), nullable=False),
        sa.Column('device_info', sa.String(255)),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('is_revoked', sa.Boolean, default=False),
        sa.Column('revoked_at', sa.DateTime),
        sa.Column('revoked_reason', sa.String(255)),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('last_used_at', sa.DateTime),
    )
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=True)
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    
    # Create feedback_records table for ML pipeline persistence
    op.create_table(
        'feedback_records',
        sa.Column('id', sa.VARCHAR(36), primary_key=True),
        sa.Column('delta_id', sa.VARCHAR(36)),
        sa.Column('strategy', sa.String(50), nullable=False),
        sa.Column('estimated_cost', sa.Float),
        sa.Column('actual_cost', sa.Float),
        sa.Column('cost_error', sa.Float),
        sa.Column('estimated_accuracy_impact', sa.Float),
        sa.Column('actual_accuracy_impact', sa.Float),
        sa.Column('accuracy_error', sa.Float),
        sa.Column('was_correct_decision', sa.Boolean),
        sa.Column('delta_features', sa.JSON(none_as_null=True)),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_feedback_records_strategy', 'feedback_records', ['strategy'])
    op.create_index('ix_feedback_records_created_at', 'feedback_records', ['created_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('feedback_records')
    op.drop_table('refresh_tokens')
    op.drop_table('api_keys')
    op.drop_table('audit_logs')
    
    # Drop user columns (be careful - this is destructive)
    columns_to_drop = [
        'email', 'password_hash', 'organization_id', 'role', 'is_active',
        'is_verified', 'oauth_provider', 'oauth_id', 'avatar_url', 'bio',
        'failed_login_attempts', 'locked_until', 'last_login_at', 'last_login_ip',
        'password_changed_at', 'email_verified_at', 'verification_token',
        'reset_token', 'reset_token_expires_at'
    ]
    
    # Drop foreign key first
    try:
        op.drop_constraint('fk_users_organization_id', 'users', type_='foreignkey')
    except:
        pass
    
    # Drop index
    try:
        op.drop_index('ix_users_email', table_name='users')
    except:
        pass
    
    for col in columns_to_drop:
        try:
            op.drop_column('users', col)
        except:
            pass
    
    op.drop_table('organizations')
