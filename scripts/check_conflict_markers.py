#!/usr/bin/env python3
"""Check tracked files for unresolved git merge conflict markers.

A portable, path-generic checker: copy this file into any repo and run
it in CI, pre-commit hooks, or Makefile targets. Scans files for unresolved
git merge conflict blocks and orphan markers across standard and configured
marker sizes. Inspects Git index modes to ignore symlinks and submodules,
supports UTF-16/32 encodings and BOMs, enforces read bounds, and allows
Markdown Setext headings only under valid heading context.

Modes:
  check_conflict_markers.py <file> ...   Check explicitly provided files
  check_conflict_markers.py --all        Check all git-tracked regular files
  check_conflict_markers.py              Default: check all git-tracked regular files

Exits 1 on any violation or read/git error (fail-closed), 0 if clean.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_LINE_LENGTH = 65536  # 64 KB
MAX_VIOLATIONS = 100

MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkdn", ".mdx"}
CODE_FENCE_PATTERN = re.compile(r"^(`{3,}|~{3,})")

DEFAULT_OPENER = re.compile(r"^(<{7,})(?: (.*))?$")
DEFAULT_DIFF3 = re.compile(r"^(\|{7,})(?: (.*))?$")
DEFAULT_SEPARATOR = re.compile(r"^={7,}$")
DEFAULT_CLOSER = re.compile(r"^(>{7,})(?: (.*))?$")

# Also catch balanced smaller markers down to width 3 if not configured
SHORT_OPENER = re.compile(r"^(<{3,6})(?: (.*))?$")
SHORT_DIFF3 = re.compile(r"^(\|{3,6})(?: (.*))?$")
SHORT_SEPARATOR = re.compile(r"^={3,6}$")
SHORT_CLOSER = re.compile(r"^(>{3,6})(?: (.*))?$")

ORPHAN_SEPARATOR_PATTERN = re.compile(r"^={3,}$")


def is_markdown_file(path: str) -> bool:
    """Return True if path has a Markdown extension."""
    return Path(path).suffix.lower() in MARKDOWN_EXTENSIONS


def is_valid_setext_heading(lines: list[str], index: int) -> bool:
    """Return True if a line of = is an underline for a preceding heading line in Markdown."""
    if index == 0:
        return False
    prev_line = lines[index - 1].strip()
    if not prev_line:
        return False
    if CODE_FENCE_PATTERN.match(prev_line):
        return False
    if prev_line.startswith(("#", "<", ">", "|", "=")):
        return False
    return True


def decode_content(raw_bytes: bytes, encoding_hint: str | None = None) -> tuple[str | None, str | None]:
    """Decode raw bytes into text using BOM, git attribute encoding, or utf-8/latin-1.

    Returns (text, error_message). text is None if file is binary.
    """
    if len(raw_bytes) > MAX_FILE_SIZE:
        return None, f"file size ({len(raw_bytes)} bytes) exceeds limit ({MAX_FILE_SIZE} bytes)"

    # Check BOMs first
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        return raw_bytes.decode("utf-8-sig", errors="replace").lstrip("\ufeff"), None
    if raw_bytes.startswith(b"\xff\xfe\x00\x00") or raw_bytes.startswith(b"\x00\x00\xfe\xff"):
        return raw_bytes.decode("utf-32", errors="replace").lstrip("\ufeff"), None
    if raw_bytes.startswith(b"\xff\xfe") or raw_bytes.startswith(b"\xfe\xff"):
        return raw_bytes.decode("utf-16", errors="replace").lstrip("\ufeff"), None

    if encoding_hint and encoding_hint != "unspecified":
        try:
            return raw_bytes.decode(encoding_hint, errors="replace").lstrip("\ufeff"), None
        except (LookupError, UnicodeDecodeError):
            pass

    # Standard UTF-8 check
    try:
        text = raw_bytes.decode("utf-8").lstrip("\ufeff")
        return text, None
    except UnicodeDecodeError:
        pass

    # Check if binary (null bytes in first 4096 bytes without UTF-16/32 BOM)
    if b"\x00" in raw_bytes[:4096]:
        return None, None

    # Fall back to latin-1
    return raw_bytes.decode("latin-1"), None


def check_content(text: str, path: str, configured_marker_size: int | None = None) -> list[str]:
    """Scan text content for unresolved conflict blocks and orphan markers."""
    violations = []
    lines = text.splitlines()

    open_marker_line = None
    open_marker_len = 0

    if configured_marker_size is not None and configured_marker_size >= 2:
        exact_opener = re.compile(rf"^(<{{{configured_marker_size}}})(?: (.*))?$")
        exact_diff3 = re.compile(rf"^(\|{{{configured_marker_size}}})(?: (.*))?$")
        exact_separator = re.compile(rf"^={{{configured_marker_size}}}$")
        exact_closer = re.compile(rf"^(>{{{configured_marker_size}}})(?: (.*))?$")
    else:
        exact_opener = exact_diff3 = exact_separator = exact_closer = None

    markdown = is_markdown_file(path)

    for number, line in enumerate(lines, 1):
        if len(violations) >= MAX_VIOLATIONS:
            violations.append(f"{path}: reached maximum violation limit ({MAX_VIOLATIONS}), stopping scan")
            break

        if len(line) > MAX_LINE_LENGTH:
            line = line[:MAX_LINE_LENGTH]

        if exact_opener:
            opener_match = exact_opener.match(line)
            diff3_match = exact_diff3.match(line)
            separator_match = exact_separator.match(line)
            closer_match = exact_closer.match(line)
        else:
            opener_match = DEFAULT_OPENER.match(line) or SHORT_OPENER.match(line)
            diff3_match = DEFAULT_DIFF3.match(line) or SHORT_DIFF3.match(line)
            separator_match = DEFAULT_SEPARATOR.match(line) or SHORT_SEPARATOR.match(line)
            closer_match = DEFAULT_CLOSER.match(line) or SHORT_CLOSER.match(line)

        if opener_match:
            marker_len = len(opener_match.group(1))
            if open_marker_line is not None:
                violations.append(f"{path}:{open_marker_line}: unclosed conflict marker opener")
            open_marker_line = number
            open_marker_len = marker_len
        elif closer_match:
            marker_len = len(closer_match.group(1))
            if open_marker_line is not None and (exact_closer or marker_len == open_marker_len):
                violations.append(f"{path}:{open_marker_line}-{number}: unresolved conflict block")
                open_marker_line = None
                open_marker_len = 0
            elif open_marker_line is not None:
                violations.append(f"{path}:{open_marker_line}: unclosed conflict marker opener")
                violations.append(f"{path}:{number}: mismatched conflict marker closer '{line}'")
                open_marker_line = None
                open_marker_len = 0
            else:
                violations.append(f"{path}:{number}: orphan conflict marker closer '{line}'")
        elif diff3_match:
            if open_marker_line is None:
                violations.append(f"{path}:{number}: orphan conflict marker separator '{line}'")
        elif separator_match or ORPHAN_SEPARATOR_PATTERN.match(line):
            if open_marker_line is not None:
                # Inside open conflict block, separator is part of the block
                pass
            else:
                # Outside open conflict block: allowed only in Markdown if valid Setext heading
                if markdown and is_valid_setext_heading(lines, number - 1):
                    pass
                else:
                    violations.append(f"{path}:{number}: orphan conflict marker separator '{line}'")

    if open_marker_line is not None:
        violations.append(f"{path}:{open_marker_line}: unclosed conflict marker opener")

    return violations


def get_git_attributes(paths: list[str]) -> dict[str, dict[str, str]]:
    """Query git attributes for conflict-marker-size and working-tree-encoding."""
    if not paths:
        return {}

    attributes = {}
    chunk_size = 500
    for i in range(0, len(paths), chunk_size):
        chunk = paths[i:i + chunk_size]
        cmd = ["git", "--no-pager", "-c", "core.fsmonitor=", "check-attr", "conflict-marker-size", "working-tree-encoding", "-z", "--"] + chunk
        proc = subprocess.run(cmd, capture_output=True, check=False)
        if proc.returncode != 0:
            continue
        raw = proc.stdout
        parts = raw.split(b"\x00")
        # Format: path, attr, value triplets
        for j in range(0, len(parts) - 2, 3):
            file_path = parts[j].decode("utf-8", errors="replace")
            attr_name = parts[j + 1].decode("utf-8", errors="replace")
            attr_value = parts[j + 2].decode("utf-8", errors="replace")
            if file_path not in attributes:
                attributes[file_path] = {}
            attributes[file_path][attr_name] = attr_value

    return attributes


def check_file(path: str, configured_size: int | None = None, encoding_hint: str | None = None) -> list[str]:
    """Check a single file for conflict markers, rejecting symlinks and respecting read limits."""
    # Never follow symlinks on disk
    if os.path.islink(path):
        return []

    file_path = Path(path)
    if not file_path.exists():
        return [f"error: file not found: {path}"]
    if file_path.is_dir():
        return []

    try:
        stat_result = os.stat(path, follow_symlinks=False)
        if stat_result.st_size > MAX_FILE_SIZE:
            return [f"error: {path}: file size ({stat_result.st_size} bytes) exceeds limit ({MAX_FILE_SIZE} bytes)"]
        raw_bytes = file_path.read_bytes()
    except OSError as error:
        return [f"error: could not read {path}: {error}"]

    text, err = decode_content(raw_bytes, encoding_hint)
    if err:
        return [f"error: {path}: {err}"]
    if text is None:
        # Binary file
        return []

    return check_content(text, path, configured_size)


def get_tracked_regular_files() -> list[str]:
    """Return all git-tracked regular files (excluding symlinks and submodules) from the index."""
    result = subprocess.run(
        ["git", "--no-pager", "-c", "core.fsmonitor=", "ls-files", "-s", "-z"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        error_msg = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git ls-files failed (exit {result.returncode}): {error_msg}")

    raw = result.stdout
    if not raw:
        return []

    regular_files = []
    parts = raw.split(b"\x00")
    for part in parts:
        if not part:
            continue
        try:
            entry_str = part.decode("utf-8", errors="replace")
            meta, file_path = entry_str.split("\t", 1)
            mode = meta.split(" ", 1)[0]
            # 100644 (regular), 100755 (executable regular). Skip 120000 (symlink), 160000 (submodule).
            if mode in ("100644", "100755"):
                regular_files.append(file_path)
        except ValueError:
            continue

    return regular_files


def main() -> int:
    args = sys.argv[1:]
    files = []

    if not args or args == ["--all"]:
        try:
            files = get_tracked_regular_files()
        except RuntimeError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
    else:
        for arg in args:
            if arg == "--all":
                try:
                    files.extend(get_tracked_regular_files())
                except RuntimeError as error:
                    print(f"error: {error}", file=sys.stderr)
                    return 1
            else:
                files.append(arg)

    attributes = get_git_attributes(files)

    violations = []
    for path in files:
        file_attrs = attributes.get(path, {})
        size_str = file_attrs.get("conflict-marker-size")
        try:
            conf_size = int(size_str) if size_str and size_str.isdigit() else None
        except ValueError:
            conf_size = None
        encoding = file_attrs.get("working-tree-encoding")

        violations.extend(check_file(path, conf_size, encoding))

    if violations:
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
