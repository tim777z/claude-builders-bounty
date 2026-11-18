"""Domain types and structured errors shared by the CHANGELOG generator."""

from __future__ import annotations

from dataclasses import dataclass


class ChangelogError(Exception):
    """Base class for every expected failure in this package."""


class InputError(ChangelogError):
    """Raised when commit text or CLI metadata is malformed or unsafe."""


class SourceError(ChangelogError):
    """Raised when commit history cannot be read from disk or git."""


class OutputError(ChangelogError):
    """Raised when the rendered CHANGELOG cannot be written."""


# Order in which sections are rendered. Anything unrecognised is rejected at
# parse time, so this list is also the allow-list of valid commit types.
COMMIT_TYPES: tuple[str, ...] = (
    "feat",
    "fix",
    "perf",
    "refactor",
    "docs",
    "test",
    "build",
    "ci",
    "chore",
    "style",
    "revert",
)

SECTION_TITLES: dict[str, str] = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "perf": "Performance Improvements",
    "refactor": "Code Refactoring",
    "docs": "Documentation",
    "test": "Tests",
    "build": "Build System",
    "ci": "Continuous Integration",
    "chore": "Maintenance",
    "style": "Styling",
    "revert": "Reverts",
}


@dataclass(frozen=True, slots=True)
class Commit:
    """A single validated Conventional Commit."""

    sha: str
    kind: str
    scope: str | None
    subject: str
    breaking: bool
