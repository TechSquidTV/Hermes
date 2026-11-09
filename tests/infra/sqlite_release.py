"""Rehearse SQLite releases on a Docker volume, never a host-shared database.

Only inert checkpoint archives and this script cross the Docker boundary.
All SQLite readers, writers, integrity checks and restores run inside Linux.
Failed runs retain their stopped containers and volume for private diagnosis.
"""

import argparse
import asyncio
import concurrent.futures
import hashlib
import json
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import time
import urllib.request
import uuid
from contextlib import closing
from pathlib import Path
from typing import TypedDict, cast

ROOT = Path("/rehearsal")


class Snapshot(TypedDict):
    columns: dict[str, list[str]]
    tables: dict[str, list[str]]
    files: dict[str, str]


def extract_checkpoint(archive_path: Path, destination: Path) -> None:
    """Restore GNU sparse names before applying the safe extraction filter."""
    destination.mkdir(parents=True)
    with tarfile.open(archive_path) as archive:
        for member in archive:
            # GNU sparse 1.0 stores the canonical path separately; a PAX path
            # may otherwise override it with the temporary GNUSparseFile name.
            member.name = member.pax_headers.get("GNU.sparse.name", member.name)
            archive.extract(member, destination, filter="data")


def encode_blob(value: object) -> str:
    if isinstance(value, bytes):
        return value.hex()
    raise TypeError(f"Unexpected database value: {type(value).__name__}")


def snapshot(directory: Path, columns: dict[str, list[str]] | None = None) -> Snapshot:
    with closing(sqlite3.connect(directory / "config/hermes.db")) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        if columns is None:
            names = [
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%' AND name!='alembic_version'"
                )
            ]
            columns = {
                name: [
                    row[1] for row in connection.execute(f'PRAGMA table_info("{name}")')
                ]
                for name in names
            }
        tables = {}
        for name, fields in columns.items():
            quoted = ",".join('"' + field + '"' for field in fields)
            tables[name] = sorted(
                hashlib.sha256(
                    json.dumps(row, default=encode_blob).encode()
                ).hexdigest()
                for row in connection.execute(f'SELECT {quoted} FROM "{name}"')
            )
    files = {}
    for name in ("downloads", "temp"):
        for path in (directory / name).rglob("*"):
            assert not path.is_symlink(), "Review checkpoint symlinks before rehearsal"
            if path.is_file():
                with path.open("rb") as stream:
                    files[str(path.relative_to(directory))] = hashlib.file_digest(
                        stream, "sha256"
                    ).hexdigest()
    return {"columns": columns, "tables": tables, "files": files}


def verify(directory: Path, baseline_file: Path, *, exact: bool) -> None:
    baseline = cast(Snapshot, json.loads(baseline_file.read_text()))
    actual = snapshot(directory, baseline["columns"])
    assert actual["files"] == baseline["files"], "Original file checksums changed"
    for name, rows in baseline["tables"].items():
        assert set(rows) <= set(
            actual["tables"][name]
        ), f"Original rows changed: {name}"
        if exact or name not in ("users", "token_blacklist"):
            assert rows == actual["tables"][name], f"Unexpected writes: {name}"


def stress_auth() -> None:
    from app.core.security import get_password_hash
    from app.db.base import async_session_maker, engine
    from app.db.models import User

    password = secrets.token_urlsafe(30)

    async def setup() -> None:
        try:
            async with async_session_maker() as session:
                session.add(
                    User(
                        id=str(uuid.uuid4()),
                        username="isolated-rehearsal",
                        email="rehearsal@example.test",
                        password_hash=get_password_hash(password),
                        is_active=True,
                        is_admin=False,
                    )
                )
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.run(setup())

    def request(route: str, data: dict[str, str]) -> dict[str, str]:
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/v1/auth/" + route,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            assert response.status == 200
            return cast(dict[str, str], json.load(response))

    def work(_: int) -> int:
        for _ in range(8):
            pair = request(
                "login", {"username": "isolated-rehearsal", "password": password}
            )
            request("refresh", {"refreshToken": pair["refreshToken"]})
        return 16

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(work, range(4))) == 64


def stress_transactions() -> None:
    from sqlalchemy import text

    from app.db.base import async_session_maker
    from app.tasks.runtime import run_async_task

    path = Path("/app/data/hermes.db")
    with closing(sqlite3.connect(path)) as reader:
        assert reader.execute("PRAGMA journal_mode").fetchone() == ("wal",)
        reader.execute("CREATE TABLE rehearsal_probe (value INTEGER NOT NULL)")
        reader.execute("INSERT INTO rehearsal_probe VALUES (0)")
        reader.commit()
        reader.execute("BEGIN")
        reader.execute("SELECT value FROM rehearsal_probe").fetchall()

        async def operation(outcome: str) -> None:
            async with async_session_maker() as session:
                await session.execute(text("UPDATE rehearsal_probe SET value=value+1"))
                if outcome == "error":
                    raise ValueError("synthetic task failure")
                if outcome == "cancel":
                    task = asyncio.current_task()
                    assert task is not None
                    task.cancel()
                    await asyncio.sleep(0)
                await session.commit()

        for _ in range(20):
            for outcome in ("success", "error", "cancel"):
                try:
                    run_async_task(operation(outcome))
                except (ValueError, asyncio.CancelledError):
                    assert outcome != "success"
                with closing(sqlite3.connect(path, timeout=1)) as independent:
                    independent.execute("UPDATE rehearsal_probe SET value=value")
                    independent.commit()
        reader.rollback()
        assert reader.execute("SELECT value FROM rehearsal_probe").fetchone() == (20,)
        reader.execute("DROP TABLE rehearsal_probe")
        reader.commit()


def probe(action: str, phase: str) -> None:
    """Executed exclusively inside a Linux container on the named volume."""
    directory = ROOT / phase / "hermes"
    if action == "unpack":
        extract_checkpoint(ROOT / "checkpoint.tar", ROOT / "original")
    elif action == "seed":
        for name in ("config", "downloads", "temp", "redis"):
            (directory / name).mkdir(parents=True)
        with closing(sqlite3.connect(directory / "config/hermes.db")) as connection:
            connection.executescript((ROOT / "seed.sql").read_text())
            connection.execute(
                "UPDATE download_files SET filepath='/app/downloads/legacy.mp4'"
            )
            connection.execute(
                "UPDATE downloads SET output_path='/app/downloads/legacy.mp4'"
            )
            connection.commit()
        (directory / "downloads/legacy.mp4").write_bytes(b"legacy-media")
    elif action == "prepare":
        shutil.copytree(ROOT / "original/hermes", directory)
        for name in ("config", "downloads", "temp", "redis"):
            (directory / name).mkdir(exist_ok=True)
    elif action == "baseline":
        (ROOT / "baseline.json").write_text(json.dumps(snapshot(directory)))
    elif action == "verify":
        verify(
            directory, ROOT / "baseline.json", exact=phase in ("before", "restored-old")
        )
    elif action == "upgraded-baseline":
        (ROOT / "upgraded.json").write_text(json.dumps(snapshot(directory)))
    elif action == "verify-restored":
        verify(directory, ROOT / "upgraded.json", exact=True)
    elif action == "auth":
        stress_auth()
    elif action == "transactions":
        stress_transactions()
    elif action == "runtime":
        assert sqlite3.sqlite_version == "3.54.1", sqlite3.sqlite_version
        with closing(sqlite3.connect(":memory:")) as connection:
            print(
                json.dumps(
                    {
                        "sqlite": sqlite3.sqlite_version,
                        "source_id": connection.execute(
                            "SELECT sqlite_source_id()"
                        ).fetchone()[0],
                    }
                )
            )
    else:
        raise ValueError(action)


def rehearse(args: argparse.Namespace) -> None:
    evidence = Path(args.evidence).resolve()
    evidence.mkdir(mode=0o700, parents=True, exist_ok=False)
    identity = "hermes-sqlite-" + uuid.uuid4().hex[:10]
    script = Path(__file__).resolve()
    created: list[str] = []
    passed = False

    def docker(*command: str, timeout: int = 180, include_stderr: bool = False) -> str:
        result = subprocess.run(
            ["docker", *command],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if include_stderr else subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        if result.returncode:
            log = evidence / "last-command.private.log"
            log.write_text(result.stdout + (result.stderr or ""))
            log.chmod(0o600)
            raise RuntimeError(f"Rehearsal failed; inspect {log}")
        return result.stdout

    images = {
        name: docker(
            "image",
            "inspect",
            reference,
            "--format",
            "{{.Id}} {{.Os}}/{{.Architecture}}",
        )
        .strip()
        .split()
        for name, reference in (
            ("old-api", args.old_api_image),
            ("old-app", args.old_app_image),
            ("api", args.api_image),
            ("app", args.app_image),
            ("redis", args.redis_image),
        )
    }
    for name, (_, platform) in images.items():
        assert platform == args.platform, f"Wrong image platform: {name}: {platform}"
    checkpoint = (
        Path(args.checkpoint)
        if args.checkpoint
        else script.parents[2] / "packages/hermes-api/tests/fixtures/v0.6.0.sqlite.sql"
    )
    with checkpoint.open("rb") as stream:
        checkpoint_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    docker("volume", "create", identity)
    docker("network", "create", "--internal", identity)
    volume = ("--mount", f"type=volume,source={identity},target=/rehearsal")
    helper = identity + "-helper"
    docker(
        "run",
        "-d",
        "--name",
        helper,
        "--network",
        "none",
        "--platform",
        args.platform,
        "--user",
        "0:0",
        *volume,
        "--entrypoint",
        "sleep",
        images["api"][0],
        "infinity",
    )
    created.append(helper)

    def check(action: str, phase: str, container: str = helper) -> str:
        return docker(
            "exec", container, "python", "/rehearsal/probe.py", "--probe", action, phase
        )

    def mounts(phase: str) -> list[str]:
        result = list(volume)
        for name, target in (
            ("config", "data"),
            ("downloads", "downloads"),
            ("temp", "temp"),
        ):
            result += [
                "--mount",
                f"type=volume,source={identity},target=/app/{target},volume-subpath={phase}/hermes/{name}",
            ]
        return result

    def wait(container: str, *command: str) -> None:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            result = subprocess.run(
                ["docker", "exec", container, *command], capture_output=True, timeout=15
            )
            if result.returncode == 0:
                return
            time.sleep(1)
        raise RuntimeError(f"Readiness timed out: {container}")

    phases = []
    try:
        docker("cp", str(script), helper + ":/rehearsal/probe.py")
        runtime = json.loads(check("runtime", "original"))
        if args.checkpoint:
            docker(
                "cp",
                str(Path(args.checkpoint).resolve()),
                helper + ":/rehearsal/checkpoint.tar",
            )
            check("unpack", "original")
        else:
            fixture = (
                script.parents[2]
                / "packages/hermes-api/tests/fixtures/v0.6.0.sqlite.sql"
            )
            docker("cp", str(fixture), helper + ":/rehearsal/seed.sql")
            check("seed", "original")
        check("baseline", "original")
        # Permissions change only on the isolated copy, never the original checkpoint.
        docker("exec", helper, "chown", "-R", "1000:1000", "/rehearsal")
        secret = secrets.token_urlsafe(48)
        for phase, version in (
            ("before", "old-"),
            ("upgrade", ""),
            ("restored-new", ""),
            ("restored-old", "old-"),
        ):
            check("prepare", phase)
            docker("exec", helper, "chown", "-R", "1000:1000", f"/rehearsal/{phase}")
            names = {
                name: f"{identity}-{phase}-{name}"
                for name in ("api", "app", "worker", "redis")
            }
            common = ["--platform", args.platform, "--network", identity]
            env = [
                "-e",
                "HERMES_SECRET_KEY=" + secret,
                "-e",
                "HERMES_DATABASE_URL=sqlite+aiosqlite:////app/data/hermes.db",
                "-e",
                "HERMES_DOWNLOAD_DIR=/app/downloads",
                "-e",
                "HERMES_TEMP_DIR=/app/temp",
                "-e",
                "HERMES_REDIS_URL=redis://" + names["redis"] + ":6379",
                "-e",
                "HERMES_ENABLE_RATE_LIMITING=false",
            ]
            if phase == "restored-new":
                docker(
                    "run",
                    "--rm",
                    *common,
                    *env,
                    *mounts(phase),
                    "--entrypoint",
                    "python",
                    images["api"][0],
                    "-m",
                    "app.manage",
                    "restore",
                    "/rehearsal/upgrade/hermes/config/backups/rehearsal/database.sqlite",
                    "--confirm-stopped",
                )
            docker(
                "run",
                "-d",
                "--name",
                names["redis"],
                *common,
                "--mount",
                f"type=volume,source={identity},target=/data,volume-subpath={phase}/hermes/redis",
                images["redis"][0],
                "redis-server",
                "--appendonly",
                "yes",
                "--maxmemory-policy",
                "noeviction",
            )
            created.append(names["redis"])
            docker(
                "run",
                "-d",
                "--name",
                names["api"],
                *common,
                *env,
                *mounts(phase),
                images[version + "api"][0],
            )
            created.append(names["api"])
            endpoint = "ready" if not version else "detailed"
            wait(
                names["api"],
                "python",
                "-c",
                f"import json,urllib.request; r=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/{endpoint}',timeout=5)); assert r['status']=='healthy'",
            )
            docker(
                "run",
                "-d",
                "--name",
                names["worker"],
                *common,
                *env,
                *mounts(phase),
                images[version + "api"][0],
                "celery",
                "-A",
                "app.worker",
                "worker",
                "--loglevel=warning",
                "--concurrency=1",
                "--queues=hermes.rehearsal.only",
            )
            created.append(names["worker"])
            wait(
                names["worker"],
                "celery",
                "-A",
                "app.worker",
                "inspect",
                "ping",
                "--timeout=2",
            )
            docker(
                "run",
                "-d",
                "--name",
                names["app"],
                *common,
                "-e",
                "VITE_API_BASE_URL=http://" + names["api"] + ":8000/api/v1",
                images[version + "app"][0],
            )
            created.append(names["app"])
            wait(names["app"], "wget", "-qO-", "http://127.0.0.1/")
            check("verify", phase)
            if phase == "upgrade":
                # Separate Linux processes share the same live WAL and SHM files.
                auth = subprocess.Popen(
                    [
                        "docker",
                        "exec",
                        names["api"],
                        "python",
                        "/rehearsal/probe.py",
                        "--probe",
                        "auth",
                        phase,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                try:
                    check("transactions", phase, names["worker"])
                    output, error = auth.communicate(timeout=180)
                    assert auth.returncode == 0, (output + error).decode()
                finally:
                    if auth.poll() is None:
                        auth.kill()
                        auth.communicate()
                check("verify", phase)
                check("upgraded-baseline", phase)
                docker(
                    "exec",
                    names["api"],
                    "python",
                    "-m",
                    "app.manage",
                    "backup",
                    "/app/data/backups/rehearsal",
                )
            elif phase == "restored-new":
                check("verify-restored", phase)
            for name in names.values():
                state = json.loads(docker("inspect", name))[0]
                assert (
                    state["RestartCount"] == 0
                    and not state["HostConfig"]["PortBindings"]
                )
            docker("stop", "--time", "30", *names.values())
            check("verify", phase)
            phases.append(phase)
            print(
                f"{phase}: integrity, original rows and file checksums passed",
                flush=True,
            )
        result = {
            "status": "passed",
            "runtime": runtime,
            "platform": args.platform,
            "images": images,
            "phases": phases,
            "auth_requests": 64,
            "transaction_outcomes": 60,
            "storage": "Linux Docker volume",
            "checkpoint_sha256": checkpoint_hash,
            "checkpoint_kind": (
                "retrieved archive" if args.checkpoint else "synthetic fixture"
            ),
        }
        (evidence / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        passed = True
    finally:
        for container in created:
            if not passed:
                log = evidence / (container + ".private.log")
                log.write_text(docker("logs", container, include_stderr=True))
                log.chmod(0o600)
        if created:
            docker("stop", "--time", "30", *created)
        if passed:
            docker("rm", *created)
            docker("network", "rm", identity)
            docker("volume", "rm", identity)
        else:
            (evidence / "retained-volume.txt").write_text(identity + "\n")


def main() -> None:
    if len(sys.argv) == 4 and sys.argv[1] == "--probe":
        sys.path.insert(0, "/app")
        probe(sys.argv[2], sys.argv[3])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "api-image",
        "app-image",
        "old-api-image",
        "old-app-image",
        "redis-image",
        "evidence",
    ):
        parser.add_argument("--" + name, required=True)
    parser.add_argument(
        "--checkpoint",
        help="Private tar archive with hermes/{config,downloads,temp,redis}; defaults to the synthetic 0.6.0 fixture",
    )
    parser.add_argument(
        "--platform", default="linux/amd64", choices=("linux/amd64", "linux/arm64")
    )
    rehearse(parser.parse_args())


if __name__ == "__main__":
    main()
