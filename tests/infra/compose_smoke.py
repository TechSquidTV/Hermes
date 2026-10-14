"""Build and smoke-test both production topologies using disposable projects and data."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(*args: str, capture: bool = False, input_text: str | None = None) -> str:
    result = subprocess.run(
        args, check=True, text=True, capture_output=capture, input=input_text
    )
    return result.stdout if capture else ""


def main() -> None:
    project = f"hermes-smoke-{uuid.uuid4().hex[:10]}"
    images = {
        name: f"ghcr.io/techsquidtv/hermes-{name}:{project}" for name in ("app", "api")
    }
    run(
        "docker",
        "build",
        "--pull",
        "-f",
        str(ROOT / "packages/hermes-app/Dockerfile"),
        "-t",
        images["app"],
        str(ROOT),
    )
    run(
        "docker",
        "build",
        "--pull",
        "-f",
        str(ROOT / "packages/hermes-api/Dockerfile"),
        "-t",
        images["api"],
        str(ROOT / "packages/hermes-api"),
    )

    with tempfile.TemporaryDirectory(prefix=project) as directory:
        workspace = Path(directory)
        for source in ROOT.glob("docker-compose*.yml"):
            shutil.copyfile(source, workspace / source.name)
        template = (
            (ROOT / ".env.example")
            .read_text()
            .replace(
                "HERMES_SECRET_KEY=your-secret-key-change-this-in-production",
                f"HERMES_SECRET_KEY={uuid.uuid4().hex}",
            )
            .replace("HERMES_IMAGE_TAG=", f"HERMES_IMAGE_TAG={project}")
        )
        (workspace / ".env").write_text(template)
        for name in ("data", "downloads", "temp"):
            target = workspace / "data" / name
            target.mkdir(parents=True, exist_ok=True)
            target.chmod(
                0o777
            )  # Disposable test volumes; production ownership is documented.

        override = workspace / "smoke-images.yml"
        lines = ["services:"]
        for service in ("app", "api", "celery_worker", "celery_beat", "redis"):
            lines.extend([f"  {service}:", f"    container_name: {project}-{service}"])
            if service != "redis":
                lines.append(
                    f"    image: {images['app' if service == 'app' else 'api']}"
                )
            if service == "app":
                lines.extend(["    ports: !override", '      - "127.0.0.1::80"'])
        override.write_text("\n".join(lines) + "\n")

        # Compose runs entirely from this directory, including env_file and bind mounts.
        # The operator's .env, containers, ports and data are never used.
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("HERMES_", "VITE_", "COMPOSE_"))
            and key not in {"API_PORT", "USER_UID", "USER_GID"}
        }
        for stack in ("docker-compose.yml", "docker-compose.example.yml"):
            command = [
                "docker",
                "compose",
                "--project-directory",
                str(workspace),
                "--project-name",
                project,
                "--file",
                str(workspace / stack),
                "--file",
                str(override),
            ]

            def compose(
                *args: str,
                capture: bool = False,
                input_text: str | None = None,
                compose_command: list[str] = command,
            ) -> str:
                result = subprocess.run(
                    [*compose_command, *args],
                    env=environment,
                    cwd=workspace,
                    check=True,
                    text=True,
                    capture_output=capture,
                    input=input_text,
                )
                return result.stdout if capture else ""

            try:
                print(f"Checking {stack}", flush=True)
                compose("pull", "redis")
                compose(
                    "up",
                    "--detach",
                    "--no-build",
                    "--pull",
                    "never",
                    "--wait",
                    "--wait-timeout",
                    "180",
                )
                address = compose("port", "app", "80", capture=True).strip()
                base = f"http://{address}"
                with urllib.request.urlopen(
                    f"{base}/api/v1/health/detailed", timeout=15
                ) as response:
                    health = json.load(response)
                assert health["status"] == "healthy", health
                assert health["environment"] == "production", health
                assert all(
                    health["dependencies"][name]["status"] == "healthy"
                    for name in ("database", "redis")
                ), health
                with urllib.request.urlopen(
                    f"{base}/api/v1/docs", timeout=15
                ) as response:
                    assert "/api/v1/openapi.json" in response.read().decode()
                with urllib.request.urlopen(
                    f"{base}/api/v1/openapi.json", timeout=15
                ) as response:
                    assert "/api/v1/health/" in json.load(response)["paths"]
                with urllib.request.urlopen(
                    f"{base}/config.js", timeout=15
                ) as response:
                    config = (
                        response.read()
                        .decode()
                        .partition("window.__RUNTIME_CONFIG__ = ")[2]
                    )
                    assert (
                        json.JSONDecoder().raw_decode(config)[0]["API_BASE_URL"]
                        == "/api/v1"
                    )

                compose(
                    "exec",
                    "--no-TTY",
                    "api",
                    "python",
                    "-",
                    input_text="""
import os
import time
from pathlib import Path
from app.core.config import settings
from app.tasks.celery_app import celery_app
from app.tasks.cleanup_tasks import cleanup_temp_files, cleanup_expired_tokens
assert settings.download_dir == "/app/downloads"
assert settings.temp_dir == "/app/temp"
assert settings.download_retention_days is None
assert "cleanup-old-downloads" not in celery_app.conf.beat_schedule
assert "cleanup-expired-tokens" in celery_app.conf.beat_schedule
assert list(Path("/app/data").glob("celerybeat-schedule*"))
media = Path(settings.download_dir) / "smoke.txt"
media.write_text("persistent media")
scratch = Path(settings.temp_dir) / "smoke.txt"
scratch.write_text("shared temp file")
os.utime(scratch, (time.time() - 90000, time.time() - 90000))
result = cleanup_temp_files.delay(dry_run=True).get(timeout=30)
assert result.get("would_delete_files", 0) >= 1, result
assert scratch.exists()
result = cleanup_expired_tokens.delay(dry_run=True).get(timeout=30)
assert result.get("dry_run") is True, result
""",
                )
                assert (
                    workspace / "data/downloads/smoke.txt"
                ).read_text() == "persistent media"
                assert (workspace / "data/data/hermes.db").is_file()
            except BaseException:
                compose("logs", "--no-color", "--tail", "100")
                raise
            finally:
                compose("down", "--volumes", "--remove-orphans")

    # Exercise the actual image entrypoint with characters that broke JS interpolation.
    for api_url in ('https://example.com/a"b\\c\nline\u2028end', "/api/v1"):
        output = run(
            "docker",
            "run",
            "--rm",
            "--env",
            f"VITE_API_BASE_URL={api_url}",
            images["app"],
            "cat",
            "/usr/share/nginx/html/config.js",
            capture=True,
        )
        config = output.partition("window.__RUNTIME_CONFIG__ = ")[2]
        assert json.JSONDecoder().raw_decode(config)[0] == {"API_BASE_URL": api_url}
    print(
        "Both Compose stacks, maintenance queues, persistent mounts and runtime config passed."
    )


if __name__ == "__main__":
    main()
