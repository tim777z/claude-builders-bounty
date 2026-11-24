"""Static checks for security/governance artifacts.

These tests verify that trust signals and packaging hygiene files exist and
contain the expected controls. They are static to keep the suite fast and
network-free.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


class SecurityHygieneTests(unittest.TestCase):
    def test_security_policy_exists_with_reporting_guidance(self) -> None:
        policy = _read("SECURITY.md")
        for token in (
            "Reporting a vulnerability",
            "Do not open a public issue",
            "shell=False",
            "1 MiB",
            "dependency auditing",
        ):
            with self.subTest(token=token):
                self.assertIn(token, policy)

    def test_gitattributes_normalizes_text_files(self) -> None:
        attrs = _read(".gitattributes")
        for token in ("* text=auto eol=lf", "*.py text diff=python", "*.lock text"):
            with self.subTest(token=token):
                self.assertIn(token, attrs)

    def test_py_typed_marker_is_packaged(self) -> None:
        self.assertTrue((REPO_ROOT / "changelog_skill" / "py.typed").exists())
        config = _read("pyproject.toml")
        self.assertIn("[tool.setuptools.package-data]", config)
        self.assertIn('changelog_skill = ["py.typed"]', config)


if __name__ == "__main__":
    unittest.main()
