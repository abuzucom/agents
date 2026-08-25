#!/usr/bin/env python3
"""Tests for scripts/check_conflict_markers.py and its CI/Makefile wiring."""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKER_PATH = REPO_ROOT / "scripts" / "check_conflict_markers.py"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "sync-check.yml"
MAKEFILE_PATH = REPO_ROOT / "Makefile"


def _load_checker_module():
    spec = importlib.util.spec_from_file_location("check_conflict_markers", CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load_checker_module()


class ConflictMarkerDetectionTest(unittest.TestCase):
    """Test detection across marker formats, sizes, and false-positive cases."""

    def test_clean_file_has_no_violations(self):
        content = "def hello():\n    return 'world'\n"
        violations = checker.check_content(content, "clean.py")
        self.assertEqual(violations, [])

    def test_standard_7char_conflict_block(self):
        content = "<<<<<<< HEAD\nleft\n=======\nright\n>>>>>>> branch\n"
        violations = checker.check_content(content, "foo.py")
        self.assertEqual(len(violations), 1)
        self.assertIn("foo.py:1-5: unresolved conflict block", violations[0])

    def test_diff3_conflict_block(self):
        content = "<<<<<<< HEAD\nleft\n||||||| base\nancestor\n=======\nright\n>>>>>>> branch\n"
        violations = checker.check_content(content, "foo.py")
        self.assertEqual(len(violations), 1)
        self.assertIn("foo.py:1-7: unresolved conflict block", violations[0])

    def test_configurable_marker_size_detected(self):
        content = "<<<<<<<<<< HEAD\nleft\n==========\nright\n>>>>>>>>>> branch\n"
        violations = checker.check_content(content, "large_marker.py")
        self.assertEqual(len(violations), 1)
        self.assertIn("large_marker.py:1-5: unresolved conflict block", violations[0])

    def test_unclosed_opener_flagged(self):
        content = "prefix\n<<<<<<< HEAD\nleft\nsome code\n"
        violations = checker.check_content(content, "unclosed.py")
        self.assertEqual(len(violations), 1)
        self.assertIn("unclosed.py:2: unclosed conflict marker opener", violations[0])

    def test_orphan_closer_flagged(self):
        content = "prefix\n>>>>>>> origin/main\nsuffix\n"
        violations = checker.check_content(content, "orphan.py")
        self.assertEqual(len(violations), 1)
        self.assertIn("orphan.py:2: orphan conflict marker closer", violations[0])

    def test_orphan_diff3_separator_flagged(self):
        content = "prefix\n||||||| merged common ancestors\nsuffix\n"
        violations = checker.check_content(content, "orphan_diff3.py")
        self.assertEqual(len(violations), 1)
        self.assertIn("orphan_diff3.py:2: orphan conflict marker separator", violations[0])

    def test_setext_markdown_heading_is_not_flagged(self):
        content = "# Markdown Doc\n\nSection Title\n=============\n\nBody text.\n"
        violations = checker.check_content(content, "doc.md")
        self.assertEqual(violations, [])

    def test_consecutive_openers_flag_previous(self):
        content = "<<<<<<< HEAD\nleft\n<<<<<<< OTHER\nother\n=======\nright\n>>>>>>> branch\n"
        violations = checker.check_content(content, "nested.py")
        self.assertEqual(len(violations), 2)
        self.assertIn("nested.py:1: unclosed conflict marker opener", violations[0])
        self.assertIn("nested.py:3-7: unresolved conflict block", violations[1])


class FileCheckingTest(unittest.TestCase):
    """Test filesystem interactions and fail-closed error handling."""

    def test_nonexistent_file_fails_closed(self):
        violations = checker.check_file("nonexistent_file_path_12345.txt")
        self.assertEqual(len(violations), 1)
        self.assertIn("error: file not found", violations[0])

    def test_binary_file_is_skipped(self):
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp.write(b"PNG\x00\x01\x02\x03<<<<<<< HEAD\x00")
            temp_path = Path(temp.name)
        try:
            violations = checker.check_file(str(temp_path))
            self.assertEqual(violations, [])
        finally:
            temp_path.unlink()

    def test_temp_file_with_conflict_is_detected(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as temp:
            temp.write("<<<<<<< HEAD\na\n=======\nb\n>>>>>>> branch\n")
            temp_path = Path(temp.name)
        try:
            violations = checker.check_file(str(temp_path))
            self.assertEqual(len(violations), 1)
        finally:
            temp_path.unlink()


class GitTrackedFilesTest(unittest.TestCase):
    """Test git-tracked files enumeration."""

    def test_get_tracked_files_includes_repo_files(self):
        files = checker.get_tracked_files()
        self.assertIn("AGENTS.md", files)
        self.assertIn("README.md", files)
        self.assertIn("scripts/check_conflict_markers.py", files)


class CliExecutionTest(unittest.TestCase):
    """Test running check_conflict_markers.py as a CLI subprocess."""

    def test_cli_on_current_repo_exits_zero(self):
        proc = subprocess.run(
            [sys.executable, str(CHECKER_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, f"stdout: {proc.stdout}, stderr: {proc.stderr}")

    def test_cli_with_conflict_file_exits_one(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as temp:
            temp.write("<<<<<<< HEAD\na\n=======\nb\n>>>>>>> branch\n")
            temp_path = Path(temp.name)
        try:
            proc = subprocess.run(
                [sys.executable, str(CHECKER_PATH), str(temp_path)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)
            self.assertIn("unresolved conflict block", proc.stderr)
        finally:
            temp_path.unlink()


PRE_COMMIT_CONFIG_PATH = REPO_ROOT / ".pre-commit-config.yaml"


class WiringTest(unittest.TestCase):
    """Test that CI workflow, Makefile, and pre-commit invoke check_conflict_markers.py."""

    def test_sync_check_workflow_wires_conflict_checker(self):
        content = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("check_conflict_markers.py", content)

    def test_makefile_wires_conflict_checker(self):
        content = MAKEFILE_PATH.read_text(encoding="utf-8")
        self.assertIn("check_conflict_markers.py", content)

    def test_pre_commit_config_wires_conflict_checker(self):
        content = PRE_COMMIT_CONFIG_PATH.read_text(encoding="utf-8")
        self.assertIn("check_conflict_markers.py", content)


if __name__ == "__main__":
    unittest.main()
