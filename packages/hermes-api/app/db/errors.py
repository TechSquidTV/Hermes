"""Classify database contention without inspecting SQL or credential values."""

import sqlite3

from sqlalchemy.exc import OperationalError


def is_sqlite_lock_error(error: OperationalError) -> bool:
    if not isinstance(error.orig, sqlite3.Error):
        return False
    code = getattr(error.orig, "sqlite_errorcode", None)
    return isinstance(code, int) and code & 0xFF in (
        sqlite3.SQLITE_BUSY,
        sqlite3.SQLITE_LOCKED,
    )
