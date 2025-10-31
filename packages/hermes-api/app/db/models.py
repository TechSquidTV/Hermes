"""
Database models for the Hermes API.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Download(Base):
    """Model for tracking download jobs."""

    __tablename__ = "downloads"

    id = Column(String, primary_key=True, index=True)
    url = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    status = Column(
        Enum(
            "pending",
            "downloading",
            "processing",
            "completed",
            "failed",
            "cancelled",
            name="download_status",
        ),
        default="pending",
        nullable=False,
    )
    progress = Column(Float, default=0.0)  # 0.0 to 100.0

    # Progress tracking fields
    downloaded_bytes = Column(Integer, nullable=True)  # Bytes downloaded so far
    total_bytes = Column(Integer, nullable=True)  # Total bytes to download
    download_speed = Column(Float, nullable=True)  # Download speed in bytes per second
    eta = Column(Float, nullable=True)  # Estimated time remaining in seconds

    format_spec = Column(String, default="best")
    output_path = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)  # Final file size in bytes
    duration = Column(Float, nullable=True)  # Video duration in seconds
    error_message = Column(Text, nullable=True)

    # Metadata
    video_id = Column(String, nullable=True, index=True)
    extractor = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    # Batch relationship
    batch_id = Column(
        String,
        ForeignKey("download_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    batch_position = Column(Integer, nullable=True)
    batch_video_id = Column(String(200), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    files = relationship(
        "DownloadFile", back_populates="download", cascade="all, delete-orphan"
    )
    batch = relationship("DownloadBatch", back_populates="downloads")

    def __repr__(self):
        return f"<Download(id={self.id}, url={self.url[:50]}..., status={self.status})>"


class DownloadFile(Base):
    """Model for tracking downloaded files."""

    __tablename__ = "download_files"

    id = Column(String, primary_key=True, index=True)
    download_id = Column(String, ForeignKey("downloads.id"), nullable=False)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_type = Column(String, nullable=False)  # video, audio, subtitle, thumbnail

    # Metadata
    format_id = Column(String, nullable=True)
    resolution = Column(String, nullable=True)
    codec = Column(String, nullable=True)
    bitrate = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    download = relationship("Download", back_populates="files")

    def __repr__(self):
        return f"<DownloadFile(id={self.id}, filename={self.filename}, type={self.file_type})>"


class DownloadBatch(Base):
    """Model for batch/playlist download operations."""

    __tablename__ = "download_batches"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Batch metadata
    batch_type = Column(
        Enum("playlist", "manual_batch", "api_batch", name="batch_type"), nullable=False
    )
    batch_title = Column(String(500), nullable=True)
    source_url = Column(Text, nullable=True)

    # Status tracking
    status = Column(
        Enum(
            "pending",
            "processing",
            "completed",
            "failed",
            "cancelled",
            name="batch_status",
        ),
        default="pending",
        nullable=False,
        index=True,
    )

    # Counts
    total_videos = Column(Integer, default=0, nullable=False)
    completed_videos = Column(Integer, default=0, nullable=False)
    failed_videos = Column(Integer, default=0, nullable=False)

    # Progress
    overall_progress = Column(Float, default=0.0)  # 0.0 to 100.0

    # Metadata from playlist
    playlist_id = Column(String(200), nullable=True)
    playlist_uploader = Column(String(200), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Settings applied to all downloads in batch
    format_spec = Column(String(100), default="best")
    output_directory = Column(Text, nullable=True)

    # Celery task tracking
    celery_task_id = Column(String(255), nullable=True)

    # Relationships
    videos = relationship(
        "BatchVideo", back_populates="batch", cascade="all, delete-orphan"
    )
    downloads = relationship("Download", back_populates="batch")

    def __repr__(self):
        return f"<DownloadBatch(id={self.id}, title={self.batch_title}, status={self.status})>"


class BatchVideo(Base):
    """Model for individual videos within a batch."""

    __tablename__ = "batch_videos"

    id = Column(String, primary_key=True, index=True)
    batch_id = Column(
        String,
        ForeignKey("download_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Video info from playlist extraction
    video_url = Column(Text, nullable=False)
    video_id = Column(String(200), nullable=True)
    title = Column(String(500), nullable=True)
    duration = Column(Integer, nullable=True)  # seconds
    thumbnail_url = Column(Text, nullable=True)
    uploader = Column(String(200), nullable=True)
    view_count = Column(Integer, nullable=True)
    upload_date = Column(String(8), nullable=True)  # YYYYMMDD

    # Position in playlist
    position = Column(Integer, nullable=False)

    # Status
    status = Column(
        Enum(
            "pending",
            "queued",
            "downloading",
            "completed",
            "failed",
            "skipped",
            name="batch_video_status",
        ),
        default="pending",
        nullable=False,
        index=True,
    )
    download_id = Column(
        String,
        ForeignKey("downloads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    batch = relationship("DownloadBatch", back_populates="videos")
    download = relationship("Download")

    def __repr__(self):
        return f"<BatchVideo(id={self.id}, title={self.title}, position={self.position}, status={self.status})>"


class Webhook(Base):
    """Model for webhook configurations."""

    __tablename__ = "webhooks"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    secret = Column(String, nullable=True)  # For signature verification
    events = Column(JSON, nullable=False)  # List of events to subscribe to
    headers = Column(JSON, nullable=True)  # Custom headers
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_triggered = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Webhook(id={self.id}, name={self.name}, url={self.url})>"


class ApiKey(Base):
    """Model for API key management."""

    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)  # Associate with user
    name = Column(String, nullable=False)
    key_hash = Column(String, nullable=False, unique=True)  # Hashed API key
    permissions = Column(JSON, nullable=False, default=list)  # List of permissions
    rate_limit = Column(Integer, default=60, nullable=False)  # Requests per minute
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_used = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<ApiKey(id={self.id}, name={self.name}, active={self.is_active})>"


class User(Base):
    """Model for user accounts."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(
        String, unique=True, index=True, nullable=False
    )  # Made required and unique
    password_hash = Column(String, nullable=False)
    avatar = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    preferences = Column(
        JSON, nullable=True, default=dict
    )  # User preferences (theme, etc.)

    # Timestamps
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_login = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


class DownloadHistory(Base):
    """Model for tracking download history and analytics."""

    __tablename__ = "download_history"

    id = Column(String, primary_key=True, index=True)
    download_id = Column(String, nullable=False, index=True)
    url = Column(String, nullable=False)
    status = Column(
        Enum("completed", "failed", "cancelled", name="history_status"), nullable=False
    )
    duration = Column(Float, nullable=True)  # Download duration in seconds
    file_size = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Metadata
    video_id = Column(String, nullable=True)
    extractor = Column(String, nullable=True)
    format_used = Column(String, nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<DownloadHistory(id={self.id}, status={self.status}, duration={self.duration}s)>"


class TokenBlacklist(Base):
    """Model for tracking blacklisted JWT tokens (for logout/revocation)."""

    __tablename__ = "token_blacklist"

    id = Column(String, primary_key=True, index=True)
    token_id = Column(String, unique=True, index=True, nullable=False)  # JWT ID (jti)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    expires_at = Column(
        DateTime, nullable=False, index=True
    )  # When the token naturally expires
    reason = Column(
        String, default="logout", nullable=False
    )  # logout, revoked, security, etc.

    # Timestamps
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self):
        return f"<TokenBlacklist(id={self.id}, token_id={self.token_id[:8]}..., reason={self.reason})>"
