"""Unit tests for CHANGELOG rendering and Markdown safety."""

from __future__ import annotations

import unittest

from changelog_skill.model import Commit, InputError
from changelog_skill.parser import parse_git_log
from changelog_skill.render import escape_markdown, render_changelog

SHA = "0123456789abcdef" * 2 + "01234567"
DATE = "2026-11-18"


def commit(kind: str, subject: str, **overrides: object) -> Commit:
    values: dict[str, object] = {
        "sha": SHA,
        "kind": kind,
        "scope": None,
        "subject": subject,
        "breaking": False,
    }
    values.update(overrides)
    return Commit(**values)  # type: ignore[arg-type]


class EscapeMarkdownTests(unittest.TestCase):
    def test_neutralises_links_html_and_emphasis(self) -> None:
        hostile = "[click](javascript:alert(1)) <script> *bold* `code` | pipe"
        escaped = escape_markdown(hostile)

        self.assertNotIn("[click]", escaped)
        self.assertNotIn("<script>", escaped)
        self.assertIn("\\[", escaped)
        self.assertIn("\\<", escaped)


class RenderChangelogTests(unittest.TestCase):
    def test_groups_by_type_in_canonical_order(self) -> None:
        commits = (
            commit("fix", "repair parser"),
            commit("feat", "add renderer"),
            commit("docs", "document usage"),
        )
        output = render_changelog(commits, version="0.1.0", release_date=DATE)

        self.assertLess(output.index("### Features"), output.index("### Bug Fixes"))
        self.assertLess(output.index("### Bug Fixes"), output.index("### Documentation"))
        self.assertIn(f"({SHA[:7]})", output)
        self.assertTrue(output.startswith("# Changelog\n"))
        self.assertIn("## [0.1.0] - 2026-11-18", output)

    def test_breaking_changes_get_a_dedicated_section(self) -> None:
        commits = (commit("feat", "remove v1", breaking=True, scope="api"),)
        output = render_changelog(commits, version="1.0.0", release_date=DATE)

        self.assertIn("### BREAKING CHANGES", output)
        self.assertIn("**feat** **(api)**: remove v1", output)
        self.assertNotIn("### Features", output)

    def test_escapes_untrusted_subjects(self) -> None:
        commits = (commit("fix", "[x](javascript:alert(1))"),)
        output = render_changelog(commits, version="0.1.0", release_date=DATE)

        self.assertNotIn("[x](javascript", output)

    def test_empty_history_renders_explanatory_placeholder(self) -> None:
        output = render_changelog((), version="0.1.0", release_date=DATE)

        self.assertIn("_No Conventional Commits were found in the selected range._", output)

    def test_rejects_invalid_version(self) -> None:
        with self.assertRaisesRegex(InputError, "version must be"):
            render_changelog((), version="bad version [x]", release_date=DATE)

    def test_rejects_invalid_date(self) -> None:
        with self.assertRaisesRegex(InputError, "YYYY-MM-DD"):
            render_changelog((), version="0.1.0", release_date="18/11/2026")

    def test_rejects_impossible_date(self) -> None:
        with self.assertRaisesRegex(InputError, "not a real calendar date"):
            render_changelog((), version="0.1.0", release_date="2026-02-30")

    def test_renders_output_of_parser_end_to_end(self) -> None:
        commits = parse_git_log(f"{SHA}\tfeat(cli): add --output flag\n")
        output = render_changelog(commits, version="0.1.0", release_date=DATE)

        self.assertIn("add --output flag", output)
        self.assertIn("### Features", output)
