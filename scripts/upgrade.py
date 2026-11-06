#!/usr/bin/env python3
"""Safely upgrade a running, single-worker Hermes Compose release."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import FrameType
from typing import Iterator, TypedDict

SERVICES = ("api", "celery_worker", "celery_beat", "app")
PRE_MIGRATION_PHASES = {
    "prepared",
    "draining",
    "backing-up",
    "backed-up",
    "aborting",
    "aborted-before-migration",
}
# Sent to the EXISTING worker: upgrades must not depend on new code being installed.
# Stop publishers first, empty its queues, pause consumption, then check again.
WORKER_CONTROL = """
import json, socket, sys
from app.tasks.celery_app import celery_app
from kombu.exceptions import ChannelError
action, saved = sys.argv[1], json.loads(sys.argv[2])
inspection = celery_app.control.inspect(timeout=5)
queues = inspection.active_queues()
if not queues or len(queues) != 1:
    raise RuntimeError("Upgrade requires exactly one reachable, managed worker")
node = next(iter(queues))
if not node.endswith("@" + socket.gethostname()):
    raise RuntimeError("An unmanaged worker is connected; drain it separately")
inspection = celery_app.control.inspect(destination=[node], timeout=5)
names = saved or [queue["name"] for queue in queues[node]]
if action in ("pause", "resume"):
    operation = celery_app.control.cancel_consumer if action == "pause" else celery_app.control.add_consumer
    for name in names:
        replies = operation(name, destination=[node], reply=True, timeout=5)
        if not replies or any("error" in reply.get(node, {}) for reply in replies):
            raise RuntimeError("Worker did not acknowledge consumer change")
else:
    busy = 0
    for method in ("active", "reserved", "scheduled"):
        replies = getattr(inspection, method)()
        if not replies or node not in replies:
            raise RuntimeError("Worker did not report its running tasks")
        busy += len(replies[node])
    with celery_app.connection_for_read() as connection:
        channel = connection.channel()
        for name in names:
            try:
                busy += channel.queue_declare(queue=name, passive=True).message_count
            except ChannelError as error:
                # Redis removes empty list keys. Missing queues are empty;
                # permission/protocol errors must still stop the upgrade.
                if str(error.reply_code) != "404":
                    raise
    print(json.dumps({"busy": busy, "queues": names}))
"""


class UpgradeError(RuntimeError):
    pass


class WorkerState(TypedDict):
    busy: int
    queues: list[str]


def validate_storage(
    environment: dict[str, str],
    old_environment: list[str],
    mounts: dict[str, str],
    old_mounts: dict[str, str],
) -> None:
    old = dict(item.split("=", 1) for item in old_environment if "=" in item)
    defaults = {
        "HERMES_DATABASE_URL": "sqlite+aiosqlite:///./data/hermes.db",
        "HERMES_REDIS_URL": "redis://redis:6379/0",
        "HERMES_DOWNLOAD_DIR": "./downloads",
        "HERMES_TEMP_DIR": "./temp",
    }
    for key, default in defaults.items():
        if environment.get(key, default) != old.get(key, default):
            raise UpgradeError(
                f"{key} differs from the running installation; move storage or brokers separately"
            )
    for target in ("/app/data", "/app/downloads", "/app/temp"):
        if target not in mounts or mounts.get(target) != old_mounts.get(target):
            raise UpgradeError(
                f"Storage mount {target} differs from the running installation"
            )


def run(arguments: list[str], *, environment: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        arguments,
        env=environment,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    if result.returncode:
        raise UpgradeError(
            f"Command failed: {shlex.join(arguments[:3])}\n{result.stderr.strip()}"
        )
    return result.stdout


@contextmanager
def upgrade_lock(project: Path) -> Iterator[None]:
    with (project / ".hermes-upgrade.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise UpgradeError(
                "Another upgrade or recovery is already running"
            ) from None
        yield


@contextmanager
def defer_signals(upgrade: Upgrade) -> Iterator[None]:
    """Finish the current Docker operation before cancelling at a checkpoint."""

    def request_stop(number: int, frame: FrameType | None) -> None:
        if not upgrade.stop_requested:
            os.write(
                2,
                b"Cancellation requested; finishing the current step before cleanup.\n",
            )
        upgrade.stop_requested = True

    previous = {
        number: signal.signal(number, request_stop)
        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    }
    try:
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


class Upgrade:
    def __init__(
        self,
        files: list[Path],
        env_file: Path,
        version: str,
        timeout: int,
        *,
        project: str | None = None,
    ) -> None:
        self.files = [file.resolve() for file in files]
        self.env_file = env_file.resolve()
        self.version = version
        self.timeout = timeout
        self.environment = {**os.environ, "HERMES_IMAGE_TAG": version}
        self.state: dict[str, object] = {}
        self.state_file: Path | None = None
        self.queues: list[str] = []
        self.project = project
        self.stop_requested = False

    def compose(self, *arguments: str) -> str:
        command = ["docker", "compose", "--env-file", str(self.env_file)]
        if self.project is not None:
            command.extend(["--project-name", self.project])
        for file in self.files:
            command.extend(["--file", str(file)])
        return run([*command, *arguments], environment=self.environment)

    def helper(self, *arguments: str) -> str:
        return self.compose(
            "run",
            "--rm",
            "--no-deps",
            "--entrypoint",
            "python",
            "api",
            "-m",
            "app.manage",
            *arguments,
        )

    def save(self, **changes: object) -> None:
        self.state.update(changes)
        if self.state_file:
            temporary = self.state_file.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.state, indent=2) + "\n")
            temporary.replace(self.state_file)

    def worker(self, action: str) -> WorkerState:
        output = self.compose(
            "exec",
            "-T",
            "celery_worker",
            "python",
            "-c",
            WORKER_CONTROL,
            action,
            json.dumps(self.queues),
        )
        result: WorkerState = (
            json.loads(output)
            if action == "probe"
            else {"busy": 0, "queues": self.queues}
        )
        return result

    def drain(self) -> None:
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            result = self.worker("probe")
            self.check_stop()
            if not self.queues:
                self.queues = list(result["queues"])
                self.save(queues=self.queues)
            if result["busy"] == 0:
                self.worker("pause")
                if self.worker("probe")["busy"] == 0:
                    self.check_stop()
                    return
                self.worker("resume")
            time.sleep(2)
        raise UpgradeError(
            "Drain timed out; existing work was preserved and no migration ran"
        )

    def check_stop(self) -> None:
        if self.stop_requested:
            raise UpgradeError("Upgrade interrupted at a safe checkpoint")

    def abort_before_migration(self) -> None:
        self.save(phase="aborting")
        # Keep publishers stopped if consumers or maintenance cannot be restored.
        # The durable aborting phase lets recovery retry these steps safely.
        running = self.compose("ps", "--status", "running", "--services").split()
        if "celery_worker" in running and self.queues:
            self.worker("resume")
        self.helper("maintenance", "off")
        # Reuse the original containers and their configured consumers.
        self.compose("start", *SERVICES)
        self.save(phase="aborted-before-migration")

    def preflight(self, pull: bool) -> dict[str, str]:
        config = json.loads(self.compose("config", "--format", "json"))
        self.project = config["name"]
        images: dict[str, str] = {}
        for name in SERVICES:
            service = config["services"][name]
            image = service.get("image", "")
            if not image.endswith(":" + self.version):
                raise UpgradeError(
                    "Use matching, exact release images for all four application services"
                )
            if "build" in service:
                raise UpgradeError(
                    "The upgrade command requires a prebuilt release Compose file"
                )
            images[name] = image
        if any(
            images[name] != images["api"] for name in ("celery_worker", "celery_beat")
        ):
            raise UpgradeError(
                "API, worker and scheduler must use the same backend image"
            )
        api_id = self.compose("ps", "--quiet", "api").strip()
        if not api_id or "\n" in api_id:
            raise UpgradeError("Expected one running API container")
        previous = json.loads(run(["docker", "inspect", api_id]))[0]
        for name in ("api", "celery_worker", "celery_beat"):
            service = config["services"][name]
            validate_storage(
                service.get("environment", {}),
                previous["Config"]["Env"],
                {
                    volume["target"]: volume["source"]
                    for volume in service.get("volumes", [])
                },
                {
                    volume["Destination"]: volume["Source"]
                    for volume in previous["Mounts"]
                },
            )
        if pull:
            print(
                "Pulling the selected release while the current version keeps running...",
                flush=True,
            )
            self.compose("pull", *SERVICES)
        metadata = json.loads(self.helper("preflight"))
        if metadata["version"] != self.version:
            raise UpgradeError(
                "Selected backend image does not identify itself as the requested release"
            )
        # Probe without changing consumers or data; refuse unknown/external workers.
        self.worker("probe")
        return images

    def apply(self, *, pull: bool = True) -> None:
        images = self.preflight(pull)
        self.check_stop()
        if not self.project:
            raise UpgradeError("Compose project identity could not be resolved")
        existing: dict[str, object] = {}
        for name in SERVICES:
            ids = self.compose("ps", "--all", "--quiet", name).split()
            if len(ids) != 1:
                raise UpgradeError(f"Expected one existing {name} container")
            details = json.loads(run(["docker", "inspect", ids[0]]))[0]
            if not details["State"]["Running"]:
                raise UpgradeError(
                    f"Start the current {name} container before upgrading"
                )
            configuration = details["Config"]
            previous: dict[str, object] = {
                "image": details["Image"],
                "command": configuration["Cmd"],
                "entrypoint": configuration["Entrypoint"],
                "environment": dict(
                    item.split("=", 1) for item in configuration["Env"] if "=" in item
                ),
            }
            health = configuration.get("Healthcheck")
            if health:
                previous["healthcheck"] = {
                    "test": health["Test"],
                    **{
                        field: f"{health[key]}ns"
                        for field, key in (
                            ("interval", "Interval"),
                            ("timeout", "Timeout"),
                            ("start_period", "StartPeriod"),
                            ("start_interval", "StartInterval"),
                        )
                        if health.get(key)
                    },
                    "retries": health.get("Retries", 3),
                }
            else:
                previous["healthcheck"] = {"disable": True}
            existing[name] = previous
        identifier = (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
            + uuid.uuid4().hex[:8]
        )
        directory = self.env_file.parent / ".hermes-upgrades" / identifier
        directory.mkdir(parents=True, mode=0o700)
        directory.parent.chmod(0o700)
        self.state_file = directory / "state.json"
        previous_env = directory / "previous.env"
        previous_env.write_bytes(self.env_file.read_bytes())
        previous_env.chmod(0o600)
        previous_images = directory / "previous-services.json"
        previous_images.write_text(
            json.dumps({"services": existing}).replace("$", "$$")
        )
        previous_images.chmod(0o600)
        backup = f"/app/data/backups/{identifier}"
        self.save(
            version=self.version,
            project_name=self.project,
            files=[str(file) for file in self.files],
            env_file=str(self.env_file),
            backup_directory=backup,
            phase="prepared",
        )
        print(f"Recovery record: {self.state_file}", flush=True)
        try:
            self.check_stop()
            print(
                "Pausing requests and scheduling; waiting for queued and active work...",
                flush=True,
            )
            self.compose("stop", "--timeout", "60", "app", "api", "celery_beat")
            self.save(phase="draining")
            self.helper("maintenance", "on")
            self.check_stop()
            self.drain()
            self.compose("stop", "--timeout", "60", "celery_worker")
            self.save(phase="backing-up")
            self.check_stop()
            snapshot = json.loads(self.helper("backup", backup))["snapshot"]
            self.save(snapshot=snapshot, phase="backed-up")
            self.check_stop()
            self.save(phase="migrating")
            print("Backup complete. Applying database migrations once...", flush=True)
            self.helper("migrate")
            self.check_stop()
            self.save(phase="starting")
            self.compose(
                "up",
                "--detach",
                "--no-deps",
                "--wait",
                "--wait-timeout",
                "180",
                "api",
                "celery_worker",
                "app",
            )
            self.helper("check-schema")
            self.check_stop()
            # Compose health checks verify readiness and worker reachability. Also
            # reject stale containers, even if an old build answers health checks.
            for name in ("api", "celery_worker", "app"):
                container = self.compose("ps", "--quiet", name).strip()
                actual = json.loads(run(["docker", "inspect", container]))[0]["Image"]
                expected = json.loads(
                    run(["docker", "image", "inspect", images[name]])
                )[0]["Id"]
                if actual != expected:
                    raise UpgradeError(f"{name} did not start the selected image")
            self.compose(
                "up",
                "--detach",
                "--no-deps",
                "--wait",
                "--wait-timeout",
                "60",
                "celery_beat",
            )
            self.check_stop()
            self.persist_version()
            self.helper("maintenance", "off")
            self.save(phase="complete")
            print(
                f"Hermes {self.version} is ready. Backup retained at {backup}.",
                flush=True,
            )
        except BaseException:
            if self.state.get("phase") in PRE_MIGRATION_PHASES:
                self.abort_before_migration()
            else:
                try:
                    self.helper("maintenance", "on")
                finally:
                    try:
                        self.compose(
                            "stop", "--timeout", "60", "app", "api", "celery_beat"
                        )
                    finally:
                        print(
                            "Upgrade stopped. Keep services offline until recovery or a forward fix.\n"
                            f"Recovery: python3 scripts/upgrade.py --recover {shlex.quote(str(self.state_file))} --restore-database",
                            file=sys.stderr,
                            flush=True,
                        )
            raise

    def persist_version(self) -> None:
        lines = self.env_file.read_text().splitlines()
        lines = [
            line
            for line in lines
            if not re.match(r"\s*(?:export\s+)?HERMES_IMAGE_TAG\s*=", line)
        ]
        temporary = self.env_file.with_name(self.env_file.name + ".upgrade-tmp")
        temporary.write_text(
            "\n".join([*lines, f"HERMES_IMAGE_TAG={self.version}"]) + "\n"
        )
        temporary.chmod(self.env_file.stat().st_mode & 0o777)
        temporary.replace(self.env_file)


def recover(state_file: Path, *, restore: bool) -> None:
    state_file = state_file.resolve()
    state = json.loads(state_file.read_text())
    before_migration = state["phase"] in PRE_MIGRATION_PHASES
    if before_migration and restore:
        raise UpgradeError(
            "No migration ran; omit --restore-database to resume the original services"
        )
    if (
        not before_migration
        and state["phase"] != "restored"
        and (not restore or not state.get("snapshot"))
    ):
        raise UpgradeError(
            "Recovery requires a completed backup and --restore-database; it replaces current database contents"
        )
    if state["phase"] in {"complete", "recovered"}:
        raise UpgradeError(
            "This upgrade completed; restoring its snapshot could discard new writes. Use the manual recovery procedure"
        )
    upgrade = Upgrade(
        [Path(file) for file in state["files"]],
        Path(state["env_file"]),
        state["version"],
        900,
        project=state.get("project_name"),
    )
    if not upgrade.project:
        raise UpgradeError(
            "Recovery record has no Compose project identity; use manual recovery"
        )
    upgrade.state, upgrade.state_file = state, state_file
    upgrade.queues = state.get("queues", [])
    with defer_signals(upgrade), upgrade_lock(upgrade.env_file.parent):
        if before_migration:
            upgrade.abort_before_migration()
            print("Original services resumed. No database restore was needed.")
            return
        previous = json.loads(
            (state_file.parent / "previous-services.json").read_text()
        )
        for service in previous["services"].values():
            # Fail before replacing the database if recorded images were pruned.
            run(["docker", "image", "inspect", service["image"]])
        if state["phase"] != "restored":
            # A failed startup may already have started workers; drain them too.
            running = upgrade.compose("ps", "--status", "running", "--services").split()
            upgrade.compose("stop", "--timeout", "60", "app", "api", "celery_beat")
            if "celery_worker" in running:
                upgrade.drain()
                upgrade.compose("stop", "--timeout", "60", "celery_worker")
            upgrade.check_stop()
            upgrade.helper("restore", state["snapshot"], "--confirm-stopped")
            upgrade.save(phase="restored")
        upgrade.check_stop()
        upgrade.helper("maintenance", "off")
        upgrade.env_file.write_bytes((state_file.parent / "previous.env").read_bytes())
        upgrade.files.append(state_file.parent / "previous-services.json")
        upgrade.compose(
            "up", "--detach", "--no-deps", "--wait", "--wait-timeout", "180", *SERVICES
        )
        upgrade.save(phase="recovered")
        print(
            "Previous images and database snapshot restored. Any writes after the snapshot were discarded."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?")
    parser.add_argument("--file", action="append", type=Path, dest="files")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument(
        "--drain-timeout",
        type=int,
        default=900,
        help="Seconds before safely abandoning the upgrade",
    )
    parser.add_argument(
        "--skip-pull",
        action="store_true",
        help="Use already-loaded release images (offline installs)",
    )
    parser.add_argument("--recover", type=Path)
    parser.add_argument(
        "--restore-database",
        action="store_true",
        help="Explicitly allow recovery to replace the database",
    )
    args = parser.parse_args()
    try:
        if args.recover:
            recover(args.recover, restore=args.restore_database)
            return
        if (
            not args.version
            or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", args.version)
            or args.drain_timeout < 1
        ):
            parser.error("Supply an exact X.Y.Z release and a positive drain timeout")
        upgrade = Upgrade(
            args.files or [Path("docker-compose.example.yml")],
            args.env_file,
            args.version,
            args.drain_timeout,
        )
        with defer_signals(upgrade), upgrade_lock(upgrade.env_file.parent):
            upgrade.apply(pull=not args.skip_pull)
    except (UpgradeError, OSError, KeyboardInterrupt) as error:
        print(f"Upgrade failed: {error}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
