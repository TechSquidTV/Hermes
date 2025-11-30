"""initial_migration

Revision ID: 96e3543c1899
Revises:
Create Date: 2025-10-31 01:37:12.541992

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '96e3543c1899'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('avatar', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('preferences', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create download_batches table
    op.create_table(
        'download_batches',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('batch_type', sa.Enum('playlist', 'manual_batch', 'api_batch', name='batch_type'), nullable=False),
        sa.Column('batch_title', sa.String(length=500), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', 'cancelled', name='batch_status'), nullable=False, default='pending'),
        sa.Column('total_videos', sa.Integer(), nullable=False, default=0),
        sa.Column('completed_videos', sa.Integer(), nullable=False, default=0),
        sa.Column('failed_videos', sa.Integer(), nullable=False, default=0),
        sa.Column('overall_progress', sa.Float(), nullable=False, default=0.0),
        sa.Column('playlist_id', sa.String(length=200), nullable=True),
        sa.Column('playlist_uploader', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('format_spec', sa.String(length=100), nullable=True, default='best'),
        sa.Column('output_directory', sa.Text(), nullable=True),
        sa.Column('celery_task_id', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_download_batches_id'), 'download_batches', ['id'], unique=False)
    op.create_index(op.f('ix_download_batches_user_id'), 'download_batches', ['user_id'], unique=False)
    op.create_index(op.f('ix_download_batches_status'), 'download_batches', ['status'], unique=False)
    op.create_index(op.f('ix_download_batches_created_at'), 'download_batches', ['created_at'], unique=False)

    # Create downloads table
    op.create_table(
        'downloads',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'downloading', 'processing', 'completed', 'failed', 'cancelled', name='download_status'), nullable=False, default='pending'),
        sa.Column('progress', sa.Float(), nullable=True, default=0.0),
        sa.Column('downloaded_bytes', sa.Integer(), nullable=True),
        sa.Column('total_bytes', sa.Integer(), nullable=True),
        sa.Column('download_speed', sa.Float(), nullable=True),
        sa.Column('eta', sa.Float(), nullable=True),
        sa.Column('format_spec', sa.String(), nullable=True, default='best'),
        sa.Column('output_path', sa.String(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('video_id', sa.String(), nullable=True),
        sa.Column('extractor', sa.String(), nullable=True),
        sa.Column('thumbnail_url', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('batch_id', sa.String(), nullable=True),
        sa.Column('batch_position', sa.Integer(), nullable=True),
        sa.Column('batch_video_id', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['batch_id'], ['download_batches.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_downloads_id'), 'downloads', ['id'], unique=False)
    op.create_index(op.f('ix_downloads_url'), 'downloads', ['url'], unique=False)
    op.create_index(op.f('ix_downloads_video_id'), 'downloads', ['video_id'], unique=False)
    op.create_index(op.f('ix_downloads_batch_id'), 'downloads', ['batch_id'], unique=False)

    # Create batch_videos table
    op.create_table(
        'batch_videos',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('batch_id', sa.String(), nullable=False),
        sa.Column('video_url', sa.Text(), nullable=False),
        sa.Column('video_id', sa.String(length=200), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('uploader', sa.String(length=200), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=True),
        sa.Column('upload_date', sa.String(length=8), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'queued', 'downloading', 'completed', 'failed', 'skipped', name='batch_video_status'), nullable=False, default='pending'),
        sa.Column('download_id', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['download_batches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['download_id'], ['downloads.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_batch_videos_id'), 'batch_videos', ['id'], unique=False)
    op.create_index(op.f('ix_batch_videos_batch_id'), 'batch_videos', ['batch_id'], unique=False)
    op.create_index(op.f('ix_batch_videos_status'), 'batch_videos', ['status'], unique=False)
    op.create_index(op.f('ix_batch_videos_download_id'), 'batch_videos', ['download_id'], unique=False)

    # Create download_files table
    op.create_table(
        'download_files',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('download_id', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('filepath', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('format_id', sa.String(), nullable=True),
        sa.Column('resolution', sa.String(), nullable=True),
        sa.Column('codec', sa.String(), nullable=True),
        sa.Column('bitrate', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['download_id'], ['downloads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_download_files_id'), 'download_files', ['id'], unique=False)

    # Create webhooks table
    op.create_table(
        'webhooks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('secret', sa.String(), nullable=True),
        sa.Column('events', sa.JSON(), nullable=False),
        sa.Column('headers', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_triggered', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhooks_id'), 'webhooks', ['id'], unique=False)

    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=False),
        sa.Column('rate_limit', sa.Integer(), nullable=False, default=60),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )
    op.create_index(op.f('ix_api_keys_id'), 'api_keys', ['id'], unique=False)
    op.create_index(op.f('ix_api_keys_user_id'), 'api_keys', ['user_id'], unique=False)

    # Create download_history table
    op.create_table(
        'download_history',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('download_id', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('completed', 'failed', 'cancelled', name='history_status'), nullable=False),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('video_id', sa.String(), nullable=True),
        sa.Column('extractor', sa.String(), nullable=True),
        sa.Column('format_used', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_download_history_id'), 'download_history', ['id'], unique=False)
    op.create_index(op.f('ix_download_history_download_id'), 'download_history', ['download_id'], unique=False)

    # Create token_blacklist table
    op.create_table(
        'token_blacklist',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('token_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('reason', sa.String(), nullable=False, default='logout'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_id')
    )
    op.create_index(op.f('ix_token_blacklist_id'), 'token_blacklist', ['id'], unique=False)
    op.create_index(op.f('ix_token_blacklist_token_id'), 'token_blacklist', ['token_id'], unique=True)
    op.create_index(op.f('ix_token_blacklist_user_id'), 'token_blacklist', ['user_id'], unique=False)
    op.create_index(op.f('ix_token_blacklist_expires_at'), 'token_blacklist', ['expires_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('token_blacklist')
    op.drop_table('download_history')
    op.drop_table('api_keys')
    op.drop_table('webhooks')
    op.drop_table('download_files')
    op.drop_table('batch_videos')
    op.drop_table('downloads')
    op.drop_table('download_batches')
    op.drop_table('users')
