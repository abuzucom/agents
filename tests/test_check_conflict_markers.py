#!/usr/bin/env python3
"""Tests for scripts/check_conflict_markers.py and its wiring."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKER_PATH = REPO_ROOT / "scripts" / "check_conflict_markers.py"
WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "sync-check.yml"
)
MAKEFILE_PATH = REPO_ROOT / "Makefile"
PRE_COMMIT_CONFIG_PATH = REPO_ROOT / ".pre-commit-config.yaml"


def _load_checker_module():
    spec = importlib.util.spec_from_file_location(
        "check_conflict_markers", CHECKER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load_checker_module()


class ConflictMarkerDetectionTest(unittest.TestCase):
    """Detection across marker formats, sizes, and edge cases."""

    def test_clean_file_has_no_violations(self):
        content = "def hello():\n    return 'world'\n"
        violations = checker.check_content(content, "clean.py")
        self.assertEqual(violations, [])

    def test_standard_7char_conflict_block(self):
        content = (
            "<<<<<<< HEAD\nleft\n=======\n"
            "right\n>>>>>>> branch\n"
        )
        violations = checker.check_content(content, "foo.py")
        self.assertEqual(len(violations), 1)
        self.assertIn(
            "foo.py:1-5: unresolved conflict block",
            violations[0],
        )

    def test_diff3_conflict_block(self):
        content = (
            "<<<<<<< HEAD\nleft\n||||||| base\n"
            "ancestor\n=======\nright\n>>>>>>> branch\n"
        )
        violations = checker.check_content(content, "foo.py")
        self.assertEqual(len(violations), 1)
        self.assertIn(
            "foo.py:1-7: unresolved conflict block",
            violations[0],
        )

    def test_size_1_conflict_block_detected(self):
        """Genuine size-1 balanced conflict block is detected."""
        content = "< HEAD\nleft\n=\nright\n> branch\n"
        violations = checker.check_content(content, "test.py")
        self.assertEqual(len(violations), 1)
        self.assertIn(
            "test.py:1-5: unresolved conflict block",
            violations[0],
        )

    def test_size_1_with_configured_size_1_detected(self):
        content = "< HEAD\nleft\n=\nright\n> branch\n"
        violations = checker.check_content(
            content, "test.py", configured_marker_size=1
        )
        self.assertEqual(len(violations), 1)
        self.assertIn(
            "test.py:1-5: unresolved conflict block",
            violations[0],
        )

    def test_size_2_conflict_block_detected(self):
        """Genuine size-2 balanced conflict block is detected."""
        content = "<< HEAD\nleft\n==\nright\n>> branch\n"
        violations = checker.check_content(content, "test.py")
        self.assertEqual(len(violations), 1)
        self.assertIn(
            "test.py:1-5: unresolved conflict block",
            violations[0],
        )

    def test_size_2_detected_with_different_configured_size(self):
        """Size-2 block detected even when configured size is 10."""
        content = "<< HEAD\nleft\n==\nright\n>> branch\n"
        violations = checker.check_content(
            content, "test.py", configured_marker_size=10
        )
        self.assertEqual(len(violations), 1)
        self.assertIn(
            "test.py:1-5: unresolved conflict block",
            violations[0],
        )

    def test_configurable_marker_size_detected_exact(self):
        content = "<<< HEAD\nleft\n===\nright\n>>> branch\n"
        violations = checker.check_content(
            content, "custom.py", configured_marker_size=3
        )
        self.assertEqual(len(violations), 1)
        self.assertIn(
            "custom.py:1-5: unresolved conflict block",
            violations[0],
        )

    def test_configurable_large_marker_size_detected(self):
        content = (
            "<<<<<<<<<< HEAD\nleft\n"
            "==========\nright\n>>>>>>>>>> branch\n"
        )
        violations = checker.check_content(
            content, "large.py", configured_marker_size=10
        )
        self.assertEqual(len(violations), 1)
        self.assertIn(
            "large.py:1-5: unresolved conflict block",
            violations[0],
        )

    def test_configured_size_10_still_catches_7char_conflict(self):
        """Generic patterns fire even when configured size is 10."""
        content = (
            "<<<<<<< HEAD\nleft\n=======\n"
            "right\n>>>>>>> branch\n"
        )
        violations = checker.check_content(
            content, "test.py", configured_marker_size=10
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("unresolved conflict block", violations[0])

    def test_configured_size_10_catches_7char_in_markdown(self):
        """Seven-char conflict in Markdown detected despite size=10."""
        content = (
            "<<<<<<< HEAD\nleft\n=======\n"
            "right\n>>>>>>> branch\n"
        )
        violations = checker.check_content(
            content, "test.md", configured_marker_size=10
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("unresolved conflict block", violations[0])

    def test_unclosed_opener_flagged(self):
        content = "prefix\n<<<<<<< HEAD\nleft\nsome code\n"
        violations = checker.check_content(
            content, "unclosed.py"
        )
        self.assertEqual(len(violations), 1)
        self.assertIn(
            "unclosed.py:2: unclosed conflict marker opener",
            violations[0],
        )

    def test_orphan_closer_flagged(self):
        content = "prefix\n>>>>>>> origin/main\nsuffix\n"
        violations = checker.check_content(
            content, "orphan.py"
        )
        self.assertEqual(len(violations), 1)
        self.assertIn(
            "orphan.py:2: orphan conflict marker closer",
            violations[0],
        )

    def test_orphan_diff3_separator_flagged(self):
        content = (
            "prefix\n||||||| merged common ancestors\nsuffix\n"
        )
        violations = checker.check_content(
            content, "orphan_diff3.py"
        )
        self.assertEqual(len(violations), 1)
        self.assertIn(
            "orphan_diff3.py:2: orphan conflict marker separator",
            violations[0],
        )

    def test_orphan_separator_in_python_is_flagged(self):
        content = "def foo():\n    x = 1\n=======\n    return x\n"
        violations = checker.check_content(
            content, "script.py"
        )
        self.assertEqual(len(violations), 1)
        self.assertIn(
            "script.py:3: orphan conflict marker separator",
            violations[0],
        )

    def test_orphan_separator_in_yaml_is_flagged(self):
        content = "key: value\n=======\nother: value\n"
        violations = checker.check_content(
            content, "config.yml"
        )
        self.assertEqual(len(violations), 1)
        self.assertIn(
            "config.yml:2: orphan conflict marker separator",
            violations[0],
        )

    def test_setext_markdown_heading_is_not_flagged(self):
        content = (
            "# Markdown Doc\n\nSection Title\n"
            "=============\n\nBody text.\n"
        )
        violations = checker.check_content(content, "doc.md")
        self.assertEqual(violations, [])

    def test_orphan_separator_in_md_without_heading_flagged(self):
        content = "\n=======\nSome text\n"
        violations = checker.check_content(content, "doc.md")
        self.assertEqual(len(violations), 1)
        self.assertIn(
            "doc.md:2: orphan conflict marker separator",
            violations[0],
        )

    def test_consecutive_openers_flag_previous(self):
        content = (
            "<<<<<<< HEAD\nleft\n<<<<<<< OTHER\n"
            "other\n=======\nright\n>>>>>>> branch\n"
        )
        violations = checker.check_content(
            content, "nested.py"
        )
        self.assertEqual(len(violations), 2)
        self.assertIn(
            "nested.py:1: unclosed conflict marker opener",
            violations[0],
        )
        self.assertIn(
            "nested.py:3-7: unresolved conflict block",
            violations[1],
        )


class FileCheckingTest(unittest.TestCase):
    """Filesystem interactions, encodings, and fail-closed errors."""

    def test_nonexistent_file_fails_closed(self):
        violations = checker.check_file(
            "nonexistent_file_path_12345.txt"
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("error:", violations[0])
        self.assertIn("file not found", violations[0])

    def test_binary_file_is_skipped(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"PNG\x00\x01\x02\x03<<<<<<< HEAD\x00")
            tmp_path = Path(tmp.name)
        try:
            violations = checker.check_file(str(tmp_path))
            self.assertEqual(violations, [])
        finally:
            tmp_path.unlink()

    def test_utf16le_file_with_bom_detected(self):
        text = (
            "<<<<<<< HEAD\nleft\n=======\n"
            "right\n>>>>>>> branch\n"
        )
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"\xff\xfe" + text.encode("utf-16-le"))
            tmp_path = Path(tmp.name)
        try:
            violations = checker.check_file(str(tmp_path))
            self.assertEqual(len(violations), 1)
            self.assertIn(
                "unresolved conflict block", violations[0]
            )
        finally:
            tmp_path.unlink()

    def test_utf16be_file_with_bom_detected(self):
        text = (
            "<<<<<<< HEAD\nleft\n=======\n"
            "right\n>>>>>>> branch\n"
        )
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"\xfe\xff" + text.encode("utf-16-be"))
            tmp_path = Path(tmp.name)
        try:
            violations = checker.check_file(str(tmp_path))
            self.assertEqual(len(violations), 1)
            self.assertIn(
                "unresolved conflict block", violations[0]
            )
        finally:
            tmp_path.unlink()

    def test_utf16_encoding_hint_without_bom_detected(self):
        text = (
            "<<<<<<< HEAD\nleft\n=======\n"
            "right\n>>>>>>> branch\n"
        )
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(text.encode("utf-16-le"))
            tmp_path = Path(tmp.name)
        try:
            violations = checker.check_file(
                str(tmp_path), encoding_hint="UTF-16LE"
            )
            self.assertEqual(len(violations), 1)
            self.assertIn(
                "unresolved conflict block", violations[0]
            )
        finally:
            tmp_path.unlink()

    def test_symlink_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "target.txt"
            target.write_text(
                "<<<<<<< HEAD\na\n=======\n"
                "b\n>>>>>>> main\n",
                encoding="utf-8",
            )
            link = Path(tmp_dir) / "link.txt"
            try:
                os.symlink(target, link)
                violations = checker.check_file(str(link))
                self.assertEqual(violations, [])
            except (OSError, NotImplementedError):
                pass  # symlinks may need privileges on Windows

    def test_safe_read_regular_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"hello world")
            tmp_path = tmp.name
        try:
            data, err = checker._safe_read(tmp_path, 1024)
            self.assertIsNone(err)
            self.assertEqual(data, b"hello world")
        finally:
            os.unlink(tmp_path)

    def test_safe_read_nonexistent(self):
        data, err = checker._safe_read(
            "no_such_file_xyz.tmp", 1024
        )
        self.assertIsNone(data)
        self.assertIn("file not found", err)

    def test_safe_read_symlink_skipped(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "target.txt"
            target.write_text("content", encoding="utf-8")
            link = Path(tmp_dir) / "link.txt"
            try:
                os.symlink(target, link)
                data, err = checker._safe_read(str(link), 1024)
                self.assertIsNone(data)
                self.assertIsNone(err)
            except (OSError, NotImplementedError):
                pass  # symlinks may need privileges on Windows

    def test_get_git_attributes_raises_on_git_failure(self):
        """get_git_attributes fails closed on non-zero git exit."""
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 128
            mock_proc.stderr = b"fatal: git check-attr error"
            mock_run.return_value = mock_proc
            with self.assertRaises(RuntimeError) as ctx:
                checker.get_git_attributes(["foo.py"])
            self.assertIn("git check-attr failed", str(ctx.exception))

    def test_staged_utf16_working_tree_encoding_not_applied(self):
        """Staged blob in index is decoded as UTF-8 without working-tree-encoding."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_path = Path(tmp_dir)
            # Simulate index entry with conflict text in UTF-8
            sha = "fake_sha_1234"
            with patch.object(checker, "_get_index_entries") as mock_entries, \
                 patch.object(checker, "get_git_attributes") as mock_attrs, \
                 patch.object(checker, "_get_blob_size") as mock_size, \
                 patch.object(checker, "_read_blob") as mock_blob:
                mock_entries.return_value = [
                    ("test.txt", sha, "0", "100644")
                ]
                mock_attrs.return_value = {
                    "test.txt": {"working-tree-encoding": "UTF-16LE"}
                }
                mock_size.return_value = 50
                mock_blob.return_value = (
                    b"<<<<<<< HEAD\nleft\n=======\n"
                    b"right\n>>>>>>> branch\n"
                )
                violations = checker._check_staged(str(repo_path))
                self.assertEqual(len(violations), 1)
                self.assertIn("unresolved conflict block", violations[0])

    def test_staged_oversized_blob_rejected_without_buffering(self):
        """Blobs exceeding MAX_FILE_SIZE are rejected via size check."""
        with patch.object(checker, "_get_index_entries") as mock_entries, \
             patch.object(checker, "get_git_attributes") as mock_attrs, \
             patch.object(checker, "_get_blob_size") as mock_size, \
             patch.object(checker, "_read_blob") as mock_blob:
            mock_entries.return_value = [
                ("huge.bin", "fake_sha_huge", "0", "100644")
            ]
            mock_attrs.return_value = {}
            mock_size.return_value = checker.MAX_FILE_SIZE + 100
            violations = checker._check_staged(".")
            self.assertEqual(len(violations), 1)
            self.assertIn("blob size", violations[0])
            self.assertIn("exceeds limit", violations[0])
            # _read_blob must never have been called
            mock_blob.assert_not_called()


class GitTrackedFilesTest(unittest.TestCase):
    """Git-tracked regular files enumeration."""

    def test_get_tracked_regular_files_includes_repo_files(self):
        files = checker.get_tracked_regular_files()
        self.assertIn("AGENTS.md", files)
        self.assertIn("README.md", files)
        self.assertIn(
            "scripts/check_conflict_markers.py", files
        )


class CliExecutionTest(unittest.TestCase):
    """CLI subprocess execution."""

    def test_cli_on_current_repo_exits_zero(self):
        proc = subprocess.run(
            [sys.executable, str(CHECKER_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            proc.returncode, 0,
            f"stdout: {proc.stdout}, stderr: {proc.stderr}",
        )

    def test_cli_with_conflict_file_exits_one(self):
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(
                "<<<<<<< HEAD\na\n=======\n"
                "b\n>>>>>>> branch\n"
            )
            tmp_path = Path(tmp.name)
        try:
            proc = subprocess.run(
                [sys.executable, str(CHECKER_PATH), str(tmp_path)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)
            self.assertIn(
                "unresolved conflict block", proc.stderr
            )
        finally:
            tmp_path.unlink()

    def test_cli_from_subdirectory_exits_zero(self):
        """Repo root is resolved; all tracked files are checked."""
        proc = subprocess.run(
            [sys.executable, str(CHECKER_PATH)],
            cwd=REPO_ROOT / "scripts",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            proc.returncode, 0,
            f"stdout: {proc.stdout}, stderr: {proc.stderr}",
        )

    def test_staged_flag_exits_zero_on_clean_repo(self):
        proc = subprocess.run(
            [sys.executable, str(CHECKER_PATH), "--staged"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            proc.returncode, 0,
            f"stdout: {proc.stdout}, stderr: {proc.stderr}",
        )


class WiringTest(unittest.TestCase):
    """Exact wiring across CI, Makefile, and pre-commit config."""

    def test_sync_check_workflow_wires_exact_command(self):
        content = WORKFLOW_PATH.read_text(encoding="utf-8")
        expected = (
            "- name: Check for unresolved conflict markers\n"
            "        run: python scripts/"
            "check_conflict_markers.py"
        )
        self.assertIn(expected, content)

    def test_makefile_wires_exact_lint_recipe(self):
        content = MAKEFILE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "\tpython scripts/check_conflict_markers.py",
            content,
        )

    def test_pre_commit_config_wires_staged_hook(self):
        content = PRE_COMMIT_CONFIG_PATH.read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "- id: check-conflict-markers", content
        )
        self.assertIn(
            "entry: python scripts/"
            "check_conflict_markers.py --staged",
            content,
        )
        self.assertIn("always_run: true", content)
        self.assertIn("pass_filenames: false", content)


if __name__ == "__main__":
    unittest.main()
