"""Shared time period helpers for analytics endpoints."""

from datetime import timedelta

PERIOD_DELTAS = {
    "day": timedelta(days=1),
    "week": timedelta(days=7),
    "month": timedelta(days=30),
    "year": timedelta(days=365),
}
DEFAULT_PERIOD_DELTA = PERIOD_DELTAS["week"]


def get_period_delta(period: str) -> timedelta:
    """Return the configured period delta, defaulting to one week."""
    return PERIOD_DELTAS.get(period, DEFAULT_PERIOD_DELTA)
