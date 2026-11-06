"""
Database models for the Hermes API.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import JsonValue
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.media import DEFAULT_FORMAT_SPEC


class Download(Base):
    """Model for tracking download jobs."""

    __tablename__ = "downloads"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
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
    progress: Mapped[float | None] = mapped_column(Float, default=0.0, nullable=True)

    # Progress tracking fields
    downloaded_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    download_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    eta: Mapped[float | None] = mapped_column(Float, nullable=True)

    format_spec: Mapped[str | None] = mapped_column(
        String, default=DEFAULT_FORMAT_SPEC, nullable=True
    )
    output_path: Mapped[str | None] = mapped_column(String, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    video_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    extractor: Mapped[str | None] = mapped_column(String, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Batch relationship
    batch_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("download_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    batch_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    batch_video_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    files: Mapped[list[DownloadFile]] = relationship(
        "DownloadFile", back_populates="download", cascade="all, delete-orphan"
    )
    batch: Mapped[DownloadBatch | None] = relationship(
        "DownloadBatch", back_populates="downloads"
    )

    def __repr__(self) -> str:
        return f"<Download(id={self.id}, url={self.url[:50]}..., status={self.status})>"


class DownloadFile(Base):
    """Model for tracking downloaded files."""

    __tablename__ = "download_files"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    download_id: Mapped[str] = mapped_column(
        String, ForeignKey("downloads.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    filepath: Mapped[str] = mapped_column(String, nullable=False, index=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)

    # Metadata
    format_id: Mapped[str | None] = mapped_column(String, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String, nullable=True)
    codec: Mapped[str | None] = mapped_column(String, nullable=True)
    bitrate: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    download: Mapped[Download] = relationship("Download", back_populates="files")

    def __repr__(self) -> str:
        return f"<DownloadFile(id={self.id}, filename={self.filename}, type={self.file_type})>"


class DownloadBatch(Base):
    """Model for batch/playlist download operations."""

    __tablename__ = "download_batches"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Batch metadata
    batch_type: Mapped[str] = mapped_column(
        Enum("playlist", "manual_batch", "api_batch", name="batch_type"), nullable=False
    )
    batch_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
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
    total_videos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_videos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_videos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Progress
    overall_progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Metadata from playlist
    playlist_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    playlist_uploader: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Settings applied to all downloads in batch
    format_spec: Mapped[str | None] = mapped_column(
        String(100), default=DEFAULT_FORMAT_SPEC, nullable=True
    )
    output_directory: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Celery task tracking
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    videos: Mapped[list[BatchVideo]] = relationship(
        "BatchVideo", back_populates="batch", cascade="all, delete-orphan"
    )
    downloads: Mapped[list[Download]] = relationship("Download", back_populates="batch")

    def __repr__(self) -> str:
        return f"<DownloadBatch(id={self.id}, title={self.batch_title}, status={self.status})>"


class BatchVideo(Base):
    """Model for individual videos within a batch."""

    __tablename__ = "batch_videos"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    batch_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("download_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Video info from playlist extraction
    video_url: Mapped[str] = mapped_column(Text, nullable=False)
    video_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploader: Mapped[str | None] = mapped_column(String(200), nullable=True)
    view_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upload_date: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # Position in playlist
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
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
    download_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("downloads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    batch: Mapped[DownloadBatch] = relationship(
        "DownloadBatch", back_populates="videos"
    )
    download: Mapped[Download | None] = relationship("Download")

    def __repr__(self) -> str:
        return f"<BatchVideo(id={self.id}, title={self.title}, position={self.position}, status={self.status})>"


class Webhook(Base):
    """Model for webhook configurations."""

    __tablename__ = "webhooks"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    secret: Mapped[str | None] = mapped_column(String, nullable=True)
    events: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    headers: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_triggered: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Webhook(id={self.id}, name={self.name}, url={self.url})>"


class ApiKey(Base):
    """Model for API key management."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    key_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    rate_limit: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_used: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, name={self.name}, active={self.is_active})>"


class User(Base):
    """Model for user accounts."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    avatar: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    preferences: Mapped[dict[str, JsonValue] | None] = mapped_column(
        JSON, nullable=True, default=dict
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


class DownloadHistory(Base):
    """Model for tracking download history and analytics."""

    __tablename__ = "download_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    download_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("completed", "failed", "cancelled", name="history_status"), nullable=False
    )
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    video_id: Mapped[str | None] = mapped_column(String, nullable=True)
    extractor: Mapped[str | None] = mapped_column(String, nullable=True)
    format_used: Mapped[str | None] = mapped_column(String, nullable=True)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"<DownloadHistory(id={self.id}, status={self.status}, duration={self.duration}s)>"


class TokenBlacklist(Base):
    """Model for tracking blacklisted JWT tokens (for logout/revocation)."""

    __tablename__ = "token_blacklist"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    token_id: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String, default="logout", nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<TokenBlacklist(id={self.id}, token_id={self.token_id[:8]}..., reason={self.reason})>"


class SystemSettings(Base):
    """Model for system-wide settings (singleton table with ID=1)."""

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    allow_public_signup: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    updated_by_user_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<SystemSettings(id={self.id}, allow_public_signup={self.allow_public_signup})>"
