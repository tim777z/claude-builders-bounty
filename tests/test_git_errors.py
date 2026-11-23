"""Structured failure paths of the git/filesystem adapters.

A hostile or broken history can make git time out, emit undecodable bytes,
exceed the size cap or simply fail. Each case must become a SourceError so the
CLI maps it to a stable exit code instead of leaking a traceback.
"""

from __future__ import annotations

import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from changelog_skill.git import (
    GIT_TIMEOUT_SECONDS,
    MAX_INPUT_BYTES,
    read_commits_from_file,
    read_commits_from_repo,
    read_commits_from_stdin,
)
from changelog_skill.model import SourceError

SHA = "a" * 40


class GitProcessErrorTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        (self.repo / ".git").mkdir()

    def test_rejects_directory_without_git_metadata(self) -> None:
        plain = self.repo / "plain"
        plain.mkdir()
        with self.assertRaisesRegex(SourceError, "not a git repository"):
            read_commits_from_repo(plain)

    def test_timeout_becomes_source_error(self) -> None:
        timeout = subprocess.TimeoutExpired(cmd="git log", timeout=GIT_TIMEOUT_SECONDS)
        with patch("changelog_skill.git.subprocess.run", side_effect=timeout):
            with self.assertRaisesRegex(SourceError, "could not read git history"):
                read_commits_from_repo(self.repo)

    def test_missing_git_executable_becomes_source_error(self) -> None:
        with patch("changelog_skill.git.subprocess.run", side_effect=FileNotFoundError("git")):
            with self.assertRaisesRegex(SourceError, "could not read git history"):
                read_commits_from_repo(self.repo)

    def test_undecodable_git_output_becomes_source_error(self) -> None:
        decode_error = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        with patch("changelog_skill.git.subprocess.run", side_effect=decode_error):
            with self.assertRaisesRegex(SourceError, "could not read git history"):
                read_commits_from_repo(self.repo)

    def test_oversized_git_output_is_rejected_before_parsing(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="a" * (MAX_INPUT_BYTES + 1), stderr=""
        )
        with patch("changelog_skill.git.subprocess.run", return_value=completed):
            with self.assertRaisesRegex(SourceError, "exceeds the 1 MiB safety limit"):
                read_commits_from_repo(self.repo)

    def test_git_failure_detail_is_bounded(self) -> None:
        # stderr from a failing git hook must not flood logs or memory.
        completed = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr="fatal: " + "x" * 2000
        )
        with patch("changelog_skill.git.subprocess.run", return_value=completed):
            with self.assertRaises(SourceError) as raised:
                read_commits_from_repo(self.repo)
        self.assertLessEqual(len(str(raised.exception)), 560)
        self.assertNotIn("x" * 501, str(raised.exception))


class StreamErrorTests(unittest.TestCase):
    def test_stdin_read_failure_is_structured(self) -> None:
        class FailingStream:
            def read(self, size: int) -> str:
                raise OSError("broken pipe")

        with self.assertRaisesRegex(SourceError, "could not read stdin"):
            read_commits_from_stdin(FailingStream())  # type: ignore[arg-type]

    def test_stdin_decode_failure_is_structured(self) -> None:
        class FailingStream:
            def read(self, size: int) -> str:
                raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

        with self.assertRaisesRegex(SourceError, "could not read stdin"):
            read_commits_from_stdin(FailingStream())  # type: ignore[arg-type]

    def test_binary_stdin_is_rejected(self) -> None:
        with self.assertRaisesRegex(SourceError, "stdin did not return text"):
            read_commits_from_stdin(io.BytesIO(b"not text"))  # type: ignore[arg-type]


class FileErrorTests(unittest.TestCase):
    def test_unreadable_file_is_structured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "commits.txt"
            source.write_text(f"{SHA}\tfeat: ok\n", encoding="utf-8")
            with patch.object(Path, "open", side_effect=PermissionError("denied")):
                with self.assertRaisesRegex(SourceError, "could not read input file"):
                    read_commits_from_file(source)


if __name__ == "__main__":
    unittest.main()
