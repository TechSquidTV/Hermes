from collections.abc import Mapping
from typing import Any

from .. import YoutubeDL
from . import FileDownloader

class HlsFD(FileDownloader):
    def __init__(self, ydl: YoutubeDL, params: Mapping[str, Any]) -> None: ...
    def _prepare_url(self, info: Mapping[str, object], url: str) -> str: ...
    @staticmethod
    def can_download(manifest: str, info: Mapping[str, object]) -> bool: ...
