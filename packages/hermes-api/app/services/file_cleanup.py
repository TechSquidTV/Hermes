"""Shared cleanup eligibility for manual and scheduled maintenance."""

from collections.abc import AsyncIterator, Collection, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import Download

logger = get_logger(__name__)


def download_artifacts(download_ids: Collection[str]) -> dict[str, list[Path]]:
    """Find regular task-prefixed outputs, without following symlinks."""
    artifacts: dict[str, list[Path]] = {download_id: [] for download_id in download_ids}
    if not artifacts:
        return artifacts
    roots = {Path(settings.download_dir).resolve(), Path(settings.temp_dir).resolve()}
    prefixes = tuple(f"{download_id}_" for download_id in download_ids)
    seen: set[Path] = set()
    for root in roots:
        for path in root.rglob("*"):
            if not path.name.startswith(prefixes):
                continue
            if path.is_symlink() or not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen or not resolved.is_relative_to(root):
                continue
            seen.add(resolved)
            owner = next(
                download_id
                for download_id in download_ids
                if path.name.startswith(f"{download_id}_")
            )
            artifacts[owner].append(path)
    return artifacts


@dataclass(frozen=True)
class ArtifactCleanup:
    files: int
    bytes_freed: int
    complete: bool
    failed: bool = False


def remove_download_artifacts(
    download_id: str,
    *,
    limit: int | None = None,
    dry_run: bool = False,
    excluded_paths: Collection[str] = (),
    paths: Collection[Path] | None = None,
) -> ArtifactCleanup:
    """Preserve the parent until all of its task artifacts can be removed."""
    files = bytes_freed = 0
    candidates = (
        download_artifacts({download_id})[download_id] if paths is None else paths
    )
    for path in candidates:
        if str(path.resolve()) in excluded_paths:
            continue
        if limit is not None and files >= limit:
            return ArtifactCleanup(files, bytes_freed, False)
        try:
            size = path.stat().st_size
            if not dry_run:
                path.unlink()
        except FileNotFoundError:
            continue
        except OSError:
            logger.exception(
                "Failed to remove download artifact", download_id=download_id
            )
            return ArtifactCleanup(files, bytes_freed, False, True)
        files += 1
        bytes_freed += size
    return ArtifactCleanup(files, bytes_freed, True)


async def temporary_cleanup_candidates(
    session: AsyncSession, max_age_hours: int
) -> AsyncIterator[Path]:
    """Include aged failed/cancelled outputs stored outside the temp directory."""
    prefixes = await active_download_prefixes(session)
    terminal_ids = set(
        await session.scalars(
            select(Download.id).where(Download.status.in_(["failed", "cancelled"]))
        )
    )
    seen: set[Path] = set()
    temp = Path(settings.temp_dir).resolve()
    downloads = Path(settings.download_dir).resolve()
    terminal_prefixes = tuple(f"{download_id}_" for download_id in terminal_ids)
    for path in cleanup_candidates(temp, max_age_hours, prefixes):
        if path.resolve().is_relative_to(downloads) and not path.name.startswith(
            terminal_prefixes
        ):
            continue
        seen.add(path.resolve())
        yield path
    cutoff = datetime.now(timezone.utc).timestamp() - max_age_hours * 3600
    for paths in download_artifacts(terminal_ids).values():
        for path in paths:
            if path.resolve() not in seen and path.stat().st_mtime < cutoff:
                yield path


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
