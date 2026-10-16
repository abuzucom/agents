#!/usr/bin/env python3
"""Enforce strict preconditions before any proposed git merge action."""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
ALLOWED_BRANCH_PREFIXES = ("feat/", "fix/", "chore/", "docs/", "test/")
IGNORED_DIRECTORIES = frozenset({".git", ".gate-staging", "__pycache__", ".pytest_cache"})
MAX_SCAN_BYTES = 512 * 1024


def _current_branch_name(root: Path) -> str:
    """Read branch name from Git administration metadata."""
    head_path = root / ".git" / "HEAD"
    if not head_path.is_file():
        return ""
    try:
        content = head_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    prefix = "ref: refs/heads/"
    if content.startswith(prefix):
        return content[len(prefix):]
    return "HEAD" if content else ""


def _is_rebase_active(root: Path) -> bool:
    """Return True if a git rebase is currently in progress."""
    git_dir = root / ".git"
    return (git_dir / "rebase-merge").is_dir() or (git_dir / "rebase-apply").is_dir()


def _is_merge_active(root: Path) -> bool:
    """Return True if an unresolved git merge is currently in progress."""
    return (root / ".git" / "MERGE_HEAD").is_file()


def _file_has_conflict_markers(path: Path) -> bool:
    """Return True if the file contains git conflict markers."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                stripped = line.strip()
                if any(stripped.startswith(marker) for marker in CONFLICT_MARKERS):
                    return True
    except OSError:
        return False
    return False


def _scan_for_conflict_markers(root: Path) -> List[str]:
    """Scan files in repository for unresolved conflict markers."""
    conflicts: List[str] = []
    for current_dir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES]
        for name in files:
            path = Path(current_dir) / name
            try:
                if path.stat().st_size > MAX_SCAN_BYTES:
                    continue
            except OSError:
                continue
            if _file_has_conflict_markers(path):
                conflicts.append(str(path.relative_to(root)))
    return conflicts


def _is_worktree_clean(root: Path) -> Tuple[bool, str]:
    """Check whether git worktree has uncommitted modifications."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, f"git status failed: {error}"
    output = result.stdout.strip()
    return (output == "", output)


def _check_branch_validity(branch: str) -> Tuple[bool, str]:
    """Verify branch naming convention under Rule 18."""
    if not branch or branch in ("HEAD", "main", "master"):
        return False, f"invalid current branch: {branch}"
    if branch.startswith("claude/"):
        return False, f"prohibited agent branch prefix: {branch}"
    if not any(branch.startswith(prefix) for prefix in ALLOWED_BRANCH_PREFIXES):
        return False, f"invalid current branch prefix: {branch}"
    return True, ""


def _check_gate_adoption_status(root: Path) -> Tuple[bool, str]:
    """Verify complete gate adoption status across all adopted clients."""
    script_path = root / "scripts" / "check_gate_adoption.py"
    if not script_path.is_file():
        return False, "check_gate_adoption.py is missing"
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--root", str(root)],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, f"gate adoption check execution failed: {error}"
    if result.returncode != 0:
        return False, result.stderr.strip() or "gate adoption check failed"
    return True, ""


def _check_sync_status(root: Path) -> Tuple[bool, str]:
    """Verify policy synchronization status."""
    script_path = root / "scripts" / "sync.py"
    if not script_path.is_file():
        return False, "sync.py is missing"
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--check"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, f"policy sync check execution failed: {error}"
    if result.returncode != 0:
        return False, result.stderr.strip() or "policy synchronization check failed"
    return True, ""


def _check_operation_preconditions(root: Path) -> List[str]:
    """Check active git operation state preconditions."""
    errors: List[str] = []
    if _is_rebase_active(root):
        errors.append("rebase is active in worktree")
    if _is_merge_active(root):
        errors.append("merge is already in progress in worktree")
    return errors


def verify_merge_safety(
    target_ref: str,
    repo_root: Optional[Path] = None,
    run_tests: bool = False,
) -> Tuple[int, List[str]]:
    """Validate all safety preconditions before executing any merge."""
    root = repo_root or Path.cwd()
    errors: List[str] = []

    target = target_ref.strip()
    if not target:
        errors.append("target reference is empty")
        return 1, errors

    branch = _current_branch_name(root)
    if branch and target == branch:
        errors.append(f"cannot merge branch into itself: {target}")
        return 1, errors

    op_errors = _check_operation_preconditions(root)
    if op_errors:
        return 1, op_errors

    conflicts = _scan_for_conflict_markers(root)
    if conflicts:
        errors.append(f"conflict marker detected in: {', '.join(conflicts)}")
        return 1, errors

    clean, status_output = _is_worktree_clean(root)
    if not clean:
        errors.append(f"worktree is not clean: {status_output}")
        return 1, errors

    valid_branch, branch_err = _check_branch_validity(branch)
    if not valid_branch:
        errors.append(branch_err)
        return 1, errors

    gate_ok, gate_err = _check_gate_adoption_status(root)
    if not gate_ok:
        errors.append(gate_err)
        return 1, errors

    sync_ok, sync_err = _check_sync_status(root)
    if not sync_ok:
        errors.append(sync_err)
        return 1, errors

    return 0, []


def main(argv: Optional[List[str]] = None) -> int:
    """Run CLI interface for merge safety verification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="Target branch or reference to merge")
    parser.add_argument("--root", default=".", help="Repository root path")
    parser.add_argument("--run-tests", action="store_true", help="Execute full test suite before merge")
    args = parser.parse_args(argv)

    code, errors = verify_merge_safety(args.target, Path(args.root), run_tests=args.run_tests)
    if code != 0:
        for err in errors:
            print(f"Pre-merge safety check failed: {err}", file=sys.stderr)
        return code
    print(f"Pre-merge safety check passed for target: {args.target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
