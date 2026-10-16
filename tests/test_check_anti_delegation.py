#!/usr/bin/env python3
"""Behavioral tests for scripts/check_anti_delegation.py (Rule 18 and Anti-Delegation)."""
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_anti_delegation as checker  # noqa: E402


class CheckAntiDelegationTest(unittest.TestCase):
    """Detect and block delegating recovery commands or manual actions to humans."""

    def test_delegating_powershell_command_detected(self):
        cases = (
            "Please run this command in powershell: git merge --abort",
            "Run git merge --abort in PowerShell to fix the tree.",
            "Execute the following command in terminal: git reset --hard",
            "You should run git checkout -b fix/branch in bash.",
        )
        for case in cases:
            with self.subTest(case=case):
                findings = checker.scan_text_for_delegation(case)
                self.assertTrue(findings, f"Failed to detect delegation: {case}")
                self.assertEqual(findings[0].category, "command_delegation")

    def test_delegating_git_recovery_detected(self):
        cases = (
            "Please run git merge --abort to resolve the conflict.",
            "Run git rebase --abort.",
            "Execute git switch -c fix/my-branch.",
            "Execute `git branch -m fix/compliant-branch`.",
        )
        for case in cases:
            with self.subTest(case=case):
                findings = checker.scan_text_for_delegation(case)
                self.assertTrue(findings, f"Failed to detect git delegation: {case}")
                self.assertEqual(findings[0].category, "git_recovery_delegation")

    def test_delegating_manual_recovery_detected(self):
        cases = (
            "Perform manual recovery on the corrupted repository.",
            "The user must manually recover the git state.",
            "Delegate the recovery action to the human.",
            "Ask the user to run recovery manually.",
        )
        for case in cases:
            with self.subTest(case=case):
                findings = checker.scan_text_for_delegation(case)
                self.assertTrue(findings, f"Failed to detect manual recovery: {case}")
                self.assertEqual(findings[0].category, "manual_recovery_delegation")

    def test_benign_text_and_policy_statements_pass(self):
        benign_cases = (
            "Never ask the user to run recovery commands.",
            "Do not delegate recovery commands to the human.",
            "Policy prohibits delegating recovery actions to humans.",
            "# The agent must run git merge --abort directly if authorized.",
            "Strict branch preflight passed on branch fix/compaction-transcript-bug.",
            "The script executes git commands autonomously after consent.",
        )
        for case in benign_cases:
            with self.subTest(case=case):
                findings = checker.scan_text_for_delegation(case)
                self.assertEqual(findings, [], f"False positive for benign text: {case}")

    def test_cli_file_scan_with_findings_returns_exit_1(self):
        sample_file = REPO_ROOT / "tests" / "fixtures" / "delegation_sample.txt"
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            sample_file.write_text(
                "Please run git merge --abort in PowerShell to clear the conflict.\n",
                encoding="utf-8",
            )
            exit_code = checker.main([str(sample_file)])
            self.assertEqual(exit_code, 1)
        finally:
            if sample_file.exists():
                sample_file.unlink()

    def test_cli_clean_file_returns_exit_0(self):
        sample_file = REPO_ROOT / "tests" / "fixtures" / "clean_sample.txt"
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            sample_file.write_text(
                "Policy forbids delegating commands to humans.\nStrict branch preflight passed.\n",
                encoding="utf-8",
            )
            exit_code = checker.main([str(sample_file)])
            self.assertEqual(exit_code, 0)
        finally:
            if sample_file.exists():
                sample_file.unlink()


if __name__ == "__main__":
    unittest.main()
