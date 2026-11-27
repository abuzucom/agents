#!/usr/bin/env python3
"""A protected gate change without an approval timeline fails closed (#194)."""
import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_gate_pr_integrity as integrity

SHA_HEX_LENGTH = 40
PROTECTED_PATH = "hooks/x.py"


def run_main(paths: list, labels: list) -> tuple:
    """Run the checker without --timeline-json and return (exit code, stderr)."""
    stderr = io.StringIO()
    with patch.object(integrity, "_has_revision", return_value=True), \
            patch.object(integrity, "_changed_paths", return_value=paths), \
            contextlib.redirect_stderr(stderr):
        code = integrity.main([
            "--base", "a" * SHA_HEX_LENGTH, "--head", "b" * SHA_HEX_LENGTH,
            "--pr-number", "1", "--labels-json", json.dumps(labels),
        ])
    return code, stderr.getvalue()


class MissingTimelineTest(unittest.TestCase):
    """A label alone cannot approve a protected change."""

    def test_protected_label_without_timeline_fails(self) -> None:
        code, output = run_main([PROTECTED_PATH], [integrity.APPROVAL_LABEL])
        self.assertEqual(code, 1)
        self.assertIn(integrity.MISSING_TIMELINE_MESSAGE, output)

    def test_unprotected_change_needs_no_timeline(self) -> None:
        code, _ = run_main(["README.md"], [])
        self.assertEqual(code, 0)

    def test_missing_label_reported_first(self) -> None:
        code, output = run_main([PROTECTED_PATH], [])
        self.assertEqual(code, 1)
        self.assertIn(f"require the {integrity.APPROVAL_LABEL} label", output)

    def test_failure_helper_names_timeline(self) -> None:
        reason = integrity._approval_failure([PROTECTED_PATH], [integrity.APPROVAL_LABEL], None)
        self.assertEqual(reason, integrity.MISSING_TIMELINE_MESSAGE)


if __name__ == "__main__":
    unittest.main()
