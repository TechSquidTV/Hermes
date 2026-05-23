"""
Tests for YTDLPService.
"""

from unittest.mock import patch

import pytest

from app.services.yt_dlp_service import YTDLPService


class FakeYoutubeDL:
    """Minimal context manager for asserting yt-dlp options."""

    calls = []

    def __init__(self, opts):
        self.opts = opts
        self.calls.append(opts)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def extract_info(self, url, download=False):
        return {"id": "test-video", "title": "Test Video", "ext": "mp4"}

    def prepare_filename(self, info):
        return self.opts["outtmpl"].replace("%(ext)s", info["ext"])


@pytest.fixture(autouse=True)
def reset_fake_youtube_dl():
    FakeYoutubeDL.calls = []


@pytest.mark.asyncio
async def test_extract_info_enables_node_js_runtime():
    service = YTDLPService()

    with patch("app.services.yt_dlp_service.yt_dlp.YoutubeDL", FakeYoutubeDL):
        result = await service.extract_info("https://example.com/video")

    assert result["title"] == "Test Video"
    assert FakeYoutubeDL.calls[0]["js_runtimes"] == {"node": {}}
    assert "remote_components" not in FakeYoutubeDL.calls[0]


@pytest.mark.asyncio
async def test_download_video_enables_node_js_runtime(tmp_path):
    service = YTDLPService()
    output_path = tmp_path / "test-video.%(ext)s"
    downloaded_path = tmp_path / "test-video.mp4"
    downloaded_path.write_bytes(b"video")

    with patch("app.services.yt_dlp_service.yt_dlp.YoutubeDL", FakeYoutubeDL):
        result_path = await service.download_video(
            "https://example.com/video",
            str(output_path),
        )

    assert result_path == str(downloaded_path)
    assert FakeYoutubeDL.calls[0]["js_runtimes"] == {"node": {}}
    assert "remote_components" not in FakeYoutubeDL.calls[0]
