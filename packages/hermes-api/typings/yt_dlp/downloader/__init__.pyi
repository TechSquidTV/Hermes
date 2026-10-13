from collections.abc import Mapping
from typing import Any

class FileDownloader: ...

def get_suitable_downloader(
    info: Mapping[str, object], params: Mapping[str, Any]
) -> type[FileDownloader] | None: ...
