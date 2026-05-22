"""Export the FastAPI OpenAPI schema without starting a server."""

import json
import sys
from pathlib import Path

from app.main import app


def main() -> None:
    schema = app.openapi()
    output = json.dumps(schema, indent=2) + "\n"

    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(output)
        return

    sys.stdout.write(output)


if __name__ == "__main__":
    main()
