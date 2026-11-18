"""Parsing of raw ``git log`` output into validated :class:`Commit` objects.

All functions here are pure: no subprocesses, no filesystem access, no global
state. That keeps the security-sensitive validation easy to test in isolation.
"""

from __future__ import annotations

import re

from .model import COMMIT_TYPES, Commit, InputError

# Format produced by: git log --pretty=format:%H%x09%s
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
_CONVENTIONAL_RE = re.compile(
    r"^(?P<kind>[a-z]+)"
    r"(?:\((?P<scope>[^()\r\n]{1,64})\))?"
    r"(?P<breaking>!)?: (?P<subject>.+)$"
)

MAX_SUBJECT_LENGTH = 200
MAX_LINES = 5_000
MAX_RAW_LINE_LENGTH = 512


def _reject_control_characters(
    value: str, *, field: str, line_number: int, allow_tab: bool = False
) -> None:
    for char in value:
        code = ord(char)
        if allow_tab and char == "\t":
            continue
        if code < 32 or code == 127:
            raise InputError(
                f"line {line_number}: {field} contains a control character (U+{code:04X})"
            )


def parse_commit_line(raw: str, *, line_number: int = 1) -> Commit:
    """Parse one ``<sha>\\t<message>`` line.

    Malformed input raises :class:`InputError` with the offending line number
    instead of being silently skipped, so a broken git history is never
    rendered into a misleading CHANGELOG.
    """
    if not isinstance(raw, str):
        raise InputError(f"line {line_number}: expected text, got {type(raw).__name__}")

    line = raw.rstrip("\r\n")
    if not line.strip():
        raise InputError(f"line {line_number}: empty commit line")
    if len(line) > MAX_RAW_LINE_LENGTH:
        raise InputError(
            f"line {line_number}: commit line exceeds {MAX_RAW_LINE_LENGTH} characters"
        )
    # The TAB is the required field separator; every other control character
    # (including NUL and escape sequences) is rejected.
    _reject_control_characters(line, field="commit line", line_number=line_number, allow_tab=True)

    parts = line.split("\t", 1)
    if len(parts) != 2:
        raise InputError(f"line {line_number}: expected '<sha><TAB><message>' format")

    # Strip spaces only: stripping all whitespace would silently swallow a
    # tab/newline that the control-character validation must reject.
    sha, message = (part.strip(" ") for part in parts)
    _reject_control_characters(sha, field="sha", line_number=line_number)
    _reject_control_characters(message, field="message", line_number=line_number)
    if not _SHA_RE.fullmatch(sha):
        raise InputError(f"line {line_number}: sha must be 7-64 hexadecimal characters")

    match = _CONVENTIONAL_RE.fullmatch(message)
    if match is None:
        raise InputError(
            f"line {line_number}: message is not a Conventional Commit "
            "(expected 'type(scope): subject')"
        )

    kind = match.group("kind")
    if kind not in COMMIT_TYPES:
        allowed = ", ".join(COMMIT_TYPES)
        raise InputError(f"line {line_number}: unknown commit type '{kind}' (allowed: {allowed})")

    subject = match.group("subject").strip()
    if not subject:
        raise InputError(f"line {line_number}: commit subject is empty")
    if len(subject) > MAX_SUBJECT_LENGTH:
        raise InputError(f"line {line_number}: subject exceeds {MAX_SUBJECT_LENGTH} characters")

    return Commit(
        sha=sha,
        kind=kind,
        scope=match.group("scope"),
        subject=subject,
        breaking=match.group("breaking") == "!",
    )


def parse_git_log(text: str, *, max_lines: int = MAX_LINES) -> tuple[Commit, ...]:
    """Parse a whole ``git log`` payload, skipping only blank separator lines."""
    if not isinstance(max_lines, int) or not 1 <= max_lines <= MAX_LINES:
        raise InputError(f"max_lines must be an integer between 1 and {MAX_LINES}")

    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) > max_lines:
        raise InputError(f"commit history exceeds the {max_lines} line safety limit")

    return tuple(
        parse_commit_line(line, line_number=index) for index, line in enumerate(lines, start=1)
    )


def parse_git_log_lenient(
    text: str, *, max_lines: int = MAX_LINES
) -> tuple[tuple[Commit, ...], int]:
    """Parse a history that also contains non-Conventional commits.

    Unparseable lines are skipped and counted rather than silently discarded;
    callers must surface the count so a degraded CHANGELOG is never mistaken
    for a complete one. Strict mode remains the default everywhere else.
    """
    if not isinstance(max_lines, int) or not 1 <= max_lines <= MAX_LINES:
        raise InputError(f"max_lines must be an integer between 1 and {MAX_LINES}")

    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) > max_lines:
        raise InputError(f"commit history exceeds the {max_lines} line safety limit")

    commits: list[Commit] = []
    skipped = 0
    for index, line in enumerate(lines, start=1):
        try:
            commits.append(parse_commit_line(line, line_number=index))
        except InputError:
            skipped += 1
    return tuple(commits), skipped
