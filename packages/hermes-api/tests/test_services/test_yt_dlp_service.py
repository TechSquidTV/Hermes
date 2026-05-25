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
    with patch(
        "app.services.yt_dlp_service.shutil.which", return_value="/usr/bin/node"
    ):
        service = YTDLPService()

    with patch("app.services.yt_dlp_service.yt_dlp.YoutubeDL", FakeYoutubeDL):
        result = await service.extract_info("https://example.com/video")

    assert result["title"] == "Test Video"
    assert FakeYoutubeDL.calls[0]["js_runtimes"] == {"node": {}}
    assert "remote_components" not in FakeYoutubeDL.calls[0]


@pytest.mark.asyncio
async def test_download_video_enables_node_js_runtime(tmp_path):
    with patch(
        "app.services.yt_dlp_service.shutil.which", return_value="/usr/bin/node"
    ):
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


@pytest.mark.asyncio
async def test_extract_info_uses_yt_dlp_defaults_when_node_is_unavailable():
    with patch("app.services.yt_dlp_service.shutil.which", return_value=None):
        service = YTDLPService()

    with patch("app.services.yt_dlp_service.yt_dlp.YoutubeDL", FakeYoutubeDL):
        result = await service.extract_info("https://example.com/video")

    assert result["title"] == "Test Video"
    assert "js_runtimes" not in FakeYoutubeDL.calls[0]
    assert "remote_components" not in FakeYoutubeDL.calls[0]


@pytest.mark.asyncio
async def test_download_video_finds_file_when_prepared_template_keeps_ext_placeholder(
    tmp_path,
):
    class FakeTemplateYoutubeDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def extract_info(self, url, download=False):
            return {"id": "test-video", "title": "Test Video"}

        def prepare_filename(self, info):
            return self.opts["outtmpl"]

    output_path = tmp_path / "test-video.%(ext)s"
    downloaded_path = tmp_path / "test-video.webm"
    downloaded_path.write_bytes(b"video")

    service = YTDLPService()
    with patch("app.services.yt_dlp_service.yt_dlp.YoutubeDL", FakeTemplateYoutubeDL):
        result_path = await service.download_video(
            "https://example.com/video",
            str(output_path),
        )

    assert result_path == str(downloaded_path)


@pytest.mark.asyncio
async def test_download_video_uses_selected_format_extension_when_common_lookup_fails(
    tmp_path,
):
    class FakeFormatYoutubeDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def extract_info(self, url, download=False):
            return {
                "id": "audio-video",
                "title": "Audio Video",
                "formats": [
                    {"format_id": "18", "ext": "mp4"},
                    {"format_id": "140", "ext": "m4a"},
                ],
            }

        def prepare_filename(self, info):
            return self.opts["outtmpl"]

    output_path = tmp_path / "audio-video.%(ext)s"
    downloaded_path = tmp_path / "audio-video.m4a"
    downloaded_path.write_bytes(b"audio")

    service = YTDLPService()
    with patch("app.services.yt_dlp_service.yt_dlp.YoutubeDL", FakeFormatYoutubeDL):
        result_path = await service.download_video(
            "https://example.com/video",
            str(output_path),
            format_spec="140",
        )

    assert result_path == str(downloaded_path)
