#!/usr/bin/env python3
"""The hardened Git probe reports tracked paths or fails closed."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
import _git_probe

GIT_TIMEOUT_SECONDS = 15


class TrackedPathsTest(unittest.TestCase):
    """tracked_paths names tracked paths and returns None on any failure."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True,
                       timeout=GIT_TIMEOUT_SECONDS)
        (self.root / "tracked.txt").write_text("x", encoding="utf-8")
        (self.root / "loose.txt").write_text("x", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "tracked.txt"], check=True,
                       timeout=GIT_TIMEOUT_SECONDS)

    def test_tracked_and_untracked(self) -> None:
        tracked = _git_probe.tracked_paths(str(self.root), ["tracked.txt", "loose.txt"])
        self.assertEqual(tracked, frozenset({"tracked.txt"}))

    def test_directory_reports_contents(self) -> None:
        (self.root / "sub").mkdir()
        (self.root / "sub" / "kept.txt").write_text("x", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "sub/kept.txt"], check=True,
                       timeout=GIT_TIMEOUT_SECONDS)
        self.assertEqual(_git_probe.tracked_paths(str(self.root), ["sub"]),
                         frozenset({"sub/kept.txt"}))

    def test_not_a_repository_fails(self) -> None:
        with tempfile.TemporaryDirectory() as other:
            self.assertIsNone(_git_probe.tracked_paths(other, ["x"]))

    def test_timeout_fails(self) -> None:
        error = subprocess.TimeoutExpired(["git"], 1)
        with patch.object(_git_probe.subprocess, "run", side_effect=error):
            self.assertIsNone(_git_probe.tracked_paths(str(self.root), ["tracked.txt"]))

    def test_missing_git_fails(self) -> None:
        with patch.object(_git_probe.subprocess, "run", side_effect=FileNotFoundError("git")):
            self.assertIsNone(_git_probe.tracked_paths(str(self.root), ["tracked.txt"]))

    def test_undecodable_output_fails(self) -> None:
        undecodable = subprocess.CompletedProcess([], 0, b"caf\xe9\0", b"")
        with patch.object(_git_probe.subprocess, "run", return_value=undecodable):
            self.assertIsNone(_git_probe.tracked_paths(str(self.root), ["tracked.txt"]))

    def test_oversized_output_fails(self) -> None:
        large = subprocess.CompletedProcess([], 0, b"a\0" * _git_probe.MAX_OUTPUT_BYTES, b"")
        with patch.object(_git_probe.subprocess, "run", return_value=large):
            self.assertIsNone(_git_probe.tracked_paths(str(self.root), ["tracked.txt"]))


if __name__ == "__main__":
    unittest.main()
