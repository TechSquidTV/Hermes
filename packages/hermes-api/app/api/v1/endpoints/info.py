"""
Video information extraction endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from yt_dlp.utils import ExtractorError

from app.core.logging import get_logger
from app.models.pydantic.response import (
    FormatDetail,
    PlaylistEntry,
    SubtitleDetail,
    ThumbnailDetail,
    VideoInfo,
)
from app.services.yt_dlp_service import YTDLPService

router = APIRouter()
logger = get_logger(__name__)
yt_service = YTDLPService()


@router.get("/", response_model=VideoInfo)
async def extract_video_info(
    url: str = Query(..., description="Video URL to extract information from"),
    include_formats: bool = Query(
        True, description="Whether to include available formats in response"
    ),
):
    """
    Extract metadata and available formats for a video without downloading it.
    Useful for previewing video details and format options.
    """
    try:
        logger.info("Extracting video info", url=url)

        # Extract with flat mode first to quickly detect if it's a playlist
        # This avoids fetching full metadata twice
        info = await yt_service.extract_info(url, download=False, extract_flat=True)

        if not info:
            raise HTTPException(
                status_code=404, detail="Could not extract video information"
            )

        # Check if this is a playlist
        is_playlist = info.get("_type") in ("playlist", "multi_video")

        if is_playlist:
            # Already have flat extracted playlist data, use it directly
            # This is much faster than re-extracting

            entries = info.get("entries", [])

            # Filter out unavailable/None entries
            valid_entries = []
            for entry in entries:
                if entry is None:
                    continue  # Skip unavailable videos

                # Build entry with URL priority
                entry_url = (
                    entry.get("webpage_url")
                    or entry.get("url")
                    or
                    # Fallback URL construction (only for known platforms)
                    (
                        f"https://www.youtube.com/watch?v={entry['id']}"
                        if "youtube" in info.get("extractor", "").lower()
                        and entry.get("id")
                        else None
                    )
                )

                if not entry_url or not entry.get("id"):
                    continue  # Skip if we can't construct valid URL

                valid_entries.append(
                    PlaylistEntry(
                        id=entry["id"],
                        title=entry.get("title", "Untitled"),
                        url=entry_url,
                        duration=entry.get("duration"),
                        thumbnail=entry.get("thumbnail")
                        or (
                            entry.get("thumbnails", [{}])[0].get("url")
                            if entry.get("thumbnails")
                            else None
                        ),
                        uploader=entry.get("uploader"),
                    )
                )

            # Build playlist response
            response = VideoInfo(
                id=info.get("id", "unknown"),
                title=info.get("title", "Untitled Playlist"),
                description=info.get("description"),
                duration=None,  # Playlists don't have single duration
                uploader=info.get("uploader"),
                upload_date=info.get("upload_date"),
                view_count=info.get("view_count"),
                webpage_url=info.get("webpage_url", url),
                extractor=info.get("extractor", ""),
                formats=[],  # Playlists don't have formats
                thumbnails=[
                    ThumbnailDetail(
                        url=thumb.get("url", ""),
                        width=thumb.get("width"),
                        height=thumb.get("height"),
                    )
                    for thumb in info.get("thumbnails", [])
                ],
                subtitles={
                    lang: [
                        SubtitleDetail(
                            url=sub.get("url", ""), ext=sub.get("ext", ""), lang=lang
                        )
                        for sub in subs
                    ]
                    for lang, subs in info.get("subtitles", {}).items()
                },
                playlist_count=len(valid_entries),
                playlist_id=info.get("id"),
                playlist_title=info.get("title"),
                entries=valid_entries,
            )

            logger.info(
                "Playlist info extracted successfully",
                playlist_id=response.id,
                video_count=len(valid_entries),
            )
            return response

        else:
            # Single video - re-extract with full metadata (formats, descriptions, etc.)
            # Flat extraction doesn't include format info needed for single videos
            info = await yt_service.extract_info(
                url, download=False, extract_flat=False
            )

            if not info:
                raise HTTPException(
                    status_code=404, detail="Could not extract video information"
                )

            response = VideoInfo(
                id=info.get("id", ""),
                title=info.get("title", ""),
                description=info.get("description"),
                duration=info.get("duration"),
                uploader=info.get("uploader"),
                upload_date=info.get("upload_date"),
                view_count=info.get("view_count"),
                webpage_url=info.get("webpage_url", url),
                extractor=info.get("extractor", ""),
                formats=[
                    FormatDetail(
                        format_id=f.get("format_id"),
                        ext=f.get("ext"),
                        resolution=f.get("resolution"),
                        fps=f.get("fps"),
                        vcodec=f.get("vcodec"),
                        acodec=f.get("acodec"),
                        tbr=f.get("tbr"),
                        filesize=f.get("filesize"),
                        format_note=f.get("format_note"),
                    )
                    for f in (info.get("formats", []) if include_formats else [])
                ],
                thumbnails=[
                    ThumbnailDetail(
                        url=thumb.get("url", ""),
                        width=thumb.get("width"),
                        height=thumb.get("height"),
                    )
                    for thumb in info.get("thumbnails", [])
                ],
                subtitles={
                    lang: [
                        SubtitleDetail(
                            url=sub.get("url", ""), ext=sub.get("ext", ""), lang=lang
                        )
                        for sub in subs
                    ]
                    for lang, subs in info.get("subtitles", {}).items()
                },
            )

            logger.info("Video info extracted successfully", video_id=response.id)
            return response

    except ExtractorError as e:
        logger.error("Extractor error", url=url, error=str(e))
        raise HTTPException(
            status_code=400, detail=f"Failed to extract information: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to extract video info", url=url, error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to extract video information: {str(e)}"
        )
