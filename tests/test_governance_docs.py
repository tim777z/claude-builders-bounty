"""Static regression tests for governance and contributor docs.

These checks keep trust signals discoverable and aligned with enforced gates.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


class GovernanceDocTests(unittest.TestCase):
    def test_contributing_guide_exists_and_states_quality_gates(self) -> None:
        guide = _read("CONTRIBUTING.md")
        for token in (
            "python -m ruff check .",
            "python -m ruff format --check .",
            "python -m mypy",
            "python -m coverage report --fail-under=90",
            "python -m pip_audit -r requirements-dev.lock",
            "Conventional Commits",
            "Tests in the same change",
            "No secrets",
            "SECURITY.md",
        ):
            with self.subTest(token=token):
                self.assertIn(token, guide)

    def test_readme_links_governance_docs(self) -> None:
        readme = _read("README.md")
        self.assertIn("[CONTRIBUTING.md](CONTRIBUTING.md)", readme)
        self.assertIn("[SECURITY.md](SECURITY.md)", readme)
        self.assertIn("`CONTRIBUTING.md` | Contributor workflow and quality gates |", readme)

    def test_security_policy_remains_private_reporting_path(self) -> None:
        policy = _read("SECURITY.md")
        self.assertIn("Do not open a public issue", policy)
        self.assertIn("Reporting a vulnerability", policy)


if __name__ == "__main__":
    unittest.main()
