"""
Tests for YTDLPService.
"""

import shutil
import wave
from unittest.mock import patch

import pytest
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

from app.services.yt_dlp_service import YTDLPService
from app.utils.media import DEFAULT_FORMAT_SPEC


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
        info = {"id": "test-video", "title": "Test Video", "ext": "mp4"}
        if download:
            info["requested_downloads"] = [
                {"filepath": self.opts["outtmpl"].replace("%(ext)s", "mp4")}
            ]
        return info

    def prepare_filename(self, info):
        raise AssertionError("Use the final filepath, not the output template")


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
@pytest.mark.parametrize("extension", ["wav", "mp3"])
async def test_download_video_returns_real_final_path_after_processing(
    tmp_path, extension
):
    if extension == "mp3" and not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for audio conversion")

    source = tmp_path / "source.wav"
    with wave.open(str(source), "wb") as sample:
        sample.setnchannels(1)
        sample.setsampwidth(2)
        sample.setframerate(8000)
        sample.writeframes(b"\0\0" * 8000)

    options = {"enable_file_urls": True, "noprogress": True}
    if extension == "mp3":
        options["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}
        ]

    # Exercise real yt-dlp downloads, conversion, and an already-downloaded file.
    service = YTDLPService()
    for _ in range(2):
        result_path = await service.download_video(
            source.as_uri(), str(tmp_path / "download.%(ext)s"), **options
        )
        assert result_path == str(tmp_path / f"download.{extension}")
        assert (tmp_path / f"download.{extension}").stat().st_size > 0
    if extension == "mp3":
        assert not (tmp_path / "download.wav").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("format_spec", [None, "140"])
async def test_download_video_preserves_yt_dlp_errors_and_format_selection(
    tmp_path, format_spec
):
    error = DownloadError("Requested format is not available")
    with (
        patch.object(FakeYoutubeDL, "extract_info", side_effect=error),
        patch("app.services.yt_dlp_service.yt_dlp.YoutubeDL", FakeYoutubeDL),
    ):
        options = {} if format_spec is None else {"format_spec": format_spec}
        with pytest.raises(DownloadError) as caught:
            await YTDLPService().download_video(
                "https://example.com/video", str(tmp_path / "video.%(ext)s"), **options
            )
    assert caught.value is error
    assert FakeYoutubeDL.calls[0]["format"] == (format_spec or DEFAULT_FORMAT_SPEC)


@pytest.mark.asyncio
@pytest.mark.parametrize("info", [None, {"id": "test-video"}])
async def test_download_video_rejects_results_without_downloaded_media(tmp_path, info):
    with (
        patch.object(FakeYoutubeDL, "extract_info", return_value=info),
        patch("app.services.yt_dlp_service.yt_dlp.YoutubeDL", FakeYoutubeDL),
    ):
        with pytest.raises(DownloadError, match="did not produce a media file"):
            await YTDLPService().download_video(
                "https://example.com/video", str(tmp_path / "video.%(ext)s")
            )


@pytest.mark.asyncio
@pytest.mark.parametrize("is_directory", [False, True])
async def test_download_video_rejects_missing_or_non_file_output(
    tmp_path, is_directory
):
    if is_directory:
        (tmp_path / "video.mp4").mkdir()
    # A similarly named file must never substitute for the actual result.
    (tmp_path / "video.mp4.webm").write_bytes(b"unrelated")
    with patch("app.services.yt_dlp_service.yt_dlp.YoutubeDL", FakeYoutubeDL):
        with pytest.raises(FileNotFoundError, match="Downloaded file is missing"):
            await YTDLPService().download_video(
                "https://example.com/video", str(tmp_path / "video.%(ext)s")
            )


def test_default_format_selects_separate_video_and_audio_streams():
    # Reproduce YouTube videos with no pre-merged format without network access.
    info = {
        "id": "test-video",
        "title": "Adaptive streams only",
        "extractor": "test",
        "formats": [
            {
                "format_id": "audio",
                "url": "https://example.test/audio.webm",
                "vcodec": "none",
                "acodec": "opus",
            },
            {
                "format_id": "video",
                "url": "https://example.test/video.mp4",
                "vcodec": "avc1",
                "acodec": "none",
            },
        ],
    }
    with YoutubeDL({"quiet": True, "format": DEFAULT_FORMAT_SPEC}) as ydl:
        result = ydl.process_ie_result(info, download=False)
    assert result["format_id"] == "video+audio"

    with YoutubeDL({"quiet": True, "format": "best"}) as ydl:
        with pytest.raises(ExtractorError, match="Requested format is not available"):
            ydl.process_ie_result(info, download=False)
