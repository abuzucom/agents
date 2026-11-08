#!/usr/bin/env python3
"""Tests for trusted_gh output stream encoding resilience."""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

# Use a writable checkout directory for test fixtures on Windows runners.
tempfile.tempdir = str(REPOSITORY_ROOT)

import trusted_gh


class RestrictedEncodingStream(io.TextIOBase):
    """Text stream that simulates a restricted terminal encoding such as cp1252."""

    def __init__(self, encoding: str = "cp1252") -> None:
        self._encoding = encoding
        self.buffer = io.BytesIO()

    @property
    def encoding(self) -> str:
        return self._encoding

    def write(self, s: str) -> int:
        encoded = s.encode(self._encoding)
        self.buffer.write(encoded)
        return len(s)


class TrustedGhEncodingTest(unittest.TestCase):
    """Verify trusted_gh output handling on streams with restricted encodings."""

    def test_run_requested_command_handles_unencodable_output(self) -> None:
        fake_result = subprocess.CompletedProcess(
            args=["gh", "run", "view"],
            returncode=0,
            stdout="run log with BOM \ufeff and symbol \u2713\n",
            stderr="",
        )
        fake_stdout = RestrictedEncodingStream("cp1252")
        fake_stderr = RestrictedEncodingStream("cp1252")

        with patch.object(trusted_gh, "authenticated_account", return_value={"id": 1, "login": "test"}):
            with patch.object(trusted_gh, "run_gh", return_value=fake_result):
                with patch.object(sys, "stdout", fake_stdout), patch.object(sys, "stderr", fake_stderr):
                    ret = trusted_gh._run_requested_command(REPOSITORY_ROOT, ["run", "view", "123"])
                    self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()
