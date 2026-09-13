"""Media-related defaults shared by download models, services, and tasks."""

# yt-dlp's default selection supports sites with separate video/audio streams.
DEFAULT_FORMAT_SPEC = "bestvideo*+bestaudio/best"
