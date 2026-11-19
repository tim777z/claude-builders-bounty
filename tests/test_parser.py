"""Unit tests for commit-history parsing and input validation."""

from __future__ import annotations

import unittest

from changelog_skill.model import InputError
from changelog_skill.parser import (
    MAX_SUBJECT_LENGTH,
    parse_commit_line,
    parse_git_log,
    parse_git_log_lenient,
)

SHA = "a" * 40


class ParseCommitLineTests(unittest.TestCase):
    def test_parses_simple_conventional_commit(self) -> None:
        commit = parse_commit_line(f"{SHA}\tfeat: add changelog generator")

        self.assertEqual(commit.sha, SHA)
        self.assertEqual(commit.kind, "feat")
        self.assertIsNone(commit.scope)
        self.assertEqual(commit.subject, "add changelog generator")
        self.assertFalse(commit.breaking)

    def test_parses_scope_and_breaking_marker(self) -> None:
        commit = parse_commit_line(f"{SHA}\tfeat(api)!: drop legacy endpoint")

        self.assertEqual(commit.scope, "api")
        self.assertTrue(commit.breaking)
        self.assertEqual(commit.subject, "drop legacy endpoint")

    def test_rejects_unknown_commit_type(self) -> None:
        with self.assertRaisesRegex(InputError, "unknown commit type 'wip'"):
            parse_commit_line(f"{SHA}\twip: half finished thing", line_number=7)

    def test_rejects_non_conventional_message(self) -> None:
        with self.assertRaisesRegex(InputError, "not a Conventional Commit"):
            parse_commit_line(f"{SHA}\tjust some message")

    def test_rejects_malformed_sha(self) -> None:
        with self.assertRaisesRegex(InputError, "sha must be"):
            parse_commit_line("not-a-sha\tfeat: valid subject")

    def test_rejects_missing_tab_separator(self) -> None:
        with self.assertRaisesRegex(InputError, "expected '<sha><TAB><message>'"):
            parse_commit_line(f"{SHA} feat: missing tab")

    def test_rejects_control_characters(self) -> None:
        with self.assertRaisesRegex(InputError, "control character"):
            parse_commit_line(f"{SHA}\tfeat: bad\x1b[31m subject")

    def test_rejects_unicode_line_separator(self) -> None:
        with self.assertRaisesRegex(InputError, "control character"):
            parse_commit_line(f"{SHA}\tfeat: first\u2028second line")

    def test_rejects_c1_control_character(self) -> None:
        with self.assertRaisesRegex(InputError, "control character"):
            parse_commit_line(f"{SHA}\tfeat: bad\u0085subject")

    def test_rejects_bidirectional_override(self) -> None:
        with self.assertRaisesRegex(InputError, "control character"):
            parse_commit_line(f"{SHA}\tfeat: spoof\u202ereversed")

    def test_rejects_oversized_subject(self) -> None:
        subject = "x" * (MAX_SUBJECT_LENGTH + 1)
        with self.assertRaisesRegex(InputError, "subject exceeds"):
            parse_commit_line(f"{SHA}\tfeat: {subject}")

    def test_rejects_empty_line(self) -> None:
        with self.assertRaisesRegex(InputError, "empty commit line"):
            parse_commit_line("   ")

    def test_error_messages_include_line_number(self) -> None:
        with self.assertRaisesRegex(InputError, "line 42:"):
            parse_commit_line("broken", line_number=42)


class ParseGitLogTests(unittest.TestCase):
    def test_skips_blank_lines_and_preserves_order(self) -> None:
        text = f"{SHA}\tfeat: first\n" "\n" f"{'b' * 40}\tfix: second\n"
        commits = parse_git_log(text)

        self.assertEqual([commit.subject for commit in commits], ["first", "second"])
        self.assertEqual([commit.kind for commit in commits], ["feat", "fix"])

    def test_enforces_line_limit(self) -> None:
        text = f"{SHA}\tfeat: first\n{'b' * 40}\tfix: second\n"
        with self.assertRaisesRegex(InputError, "safety limit"):
            parse_git_log(text, max_lines=1)

    def test_rejects_invalid_max_lines(self) -> None:
        with self.assertRaisesRegex(InputError, "max_lines must be"):
            parse_git_log("", max_lines=0)

    def test_empty_log_is_valid(self) -> None:
        self.assertEqual(parse_git_log(""), ())

    def test_rejects_unsafe_character_before_splitting(self) -> None:
        # U+2028 is a line separator to splitlines(), so the payload guard must
        # reject it before a fragment could be parsed as a separate commit.
        text = f"{SHA}\tfeat: first\u2028second"
        with self.assertRaisesRegex(InputError, "control character"):
            parse_git_log(text)

    def test_lenient_mode_does_not_silently_accept_unsafe_text(self) -> None:
        text = f"{SHA}\tfeat: ok\n{SHA}\tfeat: spoof\u202ereversed\n"
        with self.assertRaisesRegex(InputError, "control character"):
            parse_git_log_lenient(text)

    def test_rejects_non_text_payload(self) -> None:
        with self.assertRaisesRegex(InputError, "expected text"):
            parse_git_log(None)  # type: ignore[arg-type]


class LenientParseTests(unittest.TestCase):
    def test_skips_invalid_lines_and_reports_count(self) -> None:
        text = f"{SHA}\tfeat: valid\n" f"{SHA}\tnot conventional\n" f"{'b' * 40}\tfix: also valid\n"
        commits, skipped = parse_git_log_lenient(text)

        self.assertEqual([commit.subject for commit in commits], ["valid", "also valid"])
        self.assertEqual(skipped, 1)

    def test_enforces_the_same_line_limit(self) -> None:
        text = f"{SHA}\tfeat: ok\n{'b' * 40}\tfix: ok\n"
        with self.assertRaisesRegex(InputError, "safety limit"):
            parse_git_log_lenient(text, max_lines=1)
