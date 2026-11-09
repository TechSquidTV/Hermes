"""The rehearsal must reject data loss and incomplete restoration evidence."""

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from sqlite_release import probe, snapshot, verify


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
        self.baseline.write_text(json.dumps(snapshot(self.root)))

    def test_changed_original_credentials_are_rejected(self) -> None:
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute("UPDATE users SET password_hash=X'334455'")
            connection.commit()
        with self.assertRaisesRegex(AssertionError, "Original rows changed"):
            verify(self.root, self.baseline, exact=False)

    def test_synthetic_checkpoint_can_seed_and_complete_its_baseline(self) -> None:
        fixture = (
            Path(__file__).resolve().parents[2]
            / "packages/hermes-api/tests/fixtures/v0.6.0.sqlite.sql"
        )
        (self.root / "seed.sql").write_text(fixture.read_text())
        with patch("sqlite_release.ROOT", self.root):
            probe("seed", "original")
            probe("baseline", "original")
            probe("verify", "original")
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
            snapshot(self.root)

    def test_restoration_requires_the_complete_upgraded_state(self) -> None:
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute("INSERT INTO users VALUES ('synthetic', X'223344')")
            connection.commit()
        verify(self.root, self.baseline, exact=False)
        with self.assertRaisesRegex(AssertionError, "Unexpected writes"):
            verify(self.root, self.baseline, exact=True)
        upgraded = self.root / "upgraded.json"
        upgraded.write_text(json.dumps(snapshot(self.root)))
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute("DELETE FROM users WHERE id='synthetic'")
            connection.commit()
        with self.assertRaisesRegex(AssertionError, "Original rows changed"):
            verify(self.root, upgraded, exact=True)

    def test_changed_media_and_symlinks_are_rejected(self) -> None:
        self.media.write_bytes(b"changed")
        with self.assertRaisesRegex(AssertionError, "file checksums changed"):
            verify(self.root, self.baseline, exact=True)
        self.media.unlink()
        self.media.symlink_to(self.database)
        with self.assertRaisesRegex(AssertionError, "symlinks"):
            snapshot(self.root)
