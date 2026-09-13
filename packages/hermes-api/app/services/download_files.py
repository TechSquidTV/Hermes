"""Register final download outputs and repair older completed downloads."""

import mimetypes
import stat
import uuid
from pathlib import Path

from sqlalchemy import and_, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Download, DownloadFile
from app.utils.files import resolve_download_path

logger = get_logger(__name__)


async def register_download_file(
    session: AsyncSession, download_id: str, output_path: str
) -> DownloadFile:
    """Upsert a verified output in the caller's transaction, without committing."""
    file_path = resolve_download_path(output_path)
    file_stat = file_path.stat()
    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError("Downloaded path is not a file")

    mime_type, _ = mimetypes.guess_type(file_path.name)
    file_type = "audio" if mime_type and mime_type.startswith("audio/") else "video"

    # A stable primary key makes simultaneous completion/repair retries safe
    # without requiring a schema migration on existing SQLite installations.
    file_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_URL, f"hermes:download-file:{download_id}:{file_path}"
        )
    )
    existing_files = await session.scalars(
        select(DownloadFile).where(DownloadFile.download_id == download_id)
    )
    for existing_file in existing_files:
        try:
            if Path(existing_file.filepath).resolve() == file_path:
                file_id = existing_file.id
                break
        except (OSError, ValueError, RuntimeError):
            continue

    metadata = {
        "filename": file_path.name,
        "filepath": str(file_path),
        "file_size": file_stat.st_size,
        "file_type": file_type,
    }
    statement = (
        insert(DownloadFile)
        .values(id=file_id, download_id=download_id, **metadata)
        .on_conflict_do_update(index_elements=[DownloadFile.id], set_=metadata)
        .returning(DownloadFile)
    )
    return (
        await session.scalars(statement, execution_options={"populate_existing": True})
    ).one()


async def backfill_download_files(session: AsyncSession) -> int:
    """Repair missing final-file records in bounded batches, verifying every path."""
    repaired = 0
    last_id = ""
    while True:
        downloads = (
            await session.scalars(
                select(Download)
                .outerjoin(
                    DownloadFile,
                    and_(
                        DownloadFile.download_id == Download.id,
                        DownloadFile.filepath == Download.output_path,
                    ),
                )
                .where(
                    Download.status == "completed",
                    Download.output_path.is_not(None),
                    DownloadFile.id.is_(None),
                    Download.id > last_id,
                )
                .order_by(Download.id)
                .limit(100)
            )
        ).all()
        if not downloads:
            return repaired

        for download in downloads:
            try:
                file_record = await register_download_file(
                    session, download.id, download.output_path
                )
            except (OSError, ValueError, RuntimeError) as error:
                logger.warning(
                    "Skipping unavailable or unsafe completed download",
                    download_id=download.id,
                    error=str(error),
                )
                continue
            download.output_path = file_record.filepath
            download.file_size = file_record.file_size
            repaired += 1

        last_id = downloads[-1].id
        await session.commit()
