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

    def test_python_floor_matches_locked_toolchain(self) -> None:
        # The hash-locked toolchain pins the advisory-free filelock 4.2.12,
        # which declares Requires-Python >=3.11. Advertising 3.10 in the CI
        # matrix made the install step fail with "requires a different Python";
        # downgrading to vulnerable 3.x would instead fail `pip-audit`. Keep
        # the declared floor, the linter target and the tested matrix aligned.
        config = _read("pyproject.toml")
        workflow = _read(".github/workflows/ci.yml")
        self.assertIn('requires-python = ">=3.11"', config)
        self.assertNotIn('requires-python = ">=3.10"', config)
        self.assertIn('target-version = "py311"', config)
        self.assertIn('python-version: ["3.11", "3.12"]', workflow)
        self.assertNotIn('"3.10"', workflow)
        self.assertIn("filelock==4.2.12", _read("requirements-dev.lock"))

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

    def test_audit_invocation_uses_importable_module(self) -> None:
        # The distribution is named `pip-audit` but its importable module is
        # `pip_audit`. A hyphenated `-m` target is not a valid Python module and
        # fails with "No module named pip-audit", which broke every CI matrix job.
        for name in ("Makefile", "README.md", ".github/workflows/ci.yml"):
            with self.subTest(file=name):
                content = _read(name)
                self.assertNotIn("-m pip-audit", content)
                self.assertIn("-m pip_audit", content)

    def test_ci_actions_target_node24(self) -> None:
        # Node 20 action runtimes are deprecated and emit a failing warning
        # annotation on current runners. Pin the immutable Node 24 releases:
        # actions/checkout v5 and actions/setup-python v6.
        workflow = _read(".github/workflows/ci.yml")
        self.assertIn("actions/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8 # v5", workflow)
        self.assertIn(
            "actions/setup-python@e797f83bcb11b83ae66e0230d6156d7c80228e7c # v6", workflow
        )
        self.assertNotIn("actions/checkout@11d5960a326750d5838078e36cf38b85af677262", workflow)
        self.assertNotIn("actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", workflow)


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
