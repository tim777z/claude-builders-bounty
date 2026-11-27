"""Security boundary regression tests for public entry points.

These tests pin the untrusted-input contract at the CLI/library boundary:
size caps, control-character rejection, and path/format validation. They
complement module-specific tests by asserting the public surface behaves
consistently as an attacker-facing interface.
"""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from changelog_skill.git import MAX_INPUT_BYTES, read_commits_from_file, read_commits_from_stdin
from changelog_skill.model import InputError, SourceError
from changelog_skill.parser import parse_git_log, parse_git_log_lenient
from changelog_skill.render import render_changelog

SHA = "a" * 40
VALID_LINE = f"{SHA}\tfeat: ok\n"


class PublicBoundaryTests(unittest.TestCase):
    def test_parse_git_log_rejects_oversized_history(self) -> None:
        text = VALID_LINE * 5001
        with self.assertRaisesRegex(InputError, "safety limit"):
            parse_git_log(text)

    def test_parse_git_log_lenient_rejects_oversized_history(self) -> None:
        text = VALID_LINE * 5001
        with self.assertRaisesRegex(InputError, "safety limit"):
            parse_git_log_lenient(text)

    def test_parse_git_log_rejects_control_characters(self) -> None:
        with self.assertRaisesRegex(InputError, "control character"):
            parse_git_log(f"{SHA}\tfeat: bad\x00subject\n")

    def test_parse_git_log_rejects_bidi_override(self) -> None:
        with self.assertRaisesRegex(InputError, "control character"):
            parse_git_log(f"{SHA}\tfeat: spoof\u202ereversed\n")

    def test_read_commits_from_file_rejects_oversized_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "big.txt"
            source.write_bytes(b"a" * (MAX_INPUT_BYTES + 1))
            with self.assertRaisesRegex(SourceError, "1 MiB safety limit"):
                read_commits_from_file(source)

    def test_read_commits_from_stdin_rejects_oversized_input(self) -> None:
        stream = io.StringIO("a" * (MAX_INPUT_BYTES + 1))
        with self.assertRaisesRegex(SourceError, "1 MiB safety limit"):
            read_commits_from_stdin(stream)

    def test_render_changelog_rejects_invalid_version(self) -> None:
        with self.assertRaisesRegex(InputError, "version must be"):
            render_changelog((), version="../bad", release_date="2026-01-01")

    def test_render_changelog_rejects_invalid_date(self) -> None:
        with self.assertRaisesRegex(InputError, "YYYY-MM-DD"):
            render_changelog((), version="0.1.0", release_date="2026/01/01")

    def test_render_changelog_escapes_hostile_subject(self) -> None:
        commits = parse_git_log(f"{SHA}\tfeat: <script>alert(1)</script>[x](javascript:1)\n")
        rendered = render_changelog(commits, version="0.1.0", release_date="2026-01-01")
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("[x](javascript:1)", rendered)
        self.assertIn("\\<script\\>", rendered)


if __name__ == "__main__":
    unittest.main()
