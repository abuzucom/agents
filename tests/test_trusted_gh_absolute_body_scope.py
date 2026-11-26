#!/usr/bin/env python3
"""An absolute body file outside the drafts directory never reaches raw gh.

Raw gh reads any readable file and posts its bytes. A write shape outside the
REST forms may name an absolute body only when that path is a regular file
directly in the repository's `.comment-drafts/` directory.
"""
import io
import json
import os
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
USAGE_EXIT_CODE = 2


class AbsoluteBodyScopeTest(unittest.TestCase):
    """Run `trusted_gh.py run` in a temporary checkout with a recording CLI."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        git_dir = self.root / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text(f"ref: refs/heads/{HEAD_BRANCH}\n", encoding="utf-8")
        self.drafts = self.root / trusted_gh.COMMENT_DRAFT_DIRECTORY
        self.drafts.mkdir()
        self.draft = self.drafts / "body.md"
        self.draft.write_bytes(b"Summary line.\n")
        self.outside = self.root / "secret.txt"
        self.outside.write_bytes(b"token\n")
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

    def assert_refused(self, body: str) -> None:
        """Assert an issue create naming one body exits 2 and starts no gh process."""
        self.calls.clear()
        code, stderr = self.run_wrapper(
            ["issue", "create", "--title", "T", "--body-file", body, "--web"])
        self.assertEqual(code, USAGE_EXIT_CODE, stderr)
        self.assertIn(trusted_gh.COMMENT_DRAFT_DIRECTORY, stderr)
        self.assertEqual(self.calls, [])

    def test_outside_absolute_body_refused(self):
        self.assert_refused(str(self.outside))
        self.assert_refused(os.devnull)

    def test_nested_absolute_body_refused(self):
        nested = self.drafts / "sub"
        nested.mkdir()
        (nested / "body.md").write_bytes(b"text\n")
        self.assert_refused(str(nested / "body.md"))

    def test_traversing_absolute_body_refused(self):
        self.assert_refused(str(self.drafts / ".." / "secret.txt"))

    def test_missing_absolute_body_refused(self):
        self.assert_refused(str(self.drafts / "missing.md"))

    @unittest.skipIf(os.name == "nt", "Symlink creation needs privileges on Windows")
    def test_symlinked_absolute_body_refused(self):
        link = self.drafts / "link.md"
        link.symlink_to(self.outside)
        self.assert_refused(str(link))

    def test_attached_outside_body_refused(self):
        self.calls.clear()
        code, _stderr = self.run_wrapper(
            ["pr", "edit", "7", f"-F{self.outside}", "--add-reviewer", "someone"])
        self.assertEqual(code, USAGE_EXIT_CODE)
        self.assertEqual(self.calls, [])

    def test_draft_absolute_body_passthrough(self):
        code, stderr = self.run_wrapper(
            ["issue", "create", "--title", "T", "--body-file", str(self.draft), "--web"])
        self.assertEqual(code, 0, stderr)
        self.assertEqual(len(self.calls), 1)


if __name__ == "__main__":
    unittest.main()
