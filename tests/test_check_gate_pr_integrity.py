#!/usr/bin/env python3
"""Test trusted base-ref checks for protected gate changes."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_gate_pr_integrity as integrity


class ProtectedPathTest(unittest.TestCase):
    """Protected paths require out-of-band human approval."""

    def test_hook_change_requires_approval(self) -> None:
        self.assertTrue(integrity.requires_approval(["hooks/_gate_core.py"]))

    def test_client_configuration_requires_approval(self) -> None:
        self.assertTrue(integrity.requires_approval([".codex/hooks.json"]))

    def test_documentation_only_change_does_not_require_approval(self) -> None:
        self.assertFalse(integrity.requires_approval(["README.md"]))

    def test_approval_label_matches_exact_value(self) -> None:
        self.assertTrue(integrity.has_approval_label([integrity.APPROVAL_LABEL]))
        self.assertFalse(integrity.has_approval_label(["gate-change-approved-now"]))

    def test_existing_head_skips_trusted_fetch(self) -> None:
        with patch.object(integrity, "_has_revision", return_value=True):
            with patch.object(integrity, "_fetch_head") as fetch_head:
                with patch.object(integrity, "_changed_paths", return_value=[]):
                    result = integrity.main([
                        "--base", "a" * 40,
                        "--head", "b" * 40,
                        "--pr-number", "1",
                        "--labels-json", "[]",
                    ])
        self.assertEqual(result, 0)
        fetch_head.assert_not_called()


if __name__ == "__main__":
    unittest.main()
