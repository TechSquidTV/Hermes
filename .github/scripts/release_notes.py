"""Render the upgrade guidance committed with a release's source code."""

import re
import sys
from pathlib import Path


def render_notes(version: str, template: Path) -> str:
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("Expected an exact X.Y.Z release version")
    return template.read_text().replace("{{VERSION}}", version)


if __name__ == "__main__":
    print(render_notes(sys.argv[1], Path(sys.argv[2])), end="")
