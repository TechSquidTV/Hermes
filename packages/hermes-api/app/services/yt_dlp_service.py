"""
YoutubeDL service wrapper for async operations.
"""

import asyncio
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from yt_dlp.utils import DownloadError, ExtractorError

from app.core.logging import get_logger
from app.services.public_network import PublicYoutubeDL
from app.utils.media import DEFAULT_FORMAT_SPEC
from app.utils.urls import validate_public_url

logger = get_logger(__name__)


@dataclass(frozen=True)
class DownloadOutputs:
    """Verified final media and sidecar paths after yt-dlp postprocessing."""

    media_path: str
    sidecar_paths: tuple[str, ...] = ()

    @property
    def paths(self) -> tuple[str, ...]:
        return (self.media_path, *self.sidecar_paths)


class YTDLPService:
    """Async wrapper for yt-dlp operations."""

    def __init__(self) -> None:
        self._default_opts: dict[str, object] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "proxy": "",
            "external_downloader": "native",
            "hls_prefer_native": True,
        }
        if shutil.which("node"):
            self._default_opts["js_runtimes"] = {"node": {}}

    async def extract_info(
        self, url: str, download: bool = False, **kwargs: object
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

        def _extract_info_sync() -> dict[str, Any] | None:
            try:
                opts = self._default_opts.copy()
                opts.update(kwargs)

                validate_public_url(url)
                with PublicYoutubeDL(opts) as ydl:
                    return ydl.extract_info(url, download=download)

            except (DownloadError, ExtractorError) as e:
                logger.warning("Failed to extract info from URL", error=str(e))
                return None
            except Exception as e:
                logger.error("Unexpected error during info extraction", error=str(e))
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
        **kwargs: object,
    ) -> DownloadOutputs:
        """Download media and return all final deliverables after postprocessing.

        yt-dlp errors propagate to the task so it can report the actual failure.
        """

        def _download_sync() -> DownloadOutputs:
            final_paths: set[str] = set()

            def collect_final_paths(event: dict[str, object]) -> None:
                # The MoveFiles hook runs after conversion/embedding and before
                # yt-dlp discards its exact source-to-destination manifest.
                if (
                    event.get("status") != "finished"
                    or event.get("postprocessor") != "MoveFiles"
                ):
                    return
                info = event.get("info_dict")
                if not isinstance(info, dict):
                    return
                moves = info.get("__files_to_move", {})
                media_path = info.get("filepath")
                if not isinstance(moves, dict) or not isinstance(media_path, str):
                    return
                final_directory = info.get("__finaldir", str(Path(media_path).parent))
                if not isinstance(final_directory, str):
                    return
                for source, destination in moves.items():
                    if isinstance(source, str):
                        final_paths.add(
                            destination
                            if isinstance(destination, str) and destination
                            else str(Path(final_directory) / Path(source).name)
                        )

            opts = {
                **self._default_opts,
                "format": format_spec,
                "outtmpl": output_path,
                "restrictfilenames": True,
                **kwargs,
            }
            opts["postprocessor_hooks"] = [collect_final_paths]
            if progress_callback:
                opts["progress_hooks"] = [progress_callback]

            validate_public_url(url)
            with PublicYoutubeDL(opts) as ydl:
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
            canonical_media = str(Path(actual_path).resolve())
            sidecars = {
                str(Path(path).resolve())
                for path in final_paths
                if os.path.isfile(path)
            }
            sidecars.discard(canonical_media)
            return DownloadOutputs(canonical_media, tuple(sorted(sidecars)))

        return await asyncio.to_thread(_download_sync)

    def get_supported_extractors(self) -> list[str]:
        """Get list of supported extractor names."""
        from yt_dlp.extractor import list_extractor_classes

        return [extractor.ie_key() for extractor in list_extractor_classes()]
