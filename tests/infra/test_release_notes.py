"""Published release guidance must describe the exact selected release."""

import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[2]
RENDER = cast(
    Callable[[str, Path], str],
    runpy.run_path(str(ROOT / ".github/scripts/release_notes.py"))["render_notes"],
)


class ReleaseNotesTests(unittest.TestCase):
    def test_both_publication_paths_pass_versioned_guidance_to_github(self) -> None:
        for workflow, step in (
            ("release.yml", "Create GitHub release"),
            (
                "publish-release-images.yml",
                "Create missing GitHub release after recovery",
            ),
        ):
            with self.subTest(workflow=workflow):
                self.run_publication(workflow, step, include_template=True)

    def test_old_release_recovery_does_not_attach_new_release_instructions(
        self,
    ) -> None:
        self.run_publication(
            "publish-release-images.yml",
            "Create missing GitHub release after recovery",
            include_template=False,
        )

    def run_publication(
        self, workflow: str, step: str, *, include_template: bool
    ) -> None:
        source = (ROOT / ".github/workflows" / workflow).read_text()
        block = source.split(f"      - name: {step}\n", 1)[1].split(
            "\n      - name:", 1
        )[0]
        script = textwrap.dedent(block.split("        run: |\n", 1)[1]).replace(
            "${{ steps.new_version.outputs.version }}", "1.2.3"
        )
        with tempfile.TemporaryDirectory(prefix="hermes-release-notes-") as directory:
            workspace = Path(directory)
            for relative in (
                ".github/scripts",
                ".release-policy/.github/scripts",
                "bin",
            ):
                (workspace / relative).mkdir(parents=True)
            for relative in (".github/scripts", ".release-policy/.github/scripts"):
                shutil.copyfile(
                    ROOT / ".github/scripts/release_notes.py",
                    workspace / relative / "release_notes.py",
                )
            if include_template:
                shutil.copyfile(
                    ROOT / ".github/release-notes.md",
                    workspace / ".github/release-notes.md",
                )
            github = workspace / "bin/gh"
            github.write_text(f"#!{sys.executable}\n" + textwrap.dedent("""\
                import os, sys
                from pathlib import Path
                if sys.argv[1:3] == ["release", "view"]:
                    sys.exit(1)
                assert sys.argv[1:4] == ["release", "create", "v1.2.3"], sys.argv
                assert "--generate-notes" in sys.argv and "--verify-tag" in sys.argv
                if os.environ["EXPECT_NOTES"] == "yes":
                    path = Path(sys.argv[sys.argv.index("--notes-file") + 1])
                    assert "python3 scripts/upgrade.py 1.2.3" in path.read_text()
                    assert "Sign in again after upgrading" in path.read_text()
                else:
                    assert "--notes-file" not in sys.argv
                Path("publication-verified").touch()
            """))
            github.chmod(0o700)
            result = subprocess.run(
                ["bash", "-euc", script],
                cwd=workspace,
                env={
                    **os.environ,
                    "PATH": str(workspace / "bin") + os.pathsep + os.environ["PATH"],
                    "RUNNER_TEMP": directory,
                    "RELEASE_TAG": "v1.2.3",
                    "EXPECT_NOTES": "yes" if include_template else "no",
                },
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((workspace / "publication-verified").exists())

    def test_rendered_guidance_includes_version_and_breaking_upgrade_steps(
        self,
    ) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / ".github/scripts/release_notes.py"),
                "1.2.3",
                str(ROOT / ".github/release-notes.md"),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("python3 scripts/upgrade.py 1.2.3", result.stdout)
        self.assertIn("/blob/v1.2.3/docs/UPGRADING.md", result.stdout)
        self.assertIn(
            "Database migration and coordinated service upgrade required", result.stdout
        )
        self.assertIn("Sign in again after upgrading", result.stdout)
        self.assertNotIn("{{VERSION}}", result.stdout)

    def test_invalid_version_is_rejected(self) -> None:
        for version in ("v1.2.3", "1.2.3-rc.1", "1.2.3\nextra"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                RENDER(version, ROOT / ".github/release-notes.md")
