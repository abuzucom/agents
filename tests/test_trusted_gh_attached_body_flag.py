#!/usr/bin/env python3
"""Attached short body file spellings get the relative draft refusal.

gh parses `-F<path>` and `-F=<path>` as `--body-file <path>`. A relative path
in either spelling must exit 2 before any gh process starts.
"""
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import trusted_gh

REPOSITORY = "example-owner/example-repo"
HEAD_BRANCH = "feat/example-change"
DRAFT_ARGUMENT = ".comment-drafts/body.md"
USAGE_EXIT_CODE = 2


class AttachedBodyFlagTest(unittest.TestCase):
    """Run `trusted_gh.py run` in a temporary checkout with a recording CLI."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        git_dir = self.root / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text(f"ref: refs/heads/{HEAD_BRANCH}\n", encoding="utf-8")
        drafts = self.root / trusted_gh.COMMENT_DRAFT_DIRECTORY
        drafts.mkdir()
        (drafts / "body.md").write_bytes(b"Summary line.\n")
        self.absolute = str(drafts / "body.md")
        self.calls = []

    def run_wrapper(self, argv: list) -> tuple[int, str]:
        """Run main() with `run` arguments and return the code and stderr."""
        response = subprocess.CompletedProcess(
            [], 0, json.dumps({"html_url": "https://github.com/x/y/1"}), "")

        def record(_repo_root, arguments, **_keywords):
            self.calls.append(list(arguments))
            return response

        stderr = io.StringIO()
        with patch.object(sys, "argv", ["trusted_gh.py", "run", *argv]), \
                patch.object(trusted_gh.os, "getcwd", return_value=str(self.root)), \
                patch.object(trusted_gh, "repository_target", return_value=REPOSITORY), \
                patch.object(trusted_gh, "verify_account", return_value=None), \
                patch.object(trusted_gh, "run_gh", side_effect=record), \
                redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            code = trusted_gh.main()
        return code, stderr.getvalue()

    def test_attached_relative_body_refused(self):
        for spelling in (f"-F{DRAFT_ARGUMENT}", f"-F={DRAFT_ARGUMENT}"):
            for command in (["issue", "create", "--title", "T"], ["pr", "edit", "7"]):
                with self.subTest(spelling=spelling, command=command):
                    self.calls.clear()
                    code, stderr = self.run_wrapper([*command, spelling, "--web"])
                    self.assertEqual(code, USAGE_EXIT_CODE, stderr)
                    self.assertEqual(self.calls, [])

    @unittest.skipUnless(trusted_gh._safe_draft_open_supported(),
                         "an absolute draft exits 2 without dir_fd and O_NOFOLLOW")
    def test_attached_absolute_body_passthrough(self):
        for spelling in (f"-F{self.absolute}", f"-F={self.absolute}"):
            with self.subTest(spelling=spelling):
                self.calls.clear()
                code, stderr = self.run_wrapper(
                    ["issue", "create", "--title", "T", spelling, "--web"])
                self.assertEqual(code, 0, stderr)
                self.assertEqual(len(self.calls), 1)


if __name__ == "__main__":
    unittest.main()
