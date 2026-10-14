"""Filesystem checks shared by managed-file registration and serving."""

from pathlib import Path

from app.core.config import settings


def resolve_download_path(path: str) -> Path:
    """Resolve symlinks and reject paths outside the configured downloads root."""
    downloads_root = Path(settings.download_dir).resolve()
    requested_path = Path(path).resolve()
    requested_path.relative_to(downloads_root)
    return requested_path


def relative_download_path(path: str | None) -> str | None:
    """Expose a root-relative media path without leaking server directories."""
    if not path:
        return None
    try:
        root = Path(settings.download_dir).resolve()
        return resolve_download_path(path).relative_to(root).as_posix()
    except (OSError, ValueError, RuntimeError):
        return None
