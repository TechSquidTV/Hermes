"""Upgrade orchestration failure injection without a Docker daemon."""

from __future__ import annotations

import io
import json
import socket
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.upgrade import (  # noqa: E402
    SERVICES,
    WORKER_CONTROL,
    Upgrade,
    UpgradeError,
    WorkerState,
    recover,
    upgrade_lock,
    validate_storage,
)


class FakeUpgrade(Upgrade):
    def __init__(
        self, directory: Path, *, busy: bool = False, failure: str = ""
    ) -> None:
        environment = directory / ".env"
        environment.write_text(
            "HERMES_IMAGE_TAG=1.0.0\nHERMES_SECRET_KEY=private-test-key\n"
        )
        super().__init__([directory / "compose.yml"], environment, "1.1.0", 1)
        self.actions: list[tuple[str, ...]] = []
        self.busy = busy
        self.failure = failure

    def compose(self, *arguments: str) -> str:
        self.actions.append(arguments)
        if arguments[0] == "ps":
            return "container-id"
        if arguments[0] == "up" and self.failure == "startup":
            raise UpgradeError("Injected startup failure")
        return ""

    def helper(self, *arguments: str) -> str:
        self.actions.append(("helper", *arguments))
        if arguments[0] == self.failure:
            raise UpgradeError("Injected " + self.failure + " failure")
        if arguments[0] == "backup":
            return json.dumps({"snapshot": arguments[1] + "/database.sqlite"})
        return ""

    def worker(self, action: str) -> WorkerState:
        self.actions.append(("worker", action))
        return {"busy": 1 if self.busy else 0, "queues": ["hermes.downloads"]}

    def preflight(self, pull: bool) -> dict[str, str]:
        return {name: f"hermes-{name}:1.1.0" for name in SERVICES}


def inspect_output(arguments: list[str], **kwargs: object) -> str:
    return json.dumps(
        [
            {
                "State": {"Running": True},
                "Image": "sha256:old-image",
                "Id": "sha256:old-image",
                "Config": {
                    "Cmd": ["old-command"],
                    "Entrypoint": ["/entrypoint"],
                    "Env": ["HERMES_SECRET_KEY=literal$dollar"],
                    "Healthcheck": {
                        "Test": ["CMD", "old-health-check"],
                        "Interval": 1000000000,
                    },
                },
            }
        ]
    )


class UpgradeLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="hermes-upgrade-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.docker = patch("scripts.upgrade.run", side_effect=inspect_output)
        self.docker.start()
        self.addCleanup(self.docker.stop)

    def test_success_drains_then_snapshots_before_migration_and_persists_release(
        self,
    ) -> None:
        upgrade = FakeUpgrade(self.directory)
        upgrade.apply()
        commands = [action[1] for action in upgrade.actions if action[0] == "helper"]
        self.assertEqual(
            commands,
            ["maintenance", "backup", "migrate", "check-schema", "maintenance"],
        )
        self.assertLess(
            upgrade.actions.index(("worker", "pause")),
            next(
                index
                for index, action in enumerate(upgrade.actions)
                if action[:2] == ("helper", "backup")
            ),
        )
        self.assertIn("HERMES_IMAGE_TAG=1.1.0", upgrade.env_file.read_text())
        self.assertEqual(upgrade.state["phase"], "complete")

    def test_active_work_timeout_resumes_old_services_without_migration_or_kill(
        self,
    ) -> None:
        upgrade = FakeUpgrade(self.directory, busy=True)
        with patch("scripts.upgrade.time.sleep"), patch(
            "scripts.upgrade.time.monotonic", side_effect=[0, 0, 2]
        ):
            with self.assertRaisesRegex(UpgradeError, "Drain timed out"):
                upgrade.apply()
        self.assertNotIn(("helper", "migrate"), upgrade.actions)
        self.assertFalse(
            any(action[:2] == ("helper", "backup") for action in upgrade.actions)
        )
        self.assertIn(("worker", "resume"), upgrade.actions)
        self.assertIn(("start", *SERVICES), upgrade.actions)
        self.assertIn("HERMES_IMAGE_TAG=1.0.0", upgrade.env_file.read_text())
        self.assertNotIn("kill", [action[0] for action in upgrade.actions])

    def test_backup_failure_restarts_existing_services_without_migrating(self) -> None:
        upgrade = FakeUpgrade(self.directory, failure="backup")
        with self.assertRaisesRegex(UpgradeError, "backup failure"):
            upgrade.apply()
        self.assertNotIn(("helper", "migrate"), upgrade.actions)
        self.assertIn(("start", *SERVICES), upgrade.actions)

    def test_migration_and_startup_failures_leave_recovery_record_and_no_image_rollback(
        self,
    ) -> None:
        for failure in ("migrate", "startup"):
            with self.subTest(failure=failure):
                upgrade = FakeUpgrade(self.directory, failure=failure)
                with self.assertRaises(UpgradeError):
                    upgrade.apply()
                self.assertIsNotNone(upgrade.state.get("snapshot"))
                self.assertNotIn(("start", *SERVICES), upgrade.actions)
                self.assertNotIn(("helper", "restore"), upgrade.actions)
                self.assertIn("HERMES_IMAGE_TAG=1.0.0", upgrade.env_file.read_text())

    def test_recovery_requires_explicit_database_replacement(self) -> None:
        state = self.directory / "state.json"
        state.write_text(
            json.dumps(
                {
                    "snapshot": "/app/data/backups/test/database.sqlite",
                    "phase": "migrating",
                }
            )
        )
        with self.assertRaisesRegex(UpgradeError, "--restore-database"):
            recover(state, restore=False)
        state.write_text(json.dumps({"snapshot": "backup", "phase": "complete"}))
        with self.assertRaisesRegex(UpgradeError, "discard new writes"):
            recover(state, restore=True)

    def test_project_lock_prevents_simultaneous_upgrade_or_restore(self) -> None:
        with upgrade_lock(self.directory):
            with self.assertRaisesRegex(UpgradeError, "already running"):
                with upgrade_lock(self.directory):
                    self.fail("Second upgrade acquired the lock")

    def test_preflight_rejects_changed_database_or_mounts(self) -> None:
        mounts = {
            path: "/host" + path
            for path in ("/app/data", "/app/downloads", "/app/temp")
        }
        with self.assertRaisesRegex(UpgradeError, "HERMES_DATABASE_URL differs"):
            validate_storage(
                {"HERMES_DATABASE_URL": "sqlite+aiosqlite:///other.db"},
                [],
                mounts,
                mounts,
            )
        with self.assertRaisesRegex(UpgradeError, "Storage mount"):
            validate_storage({}, [], mounts, {**mounts, "/app/data": "/other-volume"})


class WorkerProbeTests(unittest.TestCase):
    def test_missing_redis_queue_is_empty_but_other_channel_errors_fail(self) -> None:
        class ChannelError(Exception):
            def __init__(self, reply_code: str) -> None:
                self.reply_code = reply_code

        exceptions = ModuleType("kombu.exceptions")
        setattr(exceptions, "ChannelError", ChannelError)
        celery_module = ModuleType("app.tasks.celery_app")
        app = MagicMock()
        setattr(celery_module, "celery_app", app)
        node = "hermes-worker@" + socket.gethostname()
        inspection = app.control.inspect.return_value
        inspection.active_queues.return_value = {node: [{"name": "hermes.downloads"}]}
        for method in ("active", "reserved", "scheduled"):
            getattr(inspection, method).return_value = {node: []}
        channel = (
            app.connection_for_read.return_value.__enter__.return_value.channel.return_value
        )
        modules = {
            "app.tasks.celery_app": celery_module,
            "kombu.exceptions": exceptions,
        }
        with patch.dict(sys.modules, modules), patch.object(
            sys, "argv", ["worker-probe", "probe", "[]"]
        ):
            channel.queue_declare.side_effect = ChannelError("404")
            output = io.StringIO()
            with redirect_stdout(output):
                exec(WORKER_CONTROL, {})
            self.assertEqual(json.loads(output.getvalue())["busy"], 0)
            channel.queue_declare.side_effect = ChannelError("403")
            with self.assertRaises(ChannelError):
                exec(WORKER_CONTROL, {})


if __name__ == "__main__":
    unittest.main()
