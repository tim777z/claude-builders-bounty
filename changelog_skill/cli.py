"""Command-line interface with predictable exit codes and atomic output."""

from __future__ import annotations

import argparse
import json
import logging
import os
import stat
import sys
import tempfile
from datetime import date as date_type
from pathlib import Path

from . import __version__
from .git import read_commits_from_file, read_commits_from_repo, read_commits_from_stdin
from .model import ChangelogError, InputError, OutputError, SourceError
from .parser import parse_git_log, parse_git_log_lenient
from .render import render_changelog

LOGGER = logging.getLogger("changelog_skill")


class _JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record for machine-readable diagnostics."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, str] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


EXIT_OK = 0
EXIT_INPUT = 3
EXIT_SOURCE = 4
EXIT_OUTPUT = 5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="changelog-skill",
        description="Generate a Markdown CHANGELOG from Conventional Commits.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--repo",
        type=Path,
        default=Path("."),
        help="local git repository to read (default: current directory)",
    )
    source.add_argument(
        "--input",
        type=Path,
        help="read raw 'git log' lines from this file instead of running git; '-' reads stdin",
    )

    parser.add_argument(
        "--release-version",
        required=True,
        help="release label for the generated section, e.g. 0.1.0",
    )
    parser.add_argument(
        "--release-date",
        default=date_type.today().isoformat(),
        help="release date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--max-count",
        type=int,
        default=500,
        help="maximum number of commits to read from git (default: 500)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="write the CHANGELOG to this file (default: stdout; '-' also means stdout)",
    )
    parser.add_argument(
        "--skip-invalid",
        action="store_true",
        help="skip non-Conventional commits (reported as a warning) instead of failing",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    parser.add_argument(
        "--log-format",
        choices=("text", "json"),
        default="text",
        help="diagnostic output format on stderr (default: text)",
    )
    return parser


def _write_output(text: str, destination: Path | None) -> None:
    if destination is None or str(destination) == "-":
        sys.stdout.write(text)
        return

    path = destination.expanduser().resolve()
    if not path.parent.is_dir():
        raise OutputError(f"output directory does not exist: {path.parent}")

    # NamedTemporaryFile is created 0600. Replacing an existing, shared
    # CHANGELOG with it would silently revoke every other reader's access, so
    # carry the previous mode over. New files keep the secure 0600 default.
    existing_mode: int | None = None
    try:
        if path.exists():
            # Copy permission bits only; never propagate setuid/setgid/sticky.
            existing_mode = stat.S_IMODE(path.stat().st_mode) & 0o777
    except OSError as exc:
        raise OutputError(f"could not inspect output file {path}: {exc}") from exc

    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(text)
        if existing_mode is not None:
            os.chmod(temporary_name, existing_mode)
        os.replace(temporary_name, path)
        temporary_name = None
    except OSError as exc:
        raise OutputError(f"could not write CHANGELOG to {path}: {exc}") from exc
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass


def _configure_logging(*, verbose: bool, json_format: bool) -> None:
    """Attach one deterministic handler to this package's logger.

    Configuring our own logger rather than the root logger means embedding the
    CLI in another process cannot silently reconfigure that process's logs.
    """
    formatter: logging.Formatter
    if json_format:
        formatter = _JsonFormatter()
    else:
        formatter = logging.Formatter("%(levelname)s: %(message)s")
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    LOGGER.handlers.clear()
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.DEBUG if verbose else logging.INFO)
    LOGGER.propagate = False


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _configure_logging(verbose=args.verbose, json_format=args.log_format == "json")

    try:
        if args.input is not None and str(args.input) == "-":
            raw = read_commits_from_stdin()
        elif args.input is not None:
            raw = read_commits_from_file(args.input)
        else:
            raw = read_commits_from_repo(args.repo, max_count=args.max_count)

        skipped = 0
        if args.skip_invalid:
            commits, skipped = parse_git_log_lenient(raw)
        else:
            commits = parse_git_log(raw)
        rendered = render_changelog(
            commits,
            version=args.release_version,
            release_date=args.release_date,
        )
        _write_output(rendered, args.output)
    except InputError as exc:
        LOGGER.error("invalid input: %s", exc)
        return EXIT_INPUT
    except SourceError as exc:
        LOGGER.error("source error: %s", exc)
        return EXIT_SOURCE
    except OutputError as exc:
        LOGGER.error("output error: %s", exc)
        return EXIT_OUTPUT
    except ChangelogError as exc:
        LOGGER.error("%s", exc)
        return EXIT_INPUT

    if skipped:
        LOGGER.warning("skipped %d non-Conventional commit(s)", skipped)
    if args.output is not None and str(args.output) != "-":
        LOGGER.info("wrote %d commits to %s", len(commits), args.output)
    return EXIT_OK
