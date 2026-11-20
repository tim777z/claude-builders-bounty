"""Static regression tests for the reproducible developer/CI toolchain.

These checks need no network and no install, so a fresh clone can verify its
own toolchain contract immediately. They pin the intent behind the Makefile,
lockfile and CI workflow: one canonical, reproducible path from clone to tests.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


class ReproducibleToolchainTests(unittest.TestCase):
    def test_dev_requirements_use_exact_pins(self) -> None:
        pins = [
            line.strip()
            for line in _read("requirements-dev.txt").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(pins, ["coverage==7.16.1", "pip-audit==2.7.3", "ruff==0.7.4"])

    def test_lockfile_is_present_hashed_and_complete(self) -> None:
        locked = [line.split("==")[0] for line in _read("requirements-dev.lock").splitlines()]
        for tool in ("coverage", "pip-audit", "ruff"):
            with self.subTest(tool=tool):
                self.assertIn(tool, locked)
        self.assertIn("--hash=sha256:", _read("requirements-dev.lock"))

    def test_makefile_exposes_canonical_targets(self) -> None:
        targets = [line.split(":", 1)[0] for line in _read("Makefile").splitlines()]
        for target in ("install-dev", "lint", "format-check", "test", "coverage", "audit"):
            with self.subTest(target=target):
                self.assertIn(target, targets)

    def test_pytest_discovery_is_configured(self) -> None:
        config = _read("pyproject.toml")
        self.assertIn("[tool.pytest.ini_options]", config)
        self.assertIn('testpaths = ["tests"]', config)

    def test_ci_installs_from_the_committed_lockfile(self) -> None:
        workflow = _read(".github/workflows/ci.yml")
        self.assertIn("requirements-dev.lock", workflow)

    def test_coverage_floor_is_configured_and_enforced(self) -> None:
        config = _read("pyproject.toml")
        workflow = _read(".github/workflows/ci.yml")
        self.assertIn("[tool.coverage.run]", config)
        self.assertIn('source = ["changelog_skill"]', config)
        self.assertIn("fail_under = 85", config)
        self.assertIn("coverage report --fail-under=85", workflow)

    def test_dependency_audit_runs_in_ci(self) -> None:
        workflow = _read(".github/workflows/ci.yml")
        self.assertIn("pip-audit", workflow)


class ContainerHardeningTests(unittest.TestCase):
    """Static checks: Docker is unavailable in the assessment sandbox, so the
    container's security posture is pinned without building or running it."""

    def test_dockerfile_drops_root_and_bytecode_writes(self) -> None:
        dockerfile = _read("Dockerfile")
        users = [line for line in dockerfile.splitlines() if line.startswith("USER ")]
        self.assertTrue(users, "Dockerfile must declare an explicit non-root USER")
        self.assertTrue(all(":" in line and "root" not in line for line in users))
        self.assertIn("PYTHONDONTWRITEBYTECODE=1", dockerfile)
        self.assertIn("ENTRYPOINT", dockerfile)

    def test_compose_applies_defense_in_depth(self) -> None:
        compose = _read("docker-compose.yml")
        for directive in (
            "network_mode: none",
            "read_only: true",
            '"no-new-privileges:true"',
            "cap_drop:",
            "ro",
        ):
            with self.subTest(directive=directive):
                self.assertIn(directive, compose)


if __name__ == "__main__":
    unittest.main()
