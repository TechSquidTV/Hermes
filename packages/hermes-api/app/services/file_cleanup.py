"""Shared cleanup eligibility for manual and scheduled maintenance."""

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Download


async def active_download_prefixes(session: AsyncSession) -> tuple[str, ...]:
    ids = await session.scalars(
        select(Download.id).where(
            Download.status.in_(["pending", "downloading", "processing"])
        )
    )
    return tuple(f"{download_id}_" for download_id in ids)


def cleanup_candidates(
    directory: Path, max_age_hours: int, active_prefixes: tuple[str, ...]
) -> Iterator[Path]:
    """Exclude fresh files, active task outputs and symlinks from deletion."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    root = directory.resolve()
    for path in directory.rglob("*"):
        if (
            path.is_symlink()
            or not path.is_file()
            or path.name.startswith(active_prefixes)
        ):
            continue
        if not path.resolve().is_relative_to(root):
            continue
        if datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc) < cutoff:
            yield path
