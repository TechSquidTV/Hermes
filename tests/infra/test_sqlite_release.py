"""The rehearsal must reject data loss and incomplete restoration evidence."""

import argparse
import io
import json
import os
import sqlite3
import sys
import tarfile
import tempfile
import textwrap
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import sqlite_release as release


class SQLiteReleaseEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="sqlite-evidence-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in ("config", "downloads", "temp"):
            (self.root / name).mkdir()
        self.database = self.root / "config/hermes.db"
        with closing(sqlite3.connect(self.database)) as connection:
            connection.executescript(
                "CREATE TABLE users (id TEXT PRIMARY KEY, password_hash BLOB);"
                "INSERT INTO users VALUES ('original', X'001122');"
            )
        self.media = self.root / "downloads/original.mp4"
        self.media.write_bytes(b"original media")
        self.baseline = self.root / "baseline.json"
        self.baseline.write_text(json.dumps(release.snapshot(self.root)))

    def failed_rehearsal(
        self, *, log_exit: int = 0, stop_exit: int = 0, setup_exit: int = 0
    ) -> Path:
        binary = self.root / "bin"
        binary.mkdir()
        docker = binary / "docker"
        docker.write_text(
            f"#!{sys.executable}\n"
            + textwrap.dedent("""\
            import sys
            from pathlib import Path
            arguments = sys.argv[1:]
            if arguments[:2] == ["image", "inspect"]:
                print("sha256:" + "a" * 64 + " linux/amd64")
            elif arguments[0] == "logs":
                print("container standard output")
                print("container error diagnostics", file=sys.stderr)
                sys.exit(__LOG_EXIT__)
            elif arguments[0] == "stop":
                (Path(sys.argv[0]).parent.parent / "stop-attempted").touch()
                sys.exit(__STOP_EXIT__)
            elif arguments[:2] == ["network", "create"]:
                sys.exit(__SETUP_EXIT__)
            elif arguments[0] == "exec":
                print("synthetic runtime check failure", file=sys.stderr)
                sys.exit(1)
        """)
            .replace("__LOG_EXIT__", str(log_exit))
            .replace("__STOP_EXIT__", str(stop_exit))
            .replace("__SETUP_EXIT__", str(setup_exit))
        )
        docker.chmod(0o700)
        evidence = self.root / "evidence"
        arguments = argparse.Namespace(
            evidence=str(evidence),
            api_image="api",
            app_image="app",
            old_api_image="old-api",
            old_app_image="old-app",
            redis_image="redis",
            checkpoint=None,
            platform="linux/amd64",
        )
        with patch.dict(
            os.environ, {"PATH": str(binary) + os.pathsep + os.environ.get("PATH", "")}
        ):
            with self.assertRaisesRegex(RuntimeError, "Rehearsal failed"):
                release.rehearse(arguments)
        return evidence

    def test_failed_rehearsal_retains_container_stdout_and_stderr(self) -> None:
        evidence = self.failed_rehearsal()
        logs = list(evidence.glob("*-helper.private.log"))
        self.assertEqual(len(logs), 1)
        self.assertIn("container standard output", logs[0].read_text())
        self.assertIn("container error diagnostics", logs[0].read_text())

    def test_failed_log_collection_still_stops_and_records_the_volume(self) -> None:
        evidence = self.failed_rehearsal(log_exit=1)
        self.assertTrue((self.root / "stop-attempted").exists())
        self.assertTrue((evidence / "retained-volume.txt").exists())
        self.assertIn(
            "collecting logs", (evidence / "cleanup-errors.private.log").read_text()
        )
        self.assertIn(
            "synthetic runtime check failure",
            (evidence / "failure-command.private.log").read_text(),
        )

    def test_failed_stop_preserves_the_primary_error_and_recovery_identity(
        self,
    ) -> None:
        evidence = self.failed_rehearsal(stop_exit=1)
        self.assertTrue((evidence / "retained-volume.txt").exists())
        self.assertIn(
            "stopping containers", (evidence / "cleanup-errors.private.log").read_text()
        )
        self.assertIn(
            "synthetic runtime check failure",
            (evidence / "failure-command.private.log").read_text(),
        )
        self.assertFalse((evidence / "result.json").exists())

    def test_setup_failure_records_a_volume_created_before_the_helper(self) -> None:
        evidence = self.failed_rehearsal(setup_exit=1)
        self.assertTrue((evidence / "retained-volume.txt").exists())
        self.assertFalse((evidence / "result.json").exists())

    def sparse_archive(self, canonical: str) -> Path:
        archive_path = self.root / "checkpoint.tar"
        content = b"original sparse media"
        sparse_map = f"1\n0\n{len(content)}\n".encode().ljust(512, b"\0")
        member = tarfile.TarInfo("hermes/downloads/GNUSparseFile.1/temporary.mp4")
        member.pax_headers = {
            "GNU.sparse.major": "1",
            "GNU.sparse.minor": "0",
            "GNU.sparse.name": canonical,
            "GNU.sparse.realsize": str(len(content)),
            "path": member.name,
        }
        member.size = len(sparse_map) + len(content)
        with tarfile.open(archive_path, "w", format=tarfile.PAX_FORMAT) as archive:
            archive.addfile(member, io.BytesIO(sparse_map + content))
        return archive_path

    def test_sparse_archive_restores_canonical_path_and_bytes(self) -> None:
        canonical = "hermes/downloads/" + "long unicode title \u2019" * 8 + ".mp4"
        destination = self.root / "restored"
        release.extract_checkpoint(self.sparse_archive(canonical), destination)
        self.assertEqual(
            (destination / canonical).read_bytes(), b"original sparse media"
        )
        self.assertFalse(list(destination.rglob("GNUSparseFile*")))

    def test_sparse_canonical_path_cannot_escape_the_destination(self) -> None:
        with self.assertRaises(tarfile.FilterError):
            release.extract_checkpoint(
                self.sparse_archive("../escape.mp4"), self.root / "restored"
            )
        self.assertFalse((self.root / "escape.mp4").exists())

    def test_changed_original_credentials_are_rejected(self) -> None:
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute("UPDATE users SET password_hash=X'334455'")
            connection.commit()
        with self.assertRaisesRegex(AssertionError, "Original rows changed"):
            release.verify(self.root, self.baseline, exact=False)

    def test_synthetic_checkpoint_can_seed_and_complete_its_baseline(self) -> None:
        fixture = (
            Path(__file__).resolve().parents[2]
            / "packages/hermes-api/tests/fixtures/v0.6.0.sqlite.sql"
        )
        (self.root / "seed.sql").write_text(fixture.read_text())
        with patch("sqlite_release.ROOT", self.root):
            release.probe("seed", "original")
            release.probe("baseline", "original")
            release.probe("verify", "original")
        directory = self.root / "original/hermes"
        self.assertEqual(
            (directory / "downloads/legacy.mp4").read_bytes(), b"legacy-media"
        )
        with closing(sqlite3.connect(directory / "config/hermes.db")) as connection:
            self.assertEqual(
                connection.execute("SELECT filepath FROM download_files").fetchone(),
                ("/app/downloads/legacy.mp4",),
            )

    def test_corruption_is_not_accepted_as_an_empty_database(self) -> None:
        self.database.write_bytes(b"broken database")
        with self.assertRaises(sqlite3.DatabaseError):
            release.snapshot(self.root)

    def test_restoration_requires_the_complete_upgraded_state(self) -> None:
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute("INSERT INTO users VALUES ('synthetic', X'223344')")
            connection.commit()
        release.verify(self.root, self.baseline, exact=False)
        with self.assertRaisesRegex(AssertionError, "Unexpected writes"):
            release.verify(self.root, self.baseline, exact=True)
        upgraded = self.root / "upgraded.json"
        upgraded.write_text(json.dumps(release.snapshot(self.root)))
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute("DELETE FROM users WHERE id='synthetic'")
            connection.commit()
        with self.assertRaisesRegex(AssertionError, "Original rows changed"):
            release.verify(self.root, upgraded, exact=True)

    def test_changed_media_and_symlinks_are_rejected(self) -> None:
        self.media.write_bytes(b"changed")
        with self.assertRaisesRegex(AssertionError, "file checksums changed"):
            release.verify(self.root, self.baseline, exact=True)
        self.media.unlink()
        self.media.symlink_to(self.database)
        with self.assertRaisesRegex(AssertionError, "symlinks"):
            release.snapshot(self.root)
