"""Command-line interface with predictable exit codes and atomic output."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
from datetime import date as date_type
from pathlib import Path

from . import __version__
from .git import read_commits_from_file, read_commits_from_repo
from .model import ChangelogError, InputError, OutputError, SourceError
from .parser import parse_git_log, parse_git_log_lenient
from .render import render_changelog

LOGGER = logging.getLogger("changelog_skill")

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
    return parser


def _write_output(text: str, destination: Path | None) -> None:
    if destination is None or str(destination) == "-":
        sys.stdout.write(text)
        return

    path = destination.expanduser().resolve()
    if not path.parent.is_dir():
        raise OutputError(f"output directory does not exist: {path.parent}")

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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    try:
        if args.input is not None and str(args.input) == "-":
            raw = sys.stdin.read()
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
