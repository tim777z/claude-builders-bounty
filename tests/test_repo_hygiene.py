"""Regression tests for repository hygiene controls.

A stray runtime log was previously committed three times. These tests keep the
ignore rules honest so diagnostics and local secrets cannot silently re-enter
version control.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _tracked_paths(pattern: str) -> list[str]:
    """List paths git would commit, ignoring local (possibly locked) artefacts.

    The control is the commit boundary: a developer may legitimately have an
    ignored runtime log open in another process, but no diagnostic output or
    local secret may ever be tracked. Checking the whole working tree here
    produced false failures for ignored files that cannot be deleted while a
    tool holds them open.
    """
    result = subprocess.run(  # noqa: S603 - fixed argv, read-only git query
        ["git", "ls-files", "--", pattern],  # noqa: S607 - git is resolved from PATH
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"could not query tracked files: {result.stderr.strip()}")
    return [line for line in result.stdout.splitlines() if line]


class RepositoryHygieneTests(unittest.TestCase):
    def test_no_runtime_logs_are_tracked(self) -> None:
        self.assertEqual(_tracked_paths("*.log"), [], "runtime logs must not be committed")

    def test_no_local_env_files_are_tracked(self) -> None:
        env_files = [
            path for path in _tracked_paths(".env*") if path.rsplit("/", 1)[-1] != ".env.example"
        ]
        self.assertEqual(env_files, [], f"local env files must not be committed: {env_files}")

    def test_gitignore_covers_logs_and_secrets(self) -> None:
        ignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in (
            "*.log",
            ".env",
            ".env.*",
            "!.env.example",
            "__pycache__/",
            ".pytest_cache/",
            ".ruff_cache/",
            ".mypy_cache/",
            ".coverage",
        ):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, ignore)


if __name__ == "__main__":
    unittest.main()
