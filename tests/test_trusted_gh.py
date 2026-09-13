#!/usr/bin/env python3
"""Tests for trusted GitHub CLI lookup and account parsing."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import trusted_gh


class AccountParsingTest(unittest.TestCase):
    """Authenticated account output stays bounded and structured."""

    def test_numeric_id_and_login_parse(self):
        account = trusted_gh.parse_account("1234567\toctocat\n")
        self.assertEqual(account, {"id": 1234567, "login": "octocat"})

    def test_malformed_account_output_fails(self):
        values = ("", "id\toctocat", "1\tbad/login", "1\toctocat\textra")
        for value in values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    trusted_gh.parse_account(value)

    def test_account_output_has_a_bound(self):
        with self.assertRaises(ValueError):
            trusted_gh.parse_account("1\t" + "a" * 300)


class ExecutableLookupTest(unittest.TestCase):
    """Repository-local programs cannot replace GitHub CLI."""

    def test_repository_gh_is_excluded(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            executable = repository / ("gh.exe" if os.name == "nt" else "gh")
            executable.write_text("untrusted executable\n", encoding="utf-8")
            executable.chmod(0o755)
            environment = {"PATH": str(repository)}
            with patch.dict(os.environ, environment, clear=False):
                with self.assertRaises(FileNotFoundError):
                    trusted_gh.resolve_gh(repository)


class TrustedRunnerSafetyTest(unittest.TestCase):
    """The wrapper rejects high-risk mutations before account lookup."""

    def test_repository_deletion_denies(self):
        result = subprocess.run(
            [sys.executable, str(REPOSITORY_ROOT / "scripts" / "trusted_gh.py"),
             "run", "repo", "delete", "OWNER/REPO"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("removes work", result.stderr)

    def test_literal_newline_escape_in_pr_body_is_rejected(self):
        result = subprocess.run(
            [sys.executable, str(REPOSITORY_ROOT / "scripts" / "trusted_gh.py"),
             "run", "pr", "edit", "45", "--body", "line1\\n\\nline2"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("literal escape text", result.stderr)

    def test_managed_proxy_placeholder_is_removed(self):
        captured = {}

        def runner(arguments, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(arguments, 0, "", "")

        with patch.dict(os.environ, {
                "HTTP_PROXY": "http://127.0.0.1:9",
                "HTTPS_PROXY": "127.0.0.1:9",
                "ALL_PROXY": "http://proxy.example.test:8080",
        }, clear=False):
            with patch.object(trusted_gh, "resolve_gh", return_value=sys.executable):
                with patch.object(trusted_gh, "_safe_directory",
                                  return_value=Path(tempfile.gettempdir())):
                    trusted_gh.run_gh(Path(tempfile.gettempdir()), ["api", "user"],
                                      runner=runner)

        self.assertNotIn("HTTP_PROXY", captured["env"])
        self.assertNotIn("HTTPS_PROXY", captured["env"])
        self.assertEqual(captured["env"]["ALL_PROXY"],
                         "http://proxy.example.test:8080")


if __name__ == "__main__":
    unittest.main()
