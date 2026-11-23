#!/usr/bin/env python3
"""Test that gate adoption requires every skill and client copy."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import _skill_sync
import check_gate_adoption

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


class SkillRequirementTest(unittest.TestCase):
    """The adoption checker and the sync list name the same skills."""

    def test_skill_tuples_match(self):
        self.assertEqual(check_gate_adoption.REQUIRED_SKILLS, _skill_sync.SKILLS)

    def test_required_files_list_skills(self):
        required = set(check_gate_adoption.required_skill_files())
        for name in _skill_sync.SKILLS:
            with self.subTest(skill=name):
                self.assertIn(_skill_sync.canonical_path(name), required)
                for relative in _skill_sync.copy_paths(name):
                    self.assertIn(relative, required)

    def test_missing_copy_reported(self):
        name = _skill_sync.SKILLS[0]
        absent = _skill_sync.copy_paths(name)[1]
        findings = check_gate_adoption.check_skill_files(
            REPOSITORY_ROOT, present=lambda relative: relative != absent)
        self.assertTrue(any(absent in finding for finding in findings), findings)

    def test_live_tree_reports_nothing(self):
        self.assertEqual(check_gate_adoption.check_skill_files(REPOSITORY_ROOT), [])


if __name__ == "__main__":
    unittest.main()
