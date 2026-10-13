from collections.abc import Iterable

def list_extractor_classes(
    age_limit: int | None = ...,
) -> Iterable[type[InfoExtractor]]: ...

class InfoExtractor:
    IE_NAME: str
    @classmethod
    def ie_key(cls) -> str: ...
