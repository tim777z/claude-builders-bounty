"""Regression tests for repository hygiene controls.

A stray runtime log was previously committed three times. These tests keep the
ignore rules honest so diagnostics and local secrets cannot silently re-enter
version control.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class RepositoryHygieneTests(unittest.TestCase):
    def test_no_runtime_logs_are_present(self) -> None:
        logs = sorted(REPO_ROOT.rglob("*.log"))
        self.assertEqual(logs, [], f"runtime logs must not be committed: {logs}")

    def test_no_local_env_files_are_present(self) -> None:
        env_files = [path for path in REPO_ROOT.rglob(".env*") if path.name != ".env.example"]
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
