#!/usr/bin/env python3
"""Global options before the command keep every body file check.

gh accepts `-R`, `--repo`, and `--hostname` before the command. The wrapper
finds the issue or pull request command where repository context finds it.
A leading global option therefore skips neither the refusal nor the stdin
handoff.
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
DRAFT_TEXT = "Summary line.\n"
USAGE_EXIT_CODE = 2
SAFE_DRAFT_OPEN = trusted_gh._safe_draft_open_supported()
NO_SAFE_DRAFT_OPEN = "this platform lacks dir_fd and O_NOFOLLOW, so the handoff cannot run"


class GlobalOptionBodyTest(unittest.TestCase):
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
        self.outside = self.root / "outside.txt"
        self.outside.write_bytes(b"outside\n")
        self.calls = []
        self.inputs = []

    def run_wrapper(self, argv: list) -> tuple[int, str]:
        """Run main() with `run` arguments and return the code and stderr."""
        response = subprocess.CompletedProcess(
            [], 0, json.dumps({"html_url": "https://github.com/x/y/1"}), "")

        def record(_repo_root, arguments, **keywords):
            self.calls.append(list(arguments))
            self.inputs.append(keywords.get("input_text"))
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

    def assert_refused(self, argv: list) -> None:
        """Assert one command exits 2 and starts no gh process."""
        self.calls.clear()
        code, stderr = self.run_wrapper(argv)
        self.assertEqual(code, USAGE_EXIT_CODE, stderr)
        self.assertEqual(self.calls, [])

    def test_leading_repo_relative_refused(self):
        for prefix in (["-R", REPOSITORY], ["--repo", REPOSITORY]):
            with self.subTest(prefix=prefix):
                self.assert_refused([*prefix, "issue", "create", "--title", "T",
                                     "--body-file", DRAFT_ARGUMENT, "--web"])

    def test_leading_repo_outside_refused(self):
        self.assert_refused(["-R", REPOSITORY, "pr", "edit", "7",
                             "--body-file", str(self.outside), "--add-reviewer", "someone"])

    @unittest.skipUnless(SAFE_DRAFT_OPEN, NO_SAFE_DRAFT_OPEN)
    def test_leading_repo_draft_stdin(self):
        code, stderr = self.run_wrapper(["-R", REPOSITORY, "issue", "create", "--title", "T",
                                         "--body-file", str(self.draft), "--web"])
        self.assertEqual(code, 0, stderr)
        self.assertEqual(self.inputs, [DRAFT_TEXT])
        self.assertNotIn(str(self.draft), " ".join(self.calls[0]))


if __name__ == "__main__":
    unittest.main()
