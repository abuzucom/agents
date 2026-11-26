#!/usr/bin/env python3
"""A draft with a second link, or a platform without a safe open, fails closed.

A hard link inside `.comment-drafts/` can name a file that lives elsewhere.
Every draft read refuses a file with more than one link. A platform without
`dir_fd` and `O_NOFOLLOW` cannot hand a draft to gh safely, so an absolute
draft exits 2 there. A body on stdin still works on every platform.
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
SAFE_DRAFT_OPEN = trusted_gh._safe_draft_open_supported()
NO_SAFE_DRAFT_OPEN = "this platform lacks dir_fd and O_NOFOLLOW, so draft reads refuse"


class DraftHarness(unittest.TestCase):
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

    def assert_refused(self, argv: list) -> None:
        """Assert one command exits 2 and starts no gh process."""
        self.calls.clear()
        code, stderr = self.run_wrapper(argv)
        self.assertEqual(code, USAGE_EXIT_CODE, stderr)
        self.assertIn("error:", stderr)
        self.assertEqual(self.calls, [])


@unittest.skipUnless(SAFE_DRAFT_OPEN, NO_SAFE_DRAFT_OPEN)
class HardLinkDraftTest(DraftHarness):
    """A draft that shares its inode with another path is refused."""

    def setUp(self):
        super().setUp()
        self.outside = self.root / "outside.txt"
        self.outside.write_bytes(b"outside\n")
        self.link = self.drafts / "linked.md"
        os.link(self.outside, self.link)

    def test_linked_absolute_draft_refused(self):
        self.assert_refused(["issue", "create", "--title", "T",
                             "--body-file", str(self.link), "--web"])

    def test_linked_rest_draft_refused(self):
        self.assert_refused(["issue", "create", "--title", "T",
                             "--body-file", ".comment-drafts/linked.md"])

    def test_single_link_draft_accepted(self):
        code, stderr = self.run_wrapper(["issue", "create", "--title", "T",
                                         "--body-file", str(self.draft), "--web"])
        self.assertEqual(code, 0, stderr)


class UnsafePlatformDraftTest(DraftHarness):
    """Without dir_fd and O_NOFOLLOW, an absolute draft exits 2."""

    def run_unsafe(self, argv: list) -> tuple[int, str]:
        """Run the wrapper as a platform without a safe draft open."""
        with patch.object(trusted_gh, "_safe_draft_open_supported", return_value=False):
            return self.run_wrapper(argv)

    def test_absolute_draft_refused_unsafe(self):
        for body in (["--body-file", str(self.draft)], [f"-F{self.draft}"]):
            with self.subTest(body=body):
                self.calls.clear()
                code, stderr = self.run_unsafe(["issue", "create", "--title", "T", *body, "--web"])
                self.assertEqual(code, USAGE_EXIT_CODE, stderr)
                self.assertIn("O_NOFOLLOW", stderr)
                self.assertEqual(self.calls, [])

    def test_stdin_body_works_unsafe(self):
        code, stderr = self.run_unsafe(["issue", "create", "--title", "T",
                                        "--body-file", "-", "--web"])
        self.assertEqual(code, 0, stderr)
        self.assertEqual(len(self.calls), 1)


if __name__ == "__main__":
    unittest.main()
