"""Filesystem checks shared by managed-file registration and serving."""

from pathlib import Path

from app.core.config import settings


def resolve_download_path(path: str) -> Path:
    """Resolve symlinks and reject paths outside the configured downloads root."""
    downloads_root = Path(settings.download_dir).resolve()
    requested_path = Path(path).resolve()
    requested_path.relative_to(downloads_root)
    return requested_path
