"""Keep recovery of old releases from moving image aliases backwards."""

import runpy
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import cast

POLICY = cast(
    Callable[[str, list[str]], dict[str, bool]],
    runpy.run_path(
        str(Path(__file__).resolve().parents[2] / ".github/scripts/release_aliases.py")
    )["alias_policy"],
)


class ReleaseAliasTests(unittest.TestCase):
    def test_workflows_do_not_bypass_alias_policy_with_automatic_latest(self) -> None:
        workflows = Path(__file__).resolve().parents[2] / ".github/workflows"
        for name in ("release.yml", "publish-release-images.yml"):
            metadata_steps = (
                (workflows / name)
                .read_text()
                .split("uses: docker/metadata-action@")[1:]
            )
            self.assertEqual(len(metadata_steps), 2)
            for step in metadata_steps:
                with self.subTest(workflow=name):
                    config = step.split("\n      - name:", 1)[0]
                    self.assertIn("flavor: latest=false", config)
                    for alias in ("latest", "major", "minor"):
                        self.assertIn(
                            "enable=${{ steps.aliases.outputs."
                            + alias
                            + " == 'true' }}",
                            config,
                        )

    def test_old_patch_is_exact_only(self) -> None:
        self.assertEqual(
            POLICY("1.2.1", ["v1.2.1", "v1.2.2", "v2.0.0"]),
            {"latest": False, "major": False, "minor": False},
        )

    def test_latest_patch_of_old_major_can_refresh_its_series(self) -> None:
        self.assertEqual(
            POLICY("1.2.2", ["v1.2.1", "v1.2.2", "v2.0.0"]),
            {"latest": False, "major": True, "minor": True},
        )

    def test_numeric_order_and_prereleases(self) -> None:
        self.assertEqual(
            POLICY("1.10.0", ["v1.9.9", "v1.10.0", "v2.0.0-rc.1"]),
            {"latest": True, "major": True, "minor": True},
        )

    def test_old_minor_cannot_change_major(self) -> None:
        self.assertEqual(
            POLICY("1.2.2", ["v1.2.2", "v1.3.0"]),
            {"latest": False, "major": False, "minor": True},
        )

    def test_missing_or_invalid_release_fails_closed(self) -> None:
        for version in ("1.0.0", "1.0.0-rc.1", "v1.0.0"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                POLICY(version, ["v0.9.0"])
