"""UTC interpretation of timestamps stored by SQLite without timezone data."""

from datetime import datetime, timezone


def as_utc(value: datetime) -> datetime:
    """Interpret naive database timestamps as UTC and normalize aware inputs."""
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )
