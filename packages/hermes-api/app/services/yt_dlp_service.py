"""
YoutubeDL service wrapper for async operations.
"""

import asyncio
import os
import shutil
from typing import Any, Callable, Dict, Optional

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

from app.core.logging import get_logger
from app.utils.media import DEFAULT_FORMAT_SPEC

logger = get_logger(__name__)


class YTDLPService:
    """Async wrapper for yt-dlp operations."""

    def __init__(self):
        self._default_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        if shutil.which("node"):
            self._default_opts["js_runtimes"] = {"node": {}}

    async def extract_info(
        self, url: str, download: bool = False, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Extract video information asynchronously.

        Args:
            url: Video URL to extract information from
            download: Whether to download the video
            **kwargs: Additional yt-dlp options

        Returns:
            Video information dictionary or None if extraction fails
        """

        def _extract_info_sync():
            try:
                opts = self._default_opts.copy()
                opts.update(kwargs)

                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(url, download=download)

            except (DownloadError, ExtractorError) as e:
                logger.warning("Failed to extract info from URL", url=url, error=str(e))
                return None
            except Exception as e:
                logger.error(
                    "Unexpected error during info extraction", url=url, error=str(e)
                )
                return None

        # Run in thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _extract_info_sync)

    async def download_video(
        self,
        url: str,
        output_path: str,
        format_spec: str = DEFAULT_FORMAT_SPEC,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        **kwargs,
    ) -> str:
        """Download media and return its final path after all postprocessing.

        yt-dlp errors propagate to the task so it can report the actual failure.
        """

        def _download_sync() -> str:
            opts = {
                **self._default_opts,
                "format": format_spec,
                "outtmpl": output_path,
                "restrictfilenames": True,
                **kwargs,
            }
            if progress_callback:
                opts["progress_hooks"] = [progress_callback]

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

            # prepare_filename uses the original format, which can differ from
            # the file produced by merging, remuxing, or audio conversion.
            downloads = info.get("requested_downloads", []) if info else []
            if not downloads:
                raise DownloadError("yt-dlp did not produce a media file")
            actual_path = downloads[0].get("filepath")
            if not isinstance(actual_path, str) or not os.path.isfile(actual_path):
                raise FileNotFoundError("Downloaded file is missing")

            logger.info("Downloaded media file", path=actual_path)
            return actual_path

        return await asyncio.to_thread(_download_sync)

    def get_supported_extractors(self) -> list[str]:
        """Get list of supported extractor names."""
        return list(
            yt_dlp.extractor.get_info_extractor.__wrapped__.__defaults__[0].keys()
        )

    def validate_url(self, url: str) -> bool:
        """
        Validate if URL can be handled by yt-dlp.

        Args:
            url: URL to validate

        Returns:
            True if URL is supported, False otherwise
        """
        try:
            # Try to find a suitable extractor
            from yt_dlp.extractor import gen_extractor_classes

            for ie_class in gen_extractor_classes():
                ie = ie_class()
                if ie.suitable(url):
                    return True

            return False

        except Exception:
            return False
