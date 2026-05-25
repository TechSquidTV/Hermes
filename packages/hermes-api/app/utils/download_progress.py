"""Helpers for shaping download progress data across API, tasks, and SSE."""

from collections.abc import Mapping
from typing import Any


def build_progress_object(
    *,
    status: str,
    progress: float | None = None,
    downloaded_bytes: int | None = None,
    total_bytes: int | None = None,
    download_speed: float | None = None,
    eta: float | None = None,
) -> dict[str, Any]:
    """Build the nested progress object used by DownloadStatus and SSE payloads."""
    return {
        "percentage": progress,
        "status": status,
        "downloaded_bytes": downloaded_bytes,
        "total_bytes": total_bytes,
        "speed": download_speed,
        "eta": eta,
    }


def build_download_progress_payload(
    *,
    status: str,
    progress: float | None = None,
    downloaded_bytes: int | None = None,
    total_bytes: int | None = None,
    download_speed: float | None = None,
    eta: float | None = None,
    message: str | None = None,
    result: dict[str, Any] | None = None,
    include_progress: bool = False,
    **extra: Any,
) -> dict[str, Any]:
    """Build a download progress payload with one canonical nested shape."""
    payload = {
        "status": status,
        **extra,
    }

    if message is not None:
        payload["message"] = message

    if include_progress or progress is not None or downloaded_bytes is not None:
        payload["progress"] = build_progress_object(
            status=status,
            progress=progress,
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
            download_speed=download_speed,
            eta=eta,
        )

    if result:
        payload["result"] = result

    return payload


def progress_source_from_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Read nested progress payloads while retaining compatibility with flat data."""
    progress_source = payload.get("progress")
    if isinstance(progress_source, Mapping):
        return progress_source
    return payload


def progress_fields_from_payload(
    payload: Mapping[str, Any], *, fallback_status: str
) -> dict[str, Any]:
    """Convert a Redis progress payload into DownloadProgress constructor kwargs."""
    progress_source = progress_source_from_payload(payload)
    return {
        "percentage": progress_source.get("percentage", 0.0),
        "status": progress_source.get("status", payload.get("status", fallback_status)),
        "downloaded_bytes": progress_source.get("downloaded_bytes"),
        "total_bytes": progress_source.get("total_bytes"),
        "speed": progress_source.get("speed"),
        "eta": progress_source.get("eta"),
    }
