"""Exercise the actual synchronous worker boundary across consecutive loops."""

import os
import subprocess
import sys
from pathlib import Path

from app.core.config import settings


def test_repeated_worker_tasks_in_one_process() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.tasks.cleanup_tasks import cleanup_expired_tokens; "
            "first = cleanup_expired_tokens(dry_run=True); "
            "second = cleanup_expired_tokens(dry_run=True); "
            "assert first == {'would_delete_tokens': 0, 'dry_run': True}, first; "
            "assert second == first, second",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={**os.environ, "HERMES_DATABASE_URL": settings.database_url},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
