"""Portable storage types shared by both supported database backends."""

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

from app.utils.dates import as_utc


class UTCDateTime(TypeDecorator[datetime]):
    """Store UTC without timezone data, matching the existing schema.

    Naive inputs mean UTC. Normalize aware inputs before binding so asyncpg
    accepts them and SQLite does not silently discard a non-UTC offset.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        return as_utc(value).replace(tzinfo=None) if value is not None else None
