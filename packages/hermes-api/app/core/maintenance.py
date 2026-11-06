"""Shared, persistent admission gate during a managed release upgrade."""

from pathlib import Path

MAINTENANCE_FILE = Path(__file__).resolve().parents[2] / "data" / ".upgrade-maintenance"


def set_maintenance(enabled: bool) -> None:
    if enabled:
        MAINTENANCE_FILE.parent.mkdir(parents=True, exist_ok=True)
        MAINTENANCE_FILE.touch(mode=0o600, exist_ok=True)
    else:
        MAINTENANCE_FILE.unlink(missing_ok=True)


def in_maintenance() -> bool:
    return MAINTENANCE_FILE.exists()
