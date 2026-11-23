"""Tests for the git/filesystem adapters, including injection resistance."""

from __future__ import annotations

import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from changelog_skill.git import (
    MAX_INPUT_BYTES,
    read_commits_from_file,
    read_commits_from_repo,
    read_commits_from_stdin,
)
from changelog_skill.model import SourceError

SHA = "a" * 40


class GitAdapterTests(unittest.TestCase):
    def test_rejects_invalid_max_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".git").mkdir()
            with self.assertRaisesRegex(SourceError, "max_count must be"):
                read_commits_from_repo(repo, max_count=0)

    def test_rejects_missing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "nope"
            with self.assertRaisesRegex(SourceError, "does not exist"):
                read_commits_from_repo(missing)

    def test_rejects_non_git_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(SourceError, "not a git repository"):
                read_commits_from_repo(Path(directory))

    def test_repo_path_is_one_literal_argument_without_a_shell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo; echo pwned"
            (repo / ".git").mkdir(parents=True)
            completed = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=f"{SHA}\tfeat: ok\n", stderr=""
            )

            with patch("changelog_skill.git.subprocess.run", return_value=completed) as run:
                output = read_commits_from_repo(repo, max_count=5)

            argv = run.call_args.args[0]
            self.assertEqual(output, f"{SHA}\tfeat: ok\n")
            self.assertEqual(argv[2], str(repo.resolve()))
            self.assertIn("--max-count=5", argv)
            self.assertIn("--pretty=tformat:%H%x09%s", argv)
            self.assertFalse(run.call_args.kwargs["shell"])

    def test_propagates_git_failure_as_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".git").mkdir()
            completed = subprocess.CompletedProcess(
                args=[], returncode=128, stdout="", stderr="fatal: bad revision"
            )
            with patch("changelog_skill.git.subprocess.run", return_value=completed):
                with self.assertRaisesRegex(SourceError, "git log failed"):
                    read_commits_from_repo(repo)


class StdinAdapterTests(unittest.TestCase):
    def test_reads_valid_text(self) -> None:
        stream = io.StringIO(f"{SHA}\tfeat: ok\n")
        self.assertEqual(read_commits_from_stdin(stream), f"{SHA}\tfeat: ok\n")

    def test_rejects_oversized_stream(self) -> None:
        stream = io.StringIO("a" * (MAX_INPUT_BYTES + 1))
        with self.assertRaisesRegex(SourceError, "stdin history exceeds"):
            read_commits_from_stdin(stream)

    def test_reads_no_more_than_the_cap_plus_one_character(self) -> None:
        class CountingStream(io.StringIO):
            requested: int | None = None

            def read(self, size: int | None = -1) -> str:  # type: ignore[override]
                CountingStream.requested = size
                return super().read(size)

        stream = CountingStream("x")
        read_commits_from_stdin(stream)
        self.assertEqual(CountingStream.requested, MAX_INPUT_BYTES + 1)


class FileAdapterTests(unittest.TestCase):
    def test_reads_valid_utf8_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "commits.txt"
            source.write_text(f"{SHA}\tfeat: ok\n", encoding="utf-8")
            self.assertEqual(read_commits_from_file(source), f"{SHA}\tfeat: ok\n")

    def test_rejects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(SourceError, "does not exist"):
                read_commits_from_file(Path(directory) / "missing.txt")

    def test_rejects_invalid_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.txt"
            source.write_bytes(b"\xff\xfe\x00not utf8")
            with self.assertRaisesRegex(SourceError, "could not read input file"):
                read_commits_from_file(source)

    def test_rejects_oversized_file_by_byte_count(self) -> None:
        # A multi-byte payload must be measured in bytes, not characters: a
        # 1 MiB character limit would let a 4 MiB file into the parser.
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "large.txt"
            source.write_bytes(("😀" * (MAX_INPUT_BYTES // 4 + 1)).encode("utf-8"))
            with self.assertRaisesRegex(SourceError, "exceeds the 1 MiB safety limit"):
                read_commits_from_file(source)

    def test_reads_file_larger_than_the_byte_cap_in_characters(self) -> None:
        # Conversely, a file just under the byte cap is valid even though its
        # payload is far fewer than MAX_INPUT_BYTES Unicode characters.
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "multibyte.txt"
            source.write_bytes(("😀" * 1000).encode("utf-8"))
            self.assertEqual(read_commits_from_file(source), "😀" * 1000)
