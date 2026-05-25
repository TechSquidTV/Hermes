"""Tests for shared utility helpers."""

from app.utils.download_progress import (
    build_download_progress_payload,
    progress_fields_from_payload,
)


def test_build_download_progress_payload_uses_nested_progress_shape():
    payload = build_download_progress_payload(
        status="downloading",
        message="Downloading: 25.0%",
        progress=25.0,
        downloaded_bytes=250,
        total_bytes=1000,
        download_speed=42.0,
        eta=12.0,
        result={"title": "Video"},
        include_progress=True,
    )

    assert payload == {
        "status": "downloading",
        "message": "Downloading: 25.0%",
        "progress": {
            "percentage": 25.0,
            "status": "downloading",
            "downloaded_bytes": 250,
            "total_bytes": 1000,
            "speed": 42.0,
            "eta": 12.0,
        },
        "result": {"title": "Video"},
    }


def test_build_download_progress_payload_preserves_empty_result_object():
    payload = build_download_progress_payload(
        status="downloading",
        result={},
    )

    assert payload["result"] == {}


def test_progress_fields_from_payload_accepts_nested_task_payload():
    fields = progress_fields_from_payload(
        {
            "status": "downloading",
            "progress": {
                "percentage": 66.0,
                "status": "downloading",
                "downloaded_bytes": 660,
                "total_bytes": 1000,
                "speed": 100.0,
                "eta": 4.0,
            },
        },
        fallback_status="processing",
    )

    assert fields == {
        "percentage": 66.0,
        "status": "downloading",
        "downloaded_bytes": 660,
        "total_bytes": 1000,
        "speed": 100.0,
        "eta": 4.0,
    }


def test_progress_fields_from_payload_accepts_legacy_flat_payload():
    fields = progress_fields_from_payload(
        {
            "percentage": 12.0,
            "downloaded_bytes": 120,
            "total_bytes": 1000,
        },
        fallback_status="downloading",
    )

    assert fields == {
        "percentage": 12.0,
        "status": "downloading",
        "downloaded_bytes": 120,
        "total_bytes": 1000,
        "speed": None,
        "eta": None,
    }
