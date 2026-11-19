"""Filesystem and git adapters. All external input is validated and bounded."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TextIO

from .model import SourceError

MAX_INPUT_BYTES = 1024 * 1024
MAX_COUNT = 5_000
GIT_TIMEOUT_SECONDS = 30

# tformat emits a trailing newline after every record so each commit is one line.
_LOG_FORMAT = "tformat:%H%x09%s"


def read_commits_from_repo(repo: Path, *, max_count: int = 500) -> str:
    """Read ``<sha>\\t<subject>`` lines from a local git repository.

    The git command is built as an argument vector with ``shell=False``: a
    repository path containing shell metacharacters is passed as one literal
    argument and can never become a second command.
    """
    if (
        not isinstance(max_count, int)
        or isinstance(max_count, bool)
        or not 1 <= max_count <= MAX_COUNT
    ):
        raise SourceError(f"max_count must be an integer between 1 and {MAX_COUNT}")

    path = Path(repo).expanduser().resolve()
    if not path.is_dir():
        raise SourceError(f"repository path does not exist or is not a directory: {path}")
    if not (path / ".git").exists():
        raise SourceError(f"not a git repository: {path}")

    command = [
        "git",
        "-C",
        str(path),
        "log",
        "--no-merges",
        f"--max-count={max_count}",
        f"--pretty={_LOG_FORMAT}",
    ]
    try:
        result = subprocess.run(  # noqa: S603 - fixed argv, shell=False by design
            command,
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        raise SourceError(f"could not read git history: {exc}") from exc

    if result.returncode != 0:
        detail = (result.stderr or "").strip()[:500]
        raise SourceError(f"git log failed (exit {result.returncode}): {detail}")

    output = result.stdout
    if len(output.encode("utf-8")) > MAX_INPUT_BYTES:
        raise SourceError("git history exceeds the 1 MiB safety limit")
    return output


def read_commits_from_stdin(stream: TextIO | None = None) -> str:
    """Read raw commit lines from stdin with the same 1 MiB cap as files.

    Reading an unbounded stream into memory would let a hostile pipeline exhaust
    the process. Reading at most one byte/character beyond the cap and checking
    the UTF-8 byte length keeps the parser's safety limits consistent across
    every input source. ``stream`` is injectable so the behaviour is testable
    without replacing the real process stdin.
    """
    source = sys.stdin if stream is None else stream
    try:
        text = source.read(MAX_INPUT_BYTES + 1)
    except (OSError, UnicodeError) as exc:
        raise SourceError(f"could not read stdin: {exc}") from exc
    if not isinstance(text, str):
        raise SourceError("stdin did not return text")
    if len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise SourceError("stdin history exceeds the 1 MiB safety limit")
    return text


def read_commits_from_file(source: Path) -> str:
    """Read raw commit lines from a local file with a strict size cap."""
    path = Path(source).expanduser().resolve()
    if not path.is_file():
        raise SourceError(f"input file does not exist: {path}")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise SourceError("input file exceeds the 1 MiB safety limit")
    try:
        return path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        raise SourceError(f"could not read input file: {exc}") from exc
