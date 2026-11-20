"""End-to-end CLI tests covering success paths and exit-code contracts."""

from __future__ import annotations

import contextlib
import io
import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from changelog_skill.cli import EXIT_INPUT, EXIT_OK, EXIT_OUTPUT, EXIT_SOURCE, main

SHA = "a" * 40
VALID_LINE = f"{SHA}\tfeat(cli): add changelog command\n"


def run_cli(arguments: list[str]) -> tuple[int, str]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        status = main(arguments)
    return status, stdout.getvalue()


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)

    def tearDown(self) -> None:
        logging.disable(logging.NOTSET)

    def test_writes_changelog_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "commits.txt"
            target = Path(directory) / "CHANGELOG.md"
            source.write_text(VALID_LINE, encoding="utf-8")

            status, stdout = run_cli(
                [
                    "--input",
                    str(source),
                    "--release-version",
                    "0.1.0",
                    "--release-date",
                    "2026-11-18",
                    "--output",
                    str(target),
                ]
            )

            self.assertEqual(status, EXIT_OK)
            self.assertEqual(stdout, "")
            rendered = target.read_text(encoding="utf-8")
            self.assertIn("## [0.1.0] - 2026-11-18", rendered)
            self.assertIn("### Features", rendered)
            self.assertIn("add changelog command", rendered)

    def test_writes_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "commits.txt"
            source.write_text(VALID_LINE, encoding="utf-8")
            status, stdout = run_cli(["--input", str(source), "--release-version", "1.0.0"])
            self.assertEqual(status, EXIT_OK)
            self.assertIn("# Changelog", stdout)

    def test_reads_from_stdin(self) -> None:
        with patch("sys.stdin", io.StringIO(VALID_LINE)):
            status, stdout = run_cli(["--input", "-", "--release-version", "0.1.0"])
        self.assertEqual(status, EXIT_OK)
        self.assertIn("add changelog command", stdout)

    def test_oversized_stdin_returns_source_exit_code(self) -> None:
        with patch("sys.stdin", io.StringIO("x" * (1024 * 1024 + 1))):
            status, _ = run_cli(["--input", "-", "--release-version", "0.1.0"])
        self.assertEqual(status, EXIT_SOURCE)

    def test_malformed_commit_returns_input_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "commits.txt"
            source.write_text(f"{SHA}\tnot conventional\n", encoding="utf-8")
            status, _ = run_cli(["--input", str(source), "--release-version", "0.1.0"])
            self.assertEqual(status, EXIT_INPUT)

    def test_invalid_release_version_returns_input_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "commits.txt"
            source.write_text(VALID_LINE, encoding="utf-8")
            status, _ = run_cli(["--input", str(source), "--release-version", "[bad] version"])
            self.assertEqual(status, EXIT_INPUT)

    def test_missing_input_returns_source_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            status, _ = run_cli(
                [
                    "--input",
                    str(Path(directory) / "missing.txt"),
                    "--release-version",
                    "0.1.0",
                ]
            )
            self.assertEqual(status, EXIT_SOURCE)

    def test_bad_output_directory_returns_output_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "commits.txt"
            source.write_text(VALID_LINE, encoding="utf-8")
            status, _ = run_cli(
                [
                    "--input",
                    str(source),
                    "--release-version",
                    "0.1.0",
                    "--output",
                    str(Path(directory) / "missing" / "CHANGELOG.md"),
                ]
            )
            self.assertEqual(status, EXIT_OUTPUT)

    def test_skip_invalid_allows_legacy_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "commits.txt"
            source.write_text(f"{SHA}\tnot conventional\n{SHA}\tfeat: kept\n", encoding="utf-8")
            status, stdout = run_cli(
                ["--input", str(source), "--release-version", "0.1.0", "--skip-invalid"]
            )
            self.assertEqual(status, EXIT_OK)
            self.assertIn("kept", stdout)
            self.assertNotIn("not conventional", stdout)

    def test_tool_version_flag(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), self.assertRaises(SystemExit) as raised:
            main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("changelog-skill", stdout.getvalue())

    def _run_with_stderr(self, arguments: list[str]) -> tuple[int, str]:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status, _ = run_cli(arguments)
        return status, stderr.getvalue()

    def test_json_log_format_emits_valid_json_lines(self) -> None:
        logging.disable(logging.NOTSET)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "commits.txt"
            target = Path(directory) / "CHANGELOG.md"
            source.write_text(VALID_LINE, encoding="utf-8")

            status, stderr = self._run_with_stderr(
                [
                    "--input",
                    str(source),
                    "--release-version",
                    "0.1.0",
                    "--output",
                    str(target),
                    "--log-format",
                    "json",
                    "--verbose",
                ]
            )

            self.assertEqual(status, EXIT_OK)
            lines = stderr.splitlines()
            self.assertTrue(lines, "expected at least one structured log line")
            for line in lines:
                payload = json.loads(line)
                self.assertEqual(payload["logger"], "changelog_skill")
                self.assertIn("level", payload)
                self.assertIn("message", payload)

    def test_default_log_format_is_human_readable_text(self) -> None:
        logging.disable(logging.NOTSET)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "commits.txt"
            target = Path(directory) / "CHANGELOG.md"
            source.write_text(VALID_LINE, encoding="utf-8")

            status, stderr = self._run_with_stderr(
                ["--input", str(source), "--release-version", "0.1.0", "--output", str(target)]
            )

            self.assertEqual(status, EXIT_OK)
            self.assertTrue(stderr.startswith("INFO: "))
