#!/usr/bin/env python3
"""Behavioral tests for scripts/check_merge_safety.py (Pre-Merge Gating)."""
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_merge_safety as checker  # noqa: E402


class CheckMergeSafetyTest(unittest.TestCase):
    """Ensure strict preconditions gate any proposed merge action."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / ".git").mkdir(parents=True, exist_ok=True)
        self.addCleanup(self.temp_dir.cleanup)

    def test_missing_or_empty_target_ref_fails(self):
        code, errors = checker.verify_merge_safety("", repo_root=self.root)
        self.assertNotEqual(code, 0)
        self.assertTrue(any("target reference is empty" in err for err in errors))

    def test_self_merge_detected_as_contradictory_and_fails(self):
        with patch.object(checker, "_current_branch_name", return_value="fix/test-branch"):
            code, errors = checker.verify_merge_safety("fix/test-branch", repo_root=self.root)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("cannot merge branch into itself" in err for err in errors))

    def test_rebase_in_progress_fails(self):
        (self.root / ".git" / "rebase-merge").mkdir(parents=True, exist_ok=True)
        code, errors = checker.verify_merge_safety("origin/main", repo_root=self.root)
        self.assertNotEqual(code, 0)
        self.assertTrue(any("rebase is active" in err for err in errors))

    def test_merge_already_in_progress_fails(self):
        (self.root / ".git" / "MERGE_HEAD").write_text("abc123\n", encoding="utf-8")
        code, errors = checker.verify_merge_safety("origin/main", repo_root=self.root)
        self.assertNotEqual(code, 0)
        self.assertTrue(any("merge is already in progress" in err for err in errors))

    def test_conflict_markers_in_tree_fails(self):
        conflict_file = self.root / "shared-files.json"
        conflict_file.write_text("<<<<<<< HEAD\nfoo\n=======\nbar\n>>>>>>> origin/main\n", encoding="utf-8")
        code, errors = checker.verify_merge_safety("origin/main", repo_root=self.root)
        self.assertNotEqual(code, 0)
        self.assertTrue(any("conflict marker detected" in err for err in errors))

    def test_dirty_worktree_fails(self):
        with patch.object(checker, "_is_worktree_clean", return_value=(False, "M tracked_file.py")):
            code, errors = checker.verify_merge_safety("origin/main", repo_root=self.root)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("worktree is not clean" in err for err in errors))

    def test_invalid_current_branch_fails(self):
        with patch.object(checker, "_current_branch_name", return_value="main"), \
             patch.object(checker, "_is_worktree_clean", return_value=(True, "")):
            code, errors = checker.verify_merge_safety("origin/main", repo_root=self.root)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("invalid current branch" in err for err in errors))

    def test_gate_adoption_failure_blocks_merge(self):
        with patch.object(checker, "_current_branch_name", return_value="fix/test-branch"), \
             patch.object(checker, "_is_worktree_clean", return_value=(True, "")), \
             patch.object(checker, "_check_gate_adoption_status", return_value=(False, "gate adoption incomplete")):
            code, errors = checker.verify_merge_safety("origin/main", repo_root=self.root)
            self.assertNotEqual(code, 0)
            self.assertTrue(any("gate adoption incomplete" in err for err in errors))

    def test_all_preconditions_met_passes(self):
        with patch.object(checker, "_current_branch_name", return_value="fix/test-branch"), \
             patch.object(checker, "_is_worktree_clean", return_value=(True, "")), \
             patch.object(checker, "_check_gate_adoption_status", return_value=(True, "")), \
             patch.object(checker, "_check_sync_status", return_value=(True, "")):
            code, errors = checker.verify_merge_safety("origin/main", repo_root=self.root)
            self.assertEqual(code, 0)
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
