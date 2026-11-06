"""Upgrade orchestration failure injection without a Docker daemon."""

from __future__ import annotations

import io
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
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
    defer_signals,
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
            return "celery_worker" if "--services" in arguments else "container-id"
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
        self.project = "test-project"
        images = {name: f"hermes-{name}:1.1.0" for name in SERVICES}
        self.configuration = {
            "name": self.project,
            "services": {
                name: {
                    "image": image,
                    "environment": {
                        "HERMES_DATABASE_URL": "sqlite+aiosqlite:////app/data/original.sqlite",
                        "HERMES_SECRET_KEY": "literal$$dollar",
                    },
                }
                for name, image in images.items()
            },
        }
        return images


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

    def test_broken_output_cannot_roll_back_a_successful_upgrade(self) -> None:
        class Disconnected(io.StringIO):
            def write(self, value: str) -> int:
                raise BrokenPipeError("Terminal disconnected")

        upgrade = FakeUpgrade(self.directory)
        with patch("sys.stdout", Disconnected()):
            upgrade.apply()
        self.assertEqual(upgrade.state["phase"], "complete")
        self.assertEqual(
            [
                action
                for action in upgrade.actions
                if action[:2] == ("helper", "maintenance")
            ],
            [("helper", "maintenance", "on"), ("helper", "maintenance", "off")],
        )
        self.assertEqual(sum(action[0] == "stop" for action in upgrade.actions), 2)

    def test_broken_error_output_preserves_the_original_failure(self) -> None:
        class Disconnected(io.StringIO):
            def write(self, value: str) -> int:
                raise OSError("Terminal disconnected")

        upgrade = FakeUpgrade(self.directory, failure="migrate")
        with patch("sys.stderr", Disconnected()), self.assertRaisesRegex(
            UpgradeError, "migrate failure"
        ):
            upgrade.apply()
        self.assertEqual(upgrade.state["phase"], "migrating")

    def test_recovery_uses_private_resolved_configuration_before_restoring(
        self,
    ) -> None:
        upgrade = FakeUpgrade(self.directory, failure="migrate")
        with self.assertRaises(UpgradeError):
            upgrade.apply()
        assert upgrade.state_file is not None
        config = Path(str(upgrade.state["compose_file"]))
        self.assertEqual(config.stat().st_mode & 0o777, 0o600)
        upgrade.env_file.write_text("HERMES_DATABASE_URL=wrong-database\n")
        upgrade.files[0].write_text("invalid mutable compose file")
        commands: list[list[str]] = []

        def docker(arguments: list[str], **keywords: object) -> str:
            commands.append(arguments)
            if arguments[:2] == ["docker", "compose"]:
                self.assertEqual(arguments[arguments.index("--file") + 1], str(config))
                if "restore" in arguments:
                    saved = json.loads(config.read_text())
                    self.assertEqual(
                        saved["services"]["api"]["environment"]["HERMES_DATABASE_URL"],
                        "sqlite+aiosqlite:////app/data/original.sqlite",
                    )
                    self.assertEqual(
                        saved["services"]["api"]["environment"]["HERMES_SECRET_KEY"],
                        "literal$$dollar",
                    )
            return ""

        with patch("scripts.upgrade.run", side_effect=docker), patch.dict(
            os.environ, {"HERMES_DATABASE_URL": "another-wrong-database"}
        ):
            recover(upgrade.state_file, restore=True)
        self.assertTrue(any("restore" in arguments for arguments in commands))

    def test_recovery_refuses_missing_configuration_before_running_docker(self) -> None:
        upgrade = FakeUpgrade(self.directory, failure="migrate")
        with self.assertRaises(UpgradeError):
            upgrade.apply()
        assert upgrade.state_file is not None
        Path(str(upgrade.state["compose_file"])).unlink()
        with patch("scripts.upgrade.run") as docker, self.assertRaisesRegex(
            UpgradeError, "saved resolved Compose"
        ):
            recover(upgrade.state_file, restore=True)
        docker.assert_not_called()

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

    def test_failed_abort_cleanup_keeps_publishers_stopped_and_can_be_retried(
        self,
    ) -> None:
        for failure in ("resume", "maintenance"):
            with self.subTest(failure=failure):
                upgrade = FakeUpgrade(self.directory, failure="backup")
                with self.assertRaises(UpgradeError):
                    upgrade.apply()
                assert upgrade.state_file is not None
                commands: list[list[str]] = []
                cleanup_failed = False

                def docker(arguments: list[str], **keywords: object) -> str:
                    nonlocal cleanup_failed
                    commands.append(arguments)
                    if "ps" in arguments:
                        return "celery_worker"
                    if failure in arguments and not cleanup_failed:
                        cleanup_failed = True
                        raise UpgradeError("Injected cleanup failure")
                    return ""

                with patch("scripts.upgrade.run", side_effect=docker):
                    with self.assertRaisesRegex(UpgradeError, "cleanup failure"):
                        recover(upgrade.state_file, restore=False)
                    self.assertFalse(any("start" in args for args in commands))
                    self.assertEqual(
                        json.loads(upgrade.state_file.read_text())["phase"],
                        "aborting",
                    )
                    recover(upgrade.state_file, restore=False)
                self.assertTrue(any("start" in args for args in commands))
                self.assertEqual(
                    json.loads(upgrade.state_file.read_text())["phase"],
                    "aborted-before-migration",
                )

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

    def test_recovery_pins_the_recorded_project_despite_current_environment(
        self,
    ) -> None:
        upgrade = FakeUpgrade(self.directory, failure="migrate")
        with self.assertRaises(UpgradeError):
            upgrade.apply()
        assert upgrade.state_file is not None
        commands: list[list[str]] = []

        def docker(arguments: list[str], **keywords: object) -> str:
            commands.append(arguments)
            if arguments[:2] == ["docker", "compose"]:
                self.assertEqual(
                    arguments[arguments.index("--project-name") + 1], "test-project"
                )
            return ""

        with patch("scripts.upgrade.run", side_effect=docker), patch.dict(
            os.environ, {"COMPOSE_PROJECT_NAME": "wrong-project"}
        ):
            recover(upgrade.state_file, restore=True)
        self.assertTrue(any("restore" in arguments for arguments in commands))
        self.assertEqual(
            json.loads(upgrade.state_file.read_text())["phase"], "recovered"
        )

    def test_interrupted_recovery_resumes_without_restoring_database_twice(
        self,
    ) -> None:
        upgrade = FakeUpgrade(self.directory, failure="migrate")
        with self.assertRaises(UpgradeError):
            upgrade.apply()
        assert upgrade.state_file is not None
        commands: list[list[str]] = []
        fail_start = True

        def docker(arguments: list[str], **keywords: object) -> str:
            nonlocal fail_start
            commands.append(arguments)
            if "up" in arguments and fail_start:
                fail_start = False
                raise UpgradeError("synthetic recovery startup failure")
            return ""

        with patch("scripts.upgrade.run", side_effect=docker):
            with self.assertRaisesRegex(UpgradeError, "recovery startup failure"):
                recover(upgrade.state_file, restore=True)
            self.assertEqual(
                json.loads(upgrade.state_file.read_text())["phase"], "restored"
            )
            recover(upgrade.state_file, restore=False)
        self.assertEqual(sum("restore" in arguments for arguments in commands), 1)

    def test_sigterm_is_deferred_until_a_safe_abort(self) -> None:
        class Interrupted(FakeUpgrade):
            def drain(self) -> None:
                os.kill(os.getpid(), signal.SIGTERM)
                self.check_stop()

        upgrade = Interrupted(self.directory)
        with defer_signals(upgrade), self.assertRaisesRegex(
            UpgradeError, "interrupted"
        ):
            upgrade.apply()
        self.assertEqual(upgrade.state["phase"], "aborted-before-migration")
        self.assertIn(("start", *SERVICES), upgrade.actions)
        self.assertNotIn(("helper", "migrate"), upgrade.actions)

    def test_hard_kill_before_backup_can_resume_without_restoring_data(self) -> None:
        program = """
import os, signal, sys
from pathlib import Path
from unittest.mock import patch
from test_upgrade import FakeUpgrade, inspect_output
from scripts.upgrade import upgrade_lock
class Interrupted(FakeUpgrade):
    def drain(self):
        self.queues = ["hermes.downloads"]
        self.save(queues=self.queues)
        Path(self.env_file.parent / "maintenance").touch()
        os.kill(os.getpid(), signal.SIGKILL)
with patch("scripts.upgrade.run", side_effect=inspect_output):
    upgrade = Interrupted(Path(sys.argv[1]))
    with upgrade_lock(upgrade.env_file.parent):
        upgrade.apply()
"""
        environment = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join((str(ROOT), str(ROOT / "tests/infra"))),
        }
        process = subprocess.run(
            [sys.executable, "-c", program, str(self.directory)],
            env=environment,
            capture_output=True,
            text=True,
        )
        self.assertEqual(process.returncode, -signal.SIGKILL, process.stderr)
        state_file = next((self.directory / ".hermes-upgrades").glob("*/state.json"))
        self.assertEqual(json.loads(state_file.read_text())["phase"], "draining")
        commands: list[list[str]] = []

        def docker(arguments: list[str], **keywords: object) -> str:
            commands.append(arguments)
            if "ps" in arguments:
                return "celery_worker"
            if "maintenance" in arguments and "off" in arguments:
                (self.directory / "maintenance").unlink()
            return ""

        with patch("scripts.upgrade.run", side_effect=docker):
            recover(state_file, restore=False)
        self.assertFalse((self.directory / "maintenance").exists())
        self.assertFalse(
            any(
                "restore" in arguments or "migrate" in arguments
                for arguments in commands
            )
        )
        self.assertTrue(any("start" in arguments for arguments in commands))
        self.assertEqual(
            json.loads(state_file.read_text())["phase"], "aborted-before-migration"
        )

    def test_terminal_interrupt_does_not_kill_the_current_child_operation(self) -> None:
        self.assert_child_operation_finishes(signal.SIGINT)

    def test_disconnected_stderr_does_not_interrupt_the_current_child_operation(
        self,
    ) -> None:
        self.assert_child_operation_finishes(signal.SIGHUP, close_stderr=True)

    def assert_child_operation_finishes(
        self, interruption: signal.Signals, *, close_stderr: bool = False
    ) -> None:
        program = """
import os, sys
from pathlib import Path
from scripts.upgrade import Upgrade, UpgradeError, defer_signals, run
directory = Path(sys.argv[1])
if sys.argv[2] == "True":
    os.close(2)
upgrade = Upgrade([], directory / ".env", "1.2.3", 1)
child = "import sys, time; from pathlib import Path; p = Path(sys.argv[1]); (p/'started').touch(); time.sleep(1); (p/'finished').touch()"
with defer_signals(upgrade):
    run([sys.executable, "-c", child, str(directory)])
    try:
        upgrade.check_stop()
    except UpgradeError:
        (directory / "safe-checkpoint").touch()
"""
        environment = {**os.environ, "PYTHONPATH": str(ROOT)}
        process = subprocess.Popen(
            [sys.executable, "-c", program, str(self.directory), str(close_stderr)],
            env=environment,
            start_new_session=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            deadline = time.monotonic() + 10
            while (
                not (self.directory / "started").exists()
                and time.monotonic() < deadline
            ):
                if process.poll() is not None:
                    self.fail(str(process.communicate()))
                time.sleep(0.01)
            self.assertTrue((self.directory / "started").exists())
            os.killpg(process.pid, interruption)
            output, error = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, (output, error))
            self.assertTrue((self.directory / "finished").exists())
            self.assertTrue((self.directory / "safe-checkpoint").exists())
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

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
