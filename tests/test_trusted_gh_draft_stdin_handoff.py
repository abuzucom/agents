#!/usr/bin/env python3
"""An absolute draft body reaches raw gh on stdin, never as a path.

The wrapper reads the validated draft once through a descriptor that follows
no link. It passes `--body-file -` and the bytes on stdin. A swap of the draft
after validation cannot change what gh posts.
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
DRAFT_TEXT = "Summary line.\n"
SECRET_TEXT = "token\n"
STDIN_BODY = ["--body-file", "-"]
SAFE_DRAFT_OPEN = trusted_gh._safe_draft_open_supported()
NO_SAFE_DRAFT_OPEN = "this platform lacks dir_fd and O_NOFOLLOW, so the handoff cannot run"


@unittest.skipUnless(SAFE_DRAFT_OPEN, NO_SAFE_DRAFT_OPEN)
class DraftStdinHandoffTest(unittest.TestCase):
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
        self.draft = drafts / "body.md"
        self.draft.write_bytes(DRAFT_TEXT.encode("ascii"))
        self.secret = self.root / "secret.txt"
        self.secret.write_bytes(SECRET_TEXT.encode("ascii"))
        self.calls = []
        self.inputs = []

    def run_wrapper(self, argv: list, before_account_check=None) -> tuple[int, str]:
        """Run main() with `run` arguments and return the code and stderr."""
        response = subprocess.CompletedProcess(
            [], 0, json.dumps({"html_url": "https://github.com/x/y/1"}), "")

        def record(_repo_root, arguments, **keywords):
            self.calls.append(list(arguments))
            self.inputs.append(keywords.get("input_text"))
            return response

        def check_account(_repo_root):
            if before_account_check is not None:
                before_account_check()

        stderr = io.StringIO()
        with patch.object(sys, "argv", ["trusted_gh.py", "run", *argv]), \
                patch.object(trusted_gh.os, "getcwd", return_value=str(self.root)), \
                patch.object(trusted_gh, "repository_target", return_value=REPOSITORY), \
                patch.object(trusted_gh, "verify_account", side_effect=check_account), \
                patch.object(trusted_gh, "run_gh", side_effect=record), \
                redirect_stdout(io.StringIO()), redirect_stderr(stderr):
            code = trusted_gh.main()
        return code, stderr.getvalue()

    def assert_stdin_handoff(self, argv: list) -> None:
        """Assert gh receives the draft bytes on stdin and never the draft path."""
        self.calls.clear()
        self.inputs.clear()
        code, stderr = self.run_wrapper(argv)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.inputs, [DRAFT_TEXT])
        self.assertNotIn(str(self.draft), " ".join(self.calls[0]))
        self.assertEqual(self.calls[0][-len(STDIN_BODY):], STDIN_BODY)

    def test_absolute_draft_goes_stdin(self):
        for body in (["--body-file", str(self.draft)], [f"--body-file={self.draft}"],
                     ["-F", str(self.draft)], [f"-F{self.draft}"], [f"-F={self.draft}"]):
            with self.subTest(body=body):
                self.assert_stdin_handoff(["issue", "create", "--title", "T", *body, "--web"])

    def test_pull_edit_draft_goes_stdin(self):
        self.assert_stdin_handoff(
            ["pr", "edit", "7", "--body-file", str(self.draft), "--add-reviewer", "someone"])

    @unittest.skipIf(os.name == "nt", "Symlink creation needs privileges on Windows")
    def test_swap_after_check_ignored(self):
        def swap_draft():
            self.draft.unlink()
            self.draft.symlink_to(self.secret)

        code, stderr = self.run_wrapper(
            ["issue", "create", "--title", "T", "--body-file", str(self.draft), "--web"],
            before_account_check=swap_draft)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(self.inputs, [DRAFT_TEXT])

    def test_stdin_body_stays_unchanged(self):
        code, stderr = self.run_wrapper(
            ["issue", "create", "--title", "T", "--body-file", "-", "--web"])
        self.assertEqual(code, 0, stderr)
        self.assertEqual(self.inputs, [None])


if __name__ == "__main__":
    unittest.main()
