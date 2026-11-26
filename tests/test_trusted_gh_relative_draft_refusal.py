#!/usr/bin/env python3
"""A relative draft body that falls out of the REST mapping fails closed.

Raw gh runs from a private temporary directory outside the repository. A
relative `--body-file` path cannot resolve there. The wrapper refuses that
shape with exit 2 and starts no gh process.
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
PULL_CREATE = ["pr", "create", "--draft", "--title", "T", "--body-file", DRAFT_ARGUMENT]
ISSUE_CREATE = ["issue", "create", "--title", "T", "--body-file", DRAFT_ARGUMENT]


def completed(stdout: str = "", returncode: int = 0):
    """Return a fixed GitHub CLI result."""
    return subprocess.CompletedProcess([], returncode, stdout, "")


class RelativeDraftHarness(unittest.TestCase):
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
        (drafts / "body.md").write_bytes(DRAFT_TEXT.encode("ascii"))
        self.calls = []

    def run_wrapper(self, argv: list) -> tuple[int, str]:
        """Run main() with `run` arguments and return the code and stderr."""
        response = completed(stdout=json.dumps({"html_url": "https://github.com/x/y/1"}))

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

    def assert_refused_naming(self, argv: list, named: str) -> None:
        """Assert one command exits 2, names a token, and starts no gh process."""
        self.calls.clear()
        code, stderr = self.run_wrapper(argv)
        self.assertEqual(code, USAGE_EXIT_CODE, stderr)
        self.assertIn("error:", stderr)
        self.assertIn(named, stderr)
        self.assertIn(trusted_gh.COMMENT_DRAFT_DIRECTORY, stderr)
        self.assertEqual(self.calls, [])


class RelativeDraftRefusalTest(RelativeDraftHarness):
    """Every REST write shape with a relative body and an extra option exits 2."""

    def test_issue_create_repo_refused(self):
        self.assert_refused_naming([*ISSUE_CREATE, "--repo", REPOSITORY], "--repo")

    def test_issue_create_extras_refused(self):
        for option, value in (("--assignee", "someone"), ("--milestone", "v1"),
                              ("-R", REPOSITORY)):
            with self.subTest(option=option):
                self.assert_refused_naming([*ISSUE_CREATE, option, value], option)

    def test_issue_edit_extras_refused(self):
        for extra in (["--repo", REPOSITORY], ["--add-assignee", "someone"],
                      ["--remove-milestone"], ["--body", "inline"]):
            with self.subTest(extra=extra):
                self.assert_refused_naming(
                    ["issue", "edit", "5", "--body-file", DRAFT_ARGUMENT, *extra], extra[0])

    def test_pull_create_extras_refused(self):
        for extra in (["--web"], ["--reviewer", "someone"], ["--head", "other"]):
            with self.subTest(extra=extra):
                self.assert_refused_naming([*PULL_CREATE, *extra], extra[0])

    def test_pull_edit_extras_refused(self):
        for extra in (["--add-reviewer", "someone"], ["--milestone", "v1"]):
            with self.subTest(extra=extra):
                self.assert_refused_naming(
                    ["pr", "edit", "7", "--body-file", DRAFT_ARGUMENT, *extra], extra[0])

    def test_missing_required_option_refused(self):
        self.assert_refused_naming(["issue", "create", "--body-file", DRAFT_ARGUMENT], "--title")
        self.assert_refused_naming(
            ["pr", "create", "--title", "T", "--body-file", DRAFT_ARGUMENT], "--draft")

    def test_short_and_inline_body_refused(self):
        self.assert_refused_naming(
            ["issue", "create", "--title", "T", "-F", DRAFT_ARGUMENT, "--web"], "-F")
        self.assert_refused_naming(
            ["issue", "create", "--title", "T", f"--body-file={DRAFT_ARGUMENT}"],
            "--body-file=")


class NonRelativeBodyPassthroughTest(RelativeDraftHarness):
    """Shapes that raw gh can still serve reach gh unchanged."""

    def assert_passthrough(self, argv: list) -> None:
        """Assert one command reaches gh as written."""
        self.calls.clear()
        code, stderr = self.run_wrapper(argv)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn("api", self.calls[0])

    def test_stdin_body_passthrough(self):
        self.assert_passthrough(["issue", "create", "--title", "T", "--body-file", "-", "--web"])

    def test_absolute_body_passthrough(self):
        absolute = str(self.root / DRAFT_ARGUMENT)
        self.assert_passthrough(["issue", "create", "--title", "T", "--body-file", absolute,
                                 "--assignee", "someone"])

    def test_bodyless_edit_passthrough(self):
        self.assert_passthrough(["pr", "edit", "7", "--title", "New title"])


if __name__ == "__main__":
    unittest.main()
