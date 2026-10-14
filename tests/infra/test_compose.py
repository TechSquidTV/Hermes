"""Validate the documented environment against each Compose topology (no daemon needed)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STACKS = ("docker-compose.yml", "docker-compose.example.yml", "docker-compose.dev.yml")


@unittest.skipUnless(shutil.which("docker"), "Docker Compose CLI is required")
class ComposeConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="hermes-compose-config-")
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        for source in ROOT.glob("docker-compose*.yml"):
            shutil.copyfile(source, self.project / source.name)
        self.environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("HERMES_", "VITE_", "COMPOSE_"))
            and key not in {"API_PORT", "USER_UID", "USER_GID"}
        }
        self.template = (
            (ROOT / ".env.example")
            .read_text()
            .replace(
                "HERMES_SECRET_KEY=your-secret-key-change-this-in-production",
                "HERMES_SECRET_KEY=compose-configuration-test-only",
            )
        )
        self.write_environment()

    def write_environment(self, image_tag: str = "1.2.3") -> None:
        (self.project / ".env").write_text(
            self.template.replace("HERMES_IMAGE_TAG=", f"HERMES_IMAGE_TAG={image_tag}")
        )

    def compose(self, stack: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["docker", "compose", "--file", stack, "config", "--format", "json"],
            cwd=self.project,
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_backend_services_share_persistent_storage_and_docker_redis(self) -> None:
        for stack in STACKS:
            with self.subTest(stack=stack):
                result = self.compose(stack)
                self.assertEqual(result.returncode, 0, result.stderr)
                services = json.loads(result.stdout)["services"]
                for name in ("api", "celery_worker", "celery_beat"):
                    service = services[name]
                    settings = service["environment"]
                    self.assertEqual(
                        settings["HERMES_REDIS_URL"], "redis://redis:6379/0"
                    )
                    self.assertEqual(settings["HERMES_DOWNLOAD_DIR"], "/app/downloads")
                    self.assertEqual(settings["HERMES_TEMP_DIR"], "/app/temp")
                    self.assertEqual(
                        settings["HERMES_DEBUG"],
                        "true" if ".dev." in stack else "false",
                    )
                    self.assertEqual(
                        {
                            volume["target"]
                            for volume in service["volumes"]
                            if volume["type"] == "bind"
                        }
                        & {"/app/data", "/app/downloads", "/app/temp"},
                        {"/app/data", "/app/downloads", "/app/temp"},
                    )
                for name in ("celery_worker", "celery_beat"):
                    self.assertEqual(
                        services[name]["command"][1:3], ["-A", "app.worker"]
                    )
                    self.assertEqual(
                        services[name]["depends_on"]["api"]["condition"],
                        "service_healthy",
                    )
                self.assertIn(
                    "--schedule=/app/data/celerybeat-schedule",
                    services["celery_beat"]["command"],
                )

    def test_prebuilt_services_use_one_explicit_release(self) -> None:
        result = self.compose("docker-compose.example.yml")
        self.assertEqual(result.returncode, 0, result.stderr)
        services = json.loads(result.stdout)["services"]
        self.assertEqual(
            services["app"]["image"], "ghcr.io/techsquidtv/hermes-app:1.2.3"
        )
        for name in ("api", "celery_worker", "celery_beat"):
            self.assertEqual(
                services[name]["image"], "ghcr.io/techsquidtv/hermes-api:1.2.3"
            )
        self.write_environment(image_tag="")
        self.assertNotEqual(self.compose("docker-compose.example.yml").returncode, 0)
        self.assertEqual(self.compose("docker-compose.yml").returncode, 0)

    def test_separate_hosts_exposes_only_the_documented_ports(self) -> None:
        result = self.compose("docker-compose.test-separate-hosts.yml")
        self.assertEqual(result.returncode, 0, result.stderr)
        services = json.loads(result.stdout)["services"]
        self.assertEqual(
            [port["published"] for port in services["app"]["ports"]], ["3001"]
        )
        self.assertEqual(
            [port["published"] for port in services["api"]["ports"]], ["8001"]
        )
        for name in ("api", "celery_worker", "celery_beat"):
            self.assertEqual(
                services[name]["environment"]["HERMES_SECRET_KEY"],
                "compose-configuration-test-only",
            )
        (self.project / ".env").write_text("")
        self.assertNotEqual(
            self.compose("docker-compose.test-separate-hosts.yml").returncode, 0
        )


if __name__ == "__main__":
    unittest.main()
