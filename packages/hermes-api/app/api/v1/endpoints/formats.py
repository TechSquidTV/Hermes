"""
Format information endpoints.

Provides information about supported video/audio formats,
quality options, and format selection guidelines.
"""

from fastapi import APIRouter, Depends

from app.core.security import get_current_api_key
from app.models.pydantic.format import FormatInfo

router = APIRouter(tags=["formats"])


@router.get("/", response_model=FormatInfo)
async def get_available_formats():
    """
    Get information about supported video formats, codecs, and containers.

    This endpoint provides comprehensive information about:
    - Supported video format extensions
    - Supported audio format extensions
    - Supported subtitle formats
    - Quality selection options
    - Common resolution options
    - Format selection guidelines

    Useful for building format selection interfaces and understanding
    what format options are available for downloads.

    Returns:
        FormatInfo: Comprehensive format information including video formats,
        audio formats, subtitle formats, and quality options.

    Example:
        ```
        GET /api/v1/formats/

        Response:
        {
            "video_formats": ["mp4", "webm", "mkv", "avi"],
            "audio_formats": ["mp3", "m4a", "ogg", "flac"],
            "subtitle_formats": ["vtt", "srt", "ass"],
            "quality_options": ["best", "worst", "bestvideo+bestaudio"],
            "resolution_options": ["360p", "480p", "720p", "1080p"],
            "format_notes": {
                "best": "Select the best quality format (video+audio)"
            }
        }
        ```
    """

    # Return static format information
    # This could be extended to query yt-dlp for dynamic format capabilities
    return FormatInfo(
        video_formats=[
            "mp4",  # MPEG-4 Part 14 (most compatible)
            "webm",  # WebM (open format)
            "mkv",  # Matroska (high quality, many features)
            "avi",  # Audio Video Interleave (legacy)
            "flv",  # Flash Video (legacy)
            "mov",  # QuickTime (Apple)
            "wmv",  # Windows Media Video
            "3gp",  # 3GPP (mobile)
            "m4v",  # iTunes video
            "mpg",  # MPEG
            "ts",  # MPEG Transport Stream
            "f4v",  # Flash MP4
        ],
        audio_formats=[
            "mp3",  # MPEG Audio Layer 3 (most compatible)
            "m4a",  # MPEG-4 Audio (AAC)
            "ogg",  # Ogg Vorbis (open format)
            "flac",  # Free Lossless Audio Codec
            "wav",  # Waveform Audio (uncompressed)
            "aac",  # Advanced Audio Coding
            "opus",  # Opus (high quality, low latency)
            "wma",  # Windows Media Audio
            "alac",  # Apple Lossless
            "aiff",  # Audio Interchange File Format
            "webm",  # WebM audio
        ],
        subtitle_formats=[
            "vtt",  # WebVTT (Web Video Text Tracks)
            "srt",  # SubRip (most common)
            "ass",  # Advanced SubStation Alpha (styled)
            "sub",  # MicroDVD/SubViewer
            "ssa",  # SubStation Alpha
            "lrc",  # LRC (lyrics)
            "sbv",  # YouTube subtitle format
            "json3",  # YouTube JSON format
            "srv1",  # YouTube SRV1 format
            "srv2",  # YouTube SRV2 format
            "srv3",  # YouTube SRV3 format
            "ttml",  # Timed Text Markup Language
        ],
        quality_options=[
            # Single format selections
            "best",  # Best quality single format
            "worst",  # Worst quality single format
            # Video + Audio combinations
            "bestvideo+bestaudio",  # Best video + best audio merged
            "worstvideo+worstaudio",  # Worst video + worst audio merged
            # Video only
            "bestvideo",  # Best video stream only
            "worstvideo",  # Worst video stream only
            # Audio only
            "bestaudio",  # Best audio stream only
            "worstaudio",  # Worst audio stream only
            # Container preferences
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",  # MP4 preferred
            "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]",  # WebM preferred
            # Resolution-based
            "bestvideo[height<=480]+bestaudio/best[height<=480]",  # Max 480p
            "bestvideo[height<=720]+bestaudio/best[height<=720]",  # Max 720p
            "bestvideo[height<=1080]+bestaudio/best[height<=1080]",  # Max 1080p
            # Format ID (can be obtained from /info endpoint)
            "137+140",  # Specific format IDs
        ],
        resolution_options=[
            "144p",  # 256x144
            "240p",  # 426x240
            "360p",  # 640x360 (SD)
            "480p",  # 854x480 (SD)
            "720p",  # 1280x720 (HD)
            "1080p",  # 1920x1080 (Full HD)
            "1440p",  # 2560x1440 (2K/QHD)
            "2160p",  # 3840x2160 (4K/UHD)
            "4320p",  # 7680x4320 (8K)
        ],
        format_notes={
            # Basic selections
            "best": "Select the best quality format with both video and audio",
            "worst": "Select the worst quality format",
            # Combined formats
            "bestvideo+bestaudio": "Download best video and audio streams separately and merge them",
            "worstvideo+worstaudio": "Download worst video and audio streams separately and merge them",
            # Stream-specific
            "bestvideo": "Download only the best video stream (no audio)",
            "bestaudio": "Download only the best audio stream (no video)",
            "worstvideo": "Download only the worst video stream",
            "worstaudio": "Download only the worst audio stream",
            # Container formats
            "mp4": "Prefer MP4 container format (most compatible, works on all devices)",
            "webm": "Prefer WebM container format (open format, good quality)",
            "mkv": "Prefer MKV container format (supports many features, high quality)",
            # Resolution limits
            "bestvideo[height<=720]+bestaudio": "Best quality up to 720p (good balance of quality and size)",
            "bestvideo[height<=1080]+bestaudio": "Best quality up to 1080p (Full HD)",
            # Audio formats
            "bestaudio[ext=m4a]": "Best audio in M4A format",
            "bestaudio[ext=mp3]": "Best audio in MP3 format (most compatible)",
            "bestaudio[ext=opus]": "Best audio in Opus format (best quality per size)",
            # Special cases
            "format_id": "Use specific format ID from video info (e.g., '137+140')",
        },
    )
