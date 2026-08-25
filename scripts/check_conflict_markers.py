#!/usr/bin/env python3
"""Check tracked files for unresolved git merge conflict markers.

A portable, path-generic checker: copy this file into any repo and run
it in CI, pre-commit hooks, or Makefile targets. Scans files for unresolved
git merge conflict blocks and orphan markers across arbitrary marker sizes
(size >= 7). Differentiates genuine conflict blocks from standalone Markdown
Setext headers (`=======`).

Modes:
  check_conflict_markers.py <file> ...   Check explicitly provided files
  check_conflict_markers.py --all        Check all git-tracked files
  check_conflict_markers.py              Default: check all git-tracked files

Exits 1 on any violation or read/git error (fail-closed), 0 if clean.
"""
import re
import subprocess
import sys
from pathlib import Path

OPENER_PATTERN = re.compile(r"^(<{7,})(?: (.*))?$")
DIFF3_PATTERN = re.compile(r"^(\|{7,})(?: (.*))?$")
SEPARATOR_PATTERN = re.compile(r"^={7,}$")
CLOSER_PATTERN = re.compile(r"^(>{7,})(?: (.*))?$")


def is_binary_string(data: bytes) -> bool:
    """Return True if bytes contain null byte or non-text indicators."""
    return b"\x00" in data[:4096]


def check_content(text: str, path: str) -> list[str]:
    """Scan content for unresolved conflict blocks and orphan markers."""
    violations = []
    lines = text.splitlines()

    open_marker_line = None
    open_marker_len = 0

    for number, line in enumerate(lines, 1):
        opener_match = OPENER_PATTERN.match(line)
        diff3_match = DIFF3_PATTERN.match(line)
        separator_match = SEPARATOR_PATTERN.match(line)
        closer_match = CLOSER_PATTERN.match(line)

        if opener_match:
            marker_len = len(opener_match.group(1))
            if open_marker_line is not None:
                violations.append(
                    f"{path}:{open_marker_line}: unclosed conflict marker opener"
                )
            open_marker_line = number
            open_marker_len = marker_len
        elif closer_match:
            marker_len = len(closer_match.group(1))
            if open_marker_line is not None:
                violations.append(
                    f"{path}:{open_marker_line}-{number}: unresolved conflict block"
                )
                open_marker_line = None
                open_marker_len = 0
            else:
                violations.append(
                    f"{path}:{number}: orphan conflict marker closer '{line}'"
                )
        elif diff3_match:
            if open_marker_line is None:
                violations.append(
                    f"{path}:{number}: orphan conflict marker separator '{line}'"
                )
        elif separator_match:
            # Standalone ======= outside an open conflict block is valid Setext heading
            pass

    if open_marker_line is not None:
        violations.append(
            f"{path}:{open_marker_line}: unclosed conflict marker opener"
        )

    return violations


def check_file(path: str) -> list[str]:
    """Check a single file for conflict markers, failing closed on read error."""
    file_path = Path(path)
    if not file_path.exists():
        return [f"error: file not found: {path}"]
    if file_path.is_dir():
        return []

    try:
        raw_bytes = file_path.read_bytes()
    except OSError as error:
        return [f"error: could not read {path}: {error}"]

    if is_binary_string(raw_bytes):
        return []

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw_bytes.decode("latin-1")
        except UnicodeDecodeError as error:
            return [f"error: could not decode {path}: {error}"]

    return check_content(text, path)


def get_tracked_files() -> list[str]:
    """Return all git-tracked files using array-based subprocess execution."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        error_msg = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git ls-files failed (exit {result.returncode}): {error_msg}")

    raw = result.stdout
    if not raw:
        return []
    parts = raw.split(b"\x00")
    files = []
    for part in parts:
        if part:
            files.append(part.decode("utf-8", errors="replace"))
    return files


def main() -> int:
    args = sys.argv[1:]
    files = []

    if not args or args == ["--all"]:
        try:
            files = get_tracked_files()
        except RuntimeError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
    else:
        for arg in args:
            if arg == "--all":
                try:
                    files.extend(get_tracked_files())
                except RuntimeError as error:
                    print(f"error: {error}", file=sys.stderr)
                    return 1
            else:
                files.append(arg)

    violations = []
    for path in files:
        violations.extend(check_file(path))

    if violations:
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
