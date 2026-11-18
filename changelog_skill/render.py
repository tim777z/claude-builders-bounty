"""Deterministic Markdown rendering for validated commits."""

from __future__ import annotations

import re
from datetime import date as date_type

from .model import COMMIT_TYPES, SECTION_TITLES, Commit, InputError

_VERSION_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+-]{0,63}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MARKDOWN_SPECIAL_RE = re.compile(r"([\\`*_\[\]<>|!])")


def escape_markdown(text: str) -> str:
    """Neutralise Markdown/HTML syntax supplied by untrusted commit messages.

    Without this, a commit subject such as ``fix: [click](javascript:...)``
    would become an active link when the generated CHANGELOG is rendered on a
    hosting platform - a low-effort content-injection vector.
    """
    return _MARKDOWN_SPECIAL_RE.sub(r"\\\1", text)


def _validate_version(version: str) -> None:
    if not isinstance(version, str) or not _VERSION_RE.fullmatch(version):
        raise InputError("version must be 1-64 characters of letters, digits, '.', '+' or '-'")


def _validate_date(release_date: str) -> None:
    if not isinstance(release_date, str) or not _DATE_RE.fullmatch(release_date):
        raise InputError("date must be an ISO date in YYYY-MM-DD format")
    try:
        date_type.fromisoformat(release_date)
    except ValueError as exc:
        raise InputError(f"date is not a real calendar date: {release_date}") from exc


def render_changelog(
    commits: tuple[Commit, ...],
    *,
    version: str,
    release_date: str,
) -> str:
    """Render commits into a release section of a Markdown CHANGELOG.

    Input order is preserved because ``git log`` is already reverse
    chronological. Grouping is stable and sections follow :data:`COMMIT_TYPES`.
    """
    _validate_version(version)
    _validate_date(release_date)

    lines = [
        "# Changelog",
        "",
        "All notable changes to this project are documented in this file.",
        "This release section is generated from Conventional Commits; do not edit by hand.",
        "",
        f"## [{version}] - {release_date}",
        "",
    ]

    if not commits:
        lines.extend(["_No Conventional Commits were found in the selected range._", ""])
        return "\n".join(lines)

    for commit in commits:
        if not isinstance(commit, Commit):
            raise InputError("commits must contain only Commit instances")

    breaking = [commit for commit in commits if commit.breaking]
    if breaking:
        lines.append("### BREAKING CHANGES")
        lines.append("")
        for commit in breaking:
            label = f"**{commit.kind}**"
            if commit.scope:
                label += f" **({escape_markdown(commit.scope)})**"
            lines.append(f"- {label}: {escape_markdown(commit.subject)} ({commit.sha[:7]})")
        lines.append("")

    for kind in COMMIT_TYPES:
        group = [commit for commit in commits if commit.kind == kind and not commit.breaking]
        if not group:
            continue
        lines.append(f"### {SECTION_TITLES[kind]}")
        lines.append("")
        for commit in group:
            scope = f" **{escape_markdown(commit.scope)}**" if commit.scope else ""
            lines.append(
                f"- **{kind}**{scope}: {escape_markdown(commit.subject)} " f"({commit.sha[:7]})"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
