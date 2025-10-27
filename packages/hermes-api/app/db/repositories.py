"""
Repository layer for database operations.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import async_session_maker
from app.db.models import (
    ApiKey,
    Download,
    DownloadFile,
    DownloadHistory,
    TokenBlacklist,
    User,
    Webhook,
)


class BaseRepository:
    """Base repository with common database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def commit(self):
        """Commit the current transaction."""
        await self.session.commit()

    async def rollback(self):
        """Rollback the current transaction."""
        await self.session.rollback()


class DownloadRepository(BaseRepository):
    """Repository for Download model operations."""

    async def create(
        self, url: str, format_spec: str = "best", status: str = "pending", **kwargs
    ) -> Download:
        """Create a new download record."""
        download_id = str(uuid.uuid4())

        download = Download(
            id=download_id,
            url=url,
            format_spec=format_spec,
            status=status,
            created_at=datetime.now(timezone.utc),
            **kwargs,
        )

        self.session.add(download)
        await self.commit()
        return download

    async def get_by_id(self, download_id: str) -> Optional[Download]:
        """Get download by ID with related files."""
        result = await self.session.execute(
            select(Download)
            .options(selectinload(Download.files))
            .where(Download.id == download_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        download_id: str,
        status: str,
        progress: float = None,
        error_message: str = None,
        **kwargs,
    ) -> Optional[Download]:
        """Update download status and progress."""
        download = await self.get_by_id(download_id)
        if not download:
            return None

        download.status = status
        download.progress = progress if progress is not None else download.progress

        if status == "downloading" and not download.started_at:
            download.started_at = datetime.now(timezone.utc)
        elif (
            status in ["completed", "failed", "cancelled"] and not download.completed_at
        ):
            download.completed_at = datetime.now(timezone.utc)

        if error_message:
            download.error_message = error_message

        # Update other fields
        for key, value in kwargs.items():
            if hasattr(download, key):
                setattr(download, key, value)

        await self.commit()
        return download

    async def get_by_status(self, status: str, limit: int = 50) -> List[Download]:
        """Get downloads by status."""
        result = await self.session.execute(
            select(Download)
            .where(Download.status == status)
            .order_by(desc(Download.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_all(self, limit: int = 1000) -> List[Download]:
        """Get all downloads."""
        result = await self.session.execute(
            select(Download).order_by(desc(Download.created_at)).limit(limit)
        )
        return result.scalars().all()

    async def get_pending_downloads(self, limit: int = 10) -> List[Download]:
        """Get pending downloads for processing."""
        return await self.get_by_status("pending", limit)

    async def delete(self, download_id: str) -> bool:
        """Delete a download record by ID."""
        download = await self.get_by_id(download_id)
        if download:
            await self.session.delete(download)
            await self.commit()
            return True
        return False

    async def get_by_batch_id(self, batch_id: str) -> List[Dict[str, Any]]:
        """
        Get all downloads for a specific batch.

        Args:
            batch_id: Batch UUID

        Returns:
            List of download dictionaries
        """
        result = await self.session.execute(
            select(Download)
            .where(Download.batch_id == batch_id)
            .order_by(Download.batch_position)
        )
        downloads = result.scalars().all()

        return [
            {
                "id": download.id,
                "url": download.url,
                "title": download.title,
                "status": download.status,
                "progress": download.progress,
                "batch_id": download.batch_id,
                "batch_position": download.batch_position,
                "batch_video_id": download.batch_video_id,
                "created_at": download.created_at,
                "started_at": download.started_at,
                "completed_at": download.completed_at,
            }
            for download in downloads
        ]


class DownloadFileRepository(BaseRepository):
    """Repository for DownloadFile model operations."""

    async def create(
        self,
        download_id: str,
        filename: str,
        filepath: str,
        file_size: int,
        file_type: str,
        **kwargs,
    ) -> DownloadFile:
        """Create a new download file record."""
        file_id = str(uuid.uuid4())

        download_file = DownloadFile(
            id=file_id,
            download_id=download_id,
            filename=filename,
            filepath=filepath,
            file_size=file_size,
            file_type=file_type,
            created_at=datetime.now(timezone.utc),
            **kwargs,
        )

        self.session.add(download_file)
        await self.commit()
        return download_file

    async def get_by_download_id(self, download_id: str) -> List[DownloadFile]:
        """Get all files for a download."""
        result = await self.session.execute(
            select(DownloadFile)
            .where(DownloadFile.download_id == download_id)
            .order_by(DownloadFile.created_at)
        )
        return result.scalars().all()

    async def delete_by_download_id(self, download_id: str) -> int:
        """Delete all files for a download. Returns count of deleted files."""
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(DownloadFile).where(DownloadFile.download_id == download_id)
        )
        await self.commit()
        return result.rowcount


class WebhookRepository(BaseRepository):
    """Repository for Webhook model operations."""

    async def create(
        self,
        name: str,
        url: str,
        events: List[str],
        secret: str = None,
        headers: Dict[str, str] = None,
    ) -> Webhook:
        """Create a new webhook."""
        webhook_id = str(uuid.uuid4())

        webhook = Webhook(
            id=webhook_id,
            name=name,
            url=url,
            events=events,
            secret=secret,
            headers=headers or {},
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(webhook)
        await self.commit()
        return webhook

    async def get_active_webhooks(self) -> List[Webhook]:
        """Get all active webhooks."""
        result = await self.session.execute(
            select(Webhook).where(Webhook.is_active).order_by(Webhook.created_at)
        )
        return result.scalars().all()

    async def get_webhooks_for_event(self, event: str) -> List[Webhook]:
        """Get webhooks that subscribe to a specific event."""
        result = await self.session.execute(
            select(Webhook).where(
                and_(Webhook.is_active, Webhook.events.contains([event]))
            )
        )
        return result.scalars().all()

    async def update_last_triggered(self, webhook_id: str) -> Optional[Webhook]:
        """Update webhook's last triggered timestamp."""
        webhook = await self.get_by_id(webhook_id)
        if webhook:
            webhook.last_triggered = datetime.now(timezone.utc)
            await self.commit()
        return webhook

    async def get_by_id(self, webhook_id: str) -> Optional[Webhook]:
        """Get webhook by ID."""
        result = await self.session.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        return result.scalar_one_or_none()


class ApiKeyRepository(BaseRepository):
    """Repository for ApiKey model operations."""

    async def create(
        self,
        user_id: str,
        name: str,
        key_hash: str,
        permissions: List[str] = None,
        rate_limit: int = 60,
    ) -> ApiKey:
        """Create a new API key."""
        key_id = str(uuid.uuid4())

        api_key = ApiKey(
            id=key_id,
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            permissions=permissions or [],
            rate_limit=rate_limit,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(api_key)
        # Don't commit here - let FastAPI handle the transaction
        # await self.commit()
        return api_key

    async def get_by_key_hash(self, key_hash: str) -> Optional[ApiKey]:
        """Get API key by hashed key."""
        result = await self.session.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def update_last_used(self, api_key_id: str) -> Optional[ApiKey]:
        """Update API key's last used timestamp."""
        api_key = await self.get_by_id(api_key_id)
        if api_key:
            api_key.last_used = datetime.now(timezone.utc)
            await self.commit()
        return api_key

    async def get_by_id(self, api_key_id: str) -> Optional[ApiKey]:
        """Get API key by ID."""
        result = await self.session.execute(
            select(ApiKey).where(ApiKey.id == api_key_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, user_id: str = None) -> list[ApiKey]:
        """Get all API keys, optionally filtered by user."""
        query = select(ApiKey)
        if user_id:
            query = query.where(ApiKey.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_user_id(self, user_id: str) -> list[ApiKey]:
        """Get all API keys for a specific user."""
        return await self.get_all(user_id=user_id)

    async def update(self, api_key: ApiKey) -> ApiKey:
        """Update API key record."""
        self.session.add(api_key)
        await self.commit()
        return api_key


class UserRepository(BaseRepository):
    """Repository for User model operations."""

    async def create(
        self, username: str, password_hash: str, email: str, avatar: str = None
    ) -> User:
        """Create a new user."""
        user_id = str(uuid.uuid4())

        user = User(
            id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            avatar=avatar,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(user)
        await self.commit()
        return user

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_last_login(self, user_id: str) -> Optional[User]:
        """Update user's last login timestamp."""
        user = await self.get_by_id(user_id)
        if user:
            user.last_login = datetime.now(timezone.utc)
            await self.commit()
        return user

    async def update(self, user: User) -> User:
        """Update user record."""
        self.session.add(user)
        await self.commit()
        return user


class DownloadHistoryRepository(BaseRepository):
    """Repository for DownloadHistory model operations."""

    async def create(
        self,
        download_id: str,
        url: str,
        status: str,
        started_at: datetime,
        completed_at: datetime,
        **kwargs,
    ) -> DownloadHistory:
        """Create a new history record."""
        history_id = str(uuid.uuid4())

        # Calculate duration
        duration = (completed_at - started_at).total_seconds() if completed_at else None

        history = DownloadHistory(
            id=history_id,
            download_id=download_id,
            url=url,
            status=status,
            duration=duration,
            started_at=started_at,
            completed_at=completed_at,
            **kwargs,
        )

        self.session.add(history)
        await self.commit()
        return history

    async def get_by_date_range(
        self, start_date: datetime, end_date: datetime, limit: int = 100
    ) -> List[DownloadHistory]:
        """Get history records within date range."""
        result = await self.session.execute(
            select(DownloadHistory)
            .where(
                and_(
                    DownloadHistory.started_at >= start_date,
                    DownloadHistory.started_at <= end_date,
                )
            )
            .order_by(desc(DownloadHistory.started_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get download statistics for the last N days."""
        cutoff_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )  # Start of today minus N days

        # This is a simplified query - in production you'd want more complex aggregation
        result = await self.session.execute(
            select(DownloadHistory).where(DownloadHistory.started_at >= cutoff_date)
        )

        records = result.scalars().all()

        total_downloads = len(records)
        completed = sum(1 for r in records if r.status == "completed")
        failed = sum(1 for r in records if r.status == "failed")

        return {
            "total_downloads": total_downloads,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / total_downloads if total_downloads > 0 else 0,
            "period_days": days,
        }


class TokenBlacklistRepository(BaseRepository):
    """Repository for TokenBlacklist model operations."""

    async def add_to_blacklist(
        self, token_id: str, user_id: str, expires_at: datetime, reason: str = "logout"
    ) -> TokenBlacklist:
        """Add a token to the blacklist."""
        blacklist_id = str(uuid.uuid4())

        blacklist_entry = TokenBlacklist(
            id=blacklist_id,
            token_id=token_id,
            user_id=user_id,
            expires_at=expires_at,
            reason=reason,
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(blacklist_entry)
        await self.commit()
        return blacklist_entry

    async def is_blacklisted(self, token_id: str) -> bool:
        """Check if a token ID is blacklisted."""
        result = await self.session.execute(
            select(TokenBlacklist).where(TokenBlacklist.token_id == token_id)
        )
        return result.scalar_one_or_none() is not None

    async def get_by_token_id(self, token_id: str) -> Optional[TokenBlacklist]:
        """Get blacklist entry by token ID."""
        result = await self.session.execute(
            select(TokenBlacklist).where(TokenBlacklist.token_id == token_id)
        )
        return result.scalar_one_or_none()

    async def cleanup_expired(self) -> int:
        """Remove expired tokens from blacklist. Returns number of deleted entries."""
        from sqlalchemy import delete

        now = datetime.now(timezone.utc)

        # Get expired entries
        result = await self.session.execute(
            select(TokenBlacklist).where(TokenBlacklist.expires_at < now)
        )
        expired_entries = result.scalars().all()
        count = len(expired_entries)

        # Delete expired entries
        await self.session.execute(
            delete(TokenBlacklist).where(TokenBlacklist.expires_at < now)
        )
        await self.commit()

        return count

    async def get_user_blacklisted_tokens(self, user_id: str) -> List[TokenBlacklist]:
        """Get all blacklisted tokens for a user."""
        result = await self.session.execute(
            select(TokenBlacklist)
            .where(TokenBlacklist.user_id == user_id)
            .order_by(desc(TokenBlacklist.created_at))
        )
        return result.scalars().all()


class BatchRepository(BaseRepository):
    """Repository for DownloadBatch and BatchVideo model operations."""

    async def create_batch(
        self,
        user_id: str,
        batch_type: str,
        total_videos: int,
        batch_title: Optional[str] = None,
        source_url: Optional[str] = None,
        format_spec: str = "best",
        output_directory: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Create a new batch record.

        Args:
            user_id: User creating the batch
            batch_type: Type of batch ('playlist', 'manual_batch', 'api_batch')
            total_videos: Number of videos in the batch
            batch_title: Optional title
            source_url: Original URL if from playlist
            format_spec: yt-dlp format specification
            output_directory: Optional custom output directory
            **kwargs: Additional fields (playlist_id, playlist_uploader, etc.)

        Returns:
            batch_id: UUID of created batch
        """
        from app.db.models import DownloadBatch

        batch_id = str(uuid.uuid4())

        batch = DownloadBatch(
            id=batch_id,
            user_id=user_id,
            batch_type=batch_type,
            batch_title=batch_title,
            source_url=source_url,
            total_videos=total_videos,
            format_spec=format_spec,
            output_directory=output_directory,
            status="pending",
            completed_videos=0,
            failed_videos=0,
            overall_progress=0.0,
            created_at=datetime.now(timezone.utc),
            **kwargs,
        )

        self.session.add(batch)
        await self.commit()
        return batch_id

    async def get_batch_by_id(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get batch by ID.

        Args:
            batch_id: Batch UUID

        Returns:
            Dictionary with batch data or None if not found
        """
        from app.db.models import DownloadBatch

        result = await self.session.execute(
            select(DownloadBatch)
            .options(selectinload(DownloadBatch.videos))
            .where(DownloadBatch.id == batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            return None

        return {
            "id": batch.id,
            "user_id": batch.user_id,
            "batch_type": batch.batch_type,
            "batch_title": batch.batch_title,
            "source_url": batch.source_url,
            "status": batch.status,
            "total_videos": batch.total_videos,
            "completed_videos": batch.completed_videos,
            "failed_videos": batch.failed_videos,
            "overall_progress": batch.overall_progress,
            "playlist_id": batch.playlist_id,
            "playlist_uploader": batch.playlist_uploader,
            "format_spec": batch.format_spec,
            "output_directory": batch.output_directory,
            "celery_task_id": batch.celery_task_id,
            "created_at": batch.created_at,
            "started_at": batch.started_at,
            "completed_at": batch.completed_at,
        }

    async def get_user_batches(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get all batches for a user.

        Args:
            user_id: User UUID
            status: Optional status filter
            limit: Maximum number of batches to return
            offset: Number of batches to skip

        Returns:
            List of batch dictionaries
        """
        from app.db.models import DownloadBatch

        query = select(DownloadBatch).where(DownloadBatch.user_id == user_id)

        if status:
            query = query.where(DownloadBatch.status == status)

        query = (
            query.order_by(desc(DownloadBatch.created_at)).limit(limit).offset(offset)
        )

        result = await self.session.execute(query)
        batches = result.scalars().all()

        return [
            {
                "id": batch.id,
                "batch_type": batch.batch_type,
                "batch_title": batch.batch_title,
                "source_url": batch.source_url,
                "status": batch.status,
                "total_videos": batch.total_videos,
                "completed_videos": batch.completed_videos,
                "failed_videos": batch.failed_videos,
                "overall_progress": batch.overall_progress,
                "created_at": batch.created_at,
                "started_at": batch.started_at,
                "completed_at": batch.completed_at,
            }
            for batch in batches
        ]

    async def update_batch(self, batch_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Update batch fields.

        Args:
            batch_id: Batch UUID
            **kwargs: Fields to update

        Returns:
            Updated batch dictionary or None if not found
        """
        from app.db.models import DownloadBatch

        result = await self.session.execute(
            select(DownloadBatch).where(DownloadBatch.id == batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            return None

        for key, value in kwargs.items():
            if hasattr(batch, key):
                setattr(batch, key, value)

        await self.commit()

        return await self.get_batch_by_id(batch_id)

    async def create_batch_videos(
        self, batch_id: str, videos: List[Any]  # List[PlaylistVideoInfo]
    ) -> None:
        """
        Create multiple batch_video records.

        Args:
            batch_id: Batch UUID
            videos: List of PlaylistVideoInfo objects
        """
        from app.db.models import BatchVideo

        batch_videos = []
        for i, video in enumerate(videos):
            batch_video = BatchVideo(
                id=str(uuid.uuid4()),
                batch_id=batch_id,
                video_url=video.url if hasattr(video, "url") else video["url"],
                video_id=(
                    video.video_id
                    if hasattr(video, "video_id")
                    else video.get("video_id")
                ),
                title=video.title if hasattr(video, "title") else video.get("title"),
                duration=(
                    video.duration
                    if hasattr(video, "duration")
                    else video.get("duration")
                ),
                thumbnail_url=(
                    video.thumbnail
                    if hasattr(video, "thumbnail")
                    else video.get("thumbnail")
                ),
                uploader=(
                    video.uploader
                    if hasattr(video, "uploader")
                    else video.get("uploader")
                ),
                view_count=(
                    video.view_count
                    if hasattr(video, "view_count")
                    else video.get("view_count")
                ),
                upload_date=(
                    video.upload_date
                    if hasattr(video, "upload_date")
                    else video.get("upload_date")
                ),
                position=i,
                status="pending",
                retry_count=0,
                created_at=datetime.now(timezone.utc),
            )
            batch_videos.append(batch_video)

        self.session.add_all(batch_videos)
        await self.commit()

    async def get_batch_videos(
        self, batch_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all videos in a batch.

        Args:
            batch_id: Batch UUID
            status: Optional status filter

        Returns:
            List of batch_video dictionaries
        """
        from app.db.models import BatchVideo

        query = select(BatchVideo).where(BatchVideo.batch_id == batch_id)

        if status:
            query = query.where(BatchVideo.status == status)

        query = query.order_by(BatchVideo.position)

        result = await self.session.execute(query)
        videos = result.scalars().all()

        return [
            {
                "id": video.id,
                "batch_id": video.batch_id,
                "video_url": video.video_url,
                "video_id": video.video_id,
                "title": video.title,
                "duration": video.duration,
                "thumbnail_url": video.thumbnail_url,
                "uploader": video.uploader,
                "view_count": video.view_count,
                "upload_date": video.upload_date,
                "position": video.position,
                "status": video.status,
                "download_id": video.download_id,
                "error_message": video.error_message,
                "retry_count": video.retry_count,
                "created_at": video.created_at,
            }
            for video in videos
        ]

    async def update_batch_video_status(
        self, batch_video_id: str, status: str, error_message: Optional[str] = None
    ) -> None:
        """
        Update batch_video status.

        Args:
            batch_video_id: BatchVideo UUID
            status: New status
            error_message: Optional error message if status is 'failed'
        """
        from app.db.models import BatchVideo

        result = await self.session.execute(
            select(BatchVideo).where(BatchVideo.id == batch_video_id)
        )
        video = result.scalar_one_or_none()

        if video:
            video.status = status
            if error_message:
                video.error_message = error_message
            await self.commit()

    async def link_download_to_batch_video(
        self, batch_video_id: str, download_id: str
    ) -> None:
        """
        Link a download to its batch_video record.

        Args:
            batch_video_id: BatchVideo UUID
            download_id: Download UUID
        """
        from app.db.models import BatchVideo

        result = await self.session.execute(
            select(BatchVideo).where(BatchVideo.id == batch_video_id)
        )
        video = result.scalar_one_or_none()

        if video:
            video.download_id = download_id
            await self.commit()

    async def get_batch_with_downloads(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get batch with all associated downloads.

        Args:
            batch_id: Batch UUID

        Returns:
            Dictionary with batch and download data
        """
        from app.db.models import DownloadBatch

        result = await self.session.execute(
            select(DownloadBatch)
            .options(
                selectinload(DownloadBatch.videos),
                selectinload(DownloadBatch.downloads),
            )
            .where(DownloadBatch.id == batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            return None

        return {
            "id": batch.id,
            "user_id": batch.user_id,
            "batch_type": batch.batch_type,
            "batch_title": batch.batch_title,
            "source_url": batch.source_url,
            "status": batch.status,
            "total_videos": batch.total_videos,
            "completed_videos": batch.completed_videos,
            "failed_videos": batch.failed_videos,
            "overall_progress": batch.overall_progress,
            "format_spec": batch.format_spec,
            "output_directory": batch.output_directory,
            "created_at": batch.created_at,
            "started_at": batch.started_at,
            "completed_at": batch.completed_at,
            "videos": [
                {
                    "id": video.id,
                    "video_url": video.video_url,
                    "video_id": video.video_id,
                    "title": video.title,
                    "position": video.position,
                    "status": video.status,
                    "download_id": video.download_id,
                }
                for video in batch.videos
            ],
            "downloads": [
                {
                    "id": download.id,
                    "url": download.url,
                    "title": download.title,
                    "status": download.status,
                    "progress": download.progress,
                    "batch_position": download.batch_position,
                }
                for download in batch.downloads
            ],
        }


# Convenience function to get repositories with session
async def get_repositories() -> Dict[str, BaseRepository]:
    """Get all repository instances with a database session."""
    async with async_session_maker() as session:
        return {
            "downloads": DownloadRepository(session),
            "download_files": DownloadFileRepository(session),
            "webhooks": WebhookRepository(session),
            "api_keys": ApiKeyRepository(session),
            "users": UserRepository(session),
            "history": DownloadHistoryRepository(session),
            "token_blacklist": TokenBlacklistRepository(session),
            "batch": BatchRepository(session),
        }
