"""
Pydantic models for format information.
"""

from typing import List

from pydantic import ConfigDict, Field

from app.models.base import CamelCaseModel


class FormatInfo(CamelCaseModel):
    """Information about supported formats and quality options."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "video_formats": ["mp4", "webm", "mkv", "avi"],
                "audio_formats": ["mp3", "m4a", "ogg", "flac"],
                "subtitle_formats": ["vtt", "srt", "ass"],
                "quality_options": [
                    "best",
                    "worst",
                    "bestvideo+bestaudio",
                    "bestaudio",
                ],
                "resolution_options": ["360p", "480p", "720p", "1080p", "2160p"],
                "format_notes": {
                    "best": "Select the best quality format (video+audio)",
                    "bestaudio": "Best audio-only stream",
                },
            }
        }
    )

    video_formats: List[str] = Field(
        ...,
        description="Supported video format extensions",
        json_schema_extra={"example": ["mp4", "webm", "mkv", "avi", "flv", "mov"]},
    )

    audio_formats: List[str] = Field(
        ...,
        description="Supported audio format extensions",
        json_schema_extra={"example": ["mp3", "m4a", "ogg", "flac", "wav", "aac"]},
    )

    subtitle_formats: List[str] = Field(
        ...,
        description="Supported subtitle format extensions",
        json_schema_extra={"example": ["vtt", "srt", "ass", "sub"]},
    )

    quality_options: List[str] = Field(
        ...,
        description="Available quality selection options",
        json_schema_extra={
            "example": [
                "best",
                "worst",
                "bestvideo+bestaudio",
                "worstvideo+worstaudio",
                "bestvideo",
                "bestaudio",
            ]
        },
    )

    resolution_options: List[str] = Field(
        default_factory=lambda: [
            "144p",
            "240p",
            "360p",
            "480p",
            "720p",
            "1080p",
            "1440p",
            "2160p",
            "4320p",
        ],
        description="Common video resolution options",
    )

    format_notes: dict = Field(
        default_factory=lambda: {
            "best": "Select the best quality format (video+audio)",
            "worst": "Select the worst quality format",
            "bestvideo+bestaudio": "Best video and audio streams merged",
            "bestaudio": "Best audio-only stream",
            "mp4": "Prefer MP4 container format",
            "webm": "Prefer WebM container format",
        },
        description="Descriptions for format selection options",
    )
