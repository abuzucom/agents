#!/usr/bin/env python3
"""Relative draft refusal holds for repeated body options and any option order.

gh keeps the last value of a repeated scalar option. gh also accepts the
issue or pull request number after its flags. Neither shape may carry a
relative body path to raw gh.
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


class BodyOptionOrderTest(unittest.TestCase):
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

    def assert_refused(self, argv: list) -> None:
        """Assert one command exits 2 and starts no gh process."""
        self.calls.clear()
        code, stderr = self.run_wrapper(argv)
        self.assertEqual(code, USAGE_EXIT_CODE, stderr)
        self.assertIn("error:", stderr)
        self.assertEqual(self.calls, [])

    def test_later_relative_body_refused(self):
        for command in (["issue", "create", "--title", "T"], ["issue", "edit", "5"],
                        ["pr", "edit", "7"]):
            with self.subTest(command=command):
                self.assert_refused([*command, "--body-file", self.absolute,
                                     "--body-file", DRAFT_ARGUMENT])

    def test_later_short_body_refused(self):
        self.assert_refused(["issue", "edit", "5", "--body-file", self.absolute,
                             "-F", DRAFT_ARGUMENT])

    def test_trailing_edit_number_refused(self):
        for command in (["issue", "edit"], ["pr", "edit"]):
            with self.subTest(command=command):
                self.assert_refused([*command, "--body-file", DRAFT_ARGUMENT, "--web", "5"])
                self.assert_refused([*command, "--body-file", DRAFT_ARGUMENT, "5"])

    def test_trailing_number_message_names_order(self):
        _code, stderr = self.run_wrapper(["issue", "edit", "--body-file", DRAFT_ARGUMENT, "5"])
        self.assertIn("the number must follow the edit subcommand", stderr)


if __name__ == "__main__":
    unittest.main()
