"""
YoutubeDL service wrapper for async operations.
"""

import asyncio
import os
import tempfile
from typing import Any, Callable, Dict, Optional

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

from app.core.logging import get_logger

logger = get_logger(__name__)


class YTDLPService:
    """Async wrapper for yt-dlp operations."""

    def __init__(self):
        self._default_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

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
        format_spec: str = "best",
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        **kwargs,
    ) -> Optional[str]:
        """
        Download video asynchronously.

        Args:
            url: Video URL to download
            output_path: Path where to save the video
            format_spec: Format selection specification
            progress_callback: Optional callback for progress updates
            **kwargs: Additional yt-dlp options

        Returns:
            Path to downloaded file or None if download fails
        """

        def _download_sync():
            try:
                opts = self._default_opts.copy()
                opts.update(
                    {
                        "format": format_spec,
                        "outtmpl": output_path,
                        "restrictfilenames": True,  # Ensure safe filenames
                        **kwargs,
                    }
                )

                # Add progress hook if callback provided
                if progress_callback:
                    opts["progress_hooks"] = [progress_callback]

                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if info:
                        # Get the actual filename from yt-dlp
                        actual_path = ydl.prepare_filename(info)
                        logger.info("Prepared filename from yt-dlp", path=actual_path)

                        # Check if the file exists and has a proper extension
                        if actual_path and os.path.exists(actual_path):
                            # File exists with proper extension, return it
                            return actual_path
                        else:
                            # Template didn't work, try to find the actual file
                            directory = os.path.dirname(actual_path)
                            base_name = os.path.basename(actual_path)

                            # Remove the template part if it exists
                            if ".%(ext)s" in base_name:
                                base_name = base_name.replace(".%(ext)s", "")

                            # Look for the actual downloaded file with common extensions
                            for ext in [
                                ".mp4",
                                ".webm",
                                ".mkv",
                                ".avi",
                                ".mov",
                                ".flv",
                                ".3gp",
                                ".m4v",
                            ]:
                                potential_path = os.path.join(
                                    directory, base_name + ext
                                )
                                if os.path.exists(potential_path):
                                    return potential_path

                            # If still not found, get extension from format info
                            formats = info.get("formats", [])
                            if formats:
                                # Find the format that matches our format_spec
                                selected_format = None
                                for fmt in formats:
                                    if fmt.get("format_id") == format_spec:
                                        selected_format = fmt
                                        break
                                    elif format_spec in ["best", "worst"] and fmt.get(
                                        "format_note"
                                    ):
                                        if (
                                            "best" in format_spec.lower()
                                            and "best"
                                            in fmt.get("format_note", "").lower()
                                        ):
                                            selected_format = fmt
                                            break

                                # Fallback to first format with extension
                                if not selected_format:
                                    for fmt in formats:
                                        if fmt.get("ext"):
                                            selected_format = fmt
                                            break

                                if selected_format and selected_format.get("ext"):
                                    ext = selected_format.get("ext")
                                    correct_path = os.path.join(
                                        directory, base_name + f".{ext}"
                                    )
                                    if os.path.exists(correct_path):
                                        return correct_path

                        # If we can't find the file, return the prepared path anyway
                        # (it might have been created with a different extension)
                        return actual_path

                return None

            except (DownloadError, ExtractorError) as e:
                logger.warning("Failed to download video", url=url, error=str(e))
                return None
            except Exception as e:
                logger.error("Unexpected error during download", url=url, error=str(e))
                return None

        # Run in thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _download_sync)

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
            from yt_dlp.extractor import gen_extractor_classes, get_info_extractor

            for ie_class in gen_extractor_classes():
                ie = ie_class()
                if ie.suitable(url):
                    return True

            return False

        except Exception:
            return False
