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
  check_conflict_markers.py --staged     Check staged index blobs (pre-commit)
  check_conflict_markers.py              Default: --all

Exits 1 on any violation or read/git error (fail-closed), 0 if clean.
"""
import errno
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_LINE_LENGTH = 65536  # 64 KB
MAX_VIOLATIONS = 100
MAX_DIAGNOSTIC_LENGTH = 200


def _sanitize(value: object) -> str:
    """Render untrusted text as printable ASCII on one line.

    An allowlist, not a strip. Zero-width characters, bidi overrides, and
    Unicode tag characters are not control characters, and they render
    invisibly or reverse the text around them, so a denylist of known-bad
    codepoints misses the cases that matter. Paths and file content reach
    CI logs and terminals, where a newline forges a log line and an escape
    sequence rewrites the screen.
    """
    rendered = []
    for character in str(value):
        if " " <= character <= "~":
            rendered.append(character)
        elif ord(character) <= 0xFF:
            rendered.append(f"\\x{ord(character):02x}")
        else:
            rendered.append(f"\\u{ord(character):04x}")
    text = "".join(rendered)
    if len(text) > MAX_DIAGNOSTIC_LENGTH:
        return text[:MAX_DIAGNOSTIC_LENGTH] + "...[truncated]"
    return text

MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkdn", ".mdx"}
CODE_FENCE_PATTERN = re.compile(r"^(`{3,}|~{3,})")

OPENER_PATTERN = re.compile(r"^(<+)(?: (.*))?$")
DIFF3_PATTERN = re.compile(r"^(\|+) *(?: (.*))?$")
SEPARATOR_PATTERN = re.compile(r"^(=+)$")
CLOSER_PATTERN = re.compile(r"^(>+)(?: (.*))?$")


def is_markdown_file(path: str) -> bool:
    """Return True if path has a Markdown extension."""
    return Path(path).suffix.lower() in MARKDOWN_EXTENSIONS


def is_valid_setext_heading(
    lines: list[str], index: int
) -> bool:
    """Return True if an = line underlines a preceding heading."""
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


def decode_content(
    raw_bytes: bytes, encoding_hint: str | None = None
) -> tuple[str | None, str | None]:
    """Decode raw bytes to text via BOM, attribute encoding, or utf-8.

    Returns (text, error_message). text is None if file is binary.
    """
    if len(raw_bytes) > MAX_FILE_SIZE:
        return None, (
            f"size ({len(raw_bytes)} bytes) exceeds "
            f"limit ({MAX_FILE_SIZE} bytes)"
        )

    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        decoded = raw_bytes.decode("utf-8-sig", errors="replace")
        return decoded.lstrip("\ufeff"), None
    if raw_bytes.startswith(
        (b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")
    ):
        decoded = raw_bytes.decode("utf-32", errors="replace")
        return decoded.lstrip("\ufeff"), None
    if raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
        decoded = raw_bytes.decode("utf-16", errors="replace")
        return decoded.lstrip("\ufeff"), None

    if encoding_hint and encoding_hint != "unspecified":
        try:
            decoded = raw_bytes.decode(
                encoding_hint, errors="replace"
            )
            return decoded.lstrip("\ufeff"), None
        except (LookupError, UnicodeDecodeError):
            pass

    try:
        return raw_bytes.decode("utf-8").lstrip("\ufeff"), None
    except UnicodeDecodeError:
        pass

    if b"\x00" in raw_bytes[:4096]:
        return None, None

    return raw_bytes.decode("latin-1"), None


def check_content(
    text: str,
    path: str,
    configured_marker_size: int | None = None,
) -> list[str]:
    """Scan text for conflict blocks and orphan markers.

    Parses balanced conflict blocks for any positive marker width (N >= 1).
    Flags unclosed openers, mismatched closers, and orphan markers for
    width >= 3 or matching configured_marker_size. Allows Setext headings
    in Markdown only when preceded by valid heading text.
    """
    safe_path = _sanitize(path)
    violations: list[str] = []
    lines = text.splitlines()
    open_marker_line: int | None = None
    open_marker_len = 0
    has_separator = False
    markdown = is_markdown_file(path)

    for number, line in enumerate(lines, 1):
        if len(violations) >= MAX_VIOLATIONS:
            violations.append(
                f"{safe_path}: reached violation limit "
                f"({MAX_VIOLATIONS}), stopping"
            )
            break

        if len(line) > MAX_LINE_LENGTH:
            line = line[:MAX_LINE_LENGTH]

        opener_match = OPENER_PATTERN.match(line)
        closer_match = CLOSER_PATTERN.match(line)
        diff3_match = DIFF3_PATTERN.match(line)
        separator_match = SEPARATOR_PATTERN.match(line)

        if opener_match:
            marker_len = len(opener_match.group(1))
            if open_marker_line is not None:
                if (
                    open_marker_len >= 3
                    or (
                        configured_marker_size is not None
                        and open_marker_len == configured_marker_size
                    )
                ):
                    violations.append(
                        f"{safe_path}:{open_marker_line}: "
                        "unclosed conflict marker opener"
                    )
            open_marker_line = number
            open_marker_len = marker_len
            has_separator = False
        elif closer_match:
            marker_len = len(closer_match.group(1))
            if open_marker_line is not None and marker_len == open_marker_len and has_separator:
                violations.append(
                    f"{safe_path}:{open_marker_line}-{number}: "
                    "unresolved conflict block"
                )
                open_marker_line = None
                open_marker_len = 0
                has_separator = False
            elif open_marker_line is not None:
                if (
                    open_marker_len >= 3
                    or (
                        configured_marker_size is not None
                        and open_marker_len == configured_marker_size
                    )
                ):
                    violations.append(
                        f"{safe_path}:{open_marker_line}: "
                        "unclosed conflict marker opener"
                    )
                if (
                    marker_len >= 3
                    or (
                        configured_marker_size is not None
                        and marker_len == configured_marker_size
                    )
                ):
                    violations.append(
                        f"{safe_path}:{number}: "
                        f"mismatched conflict marker closer '{_sanitize(line)}'"
                    )
                open_marker_line = None
                open_marker_len = 0
                has_separator = False
            else:
                if (
                    marker_len >= 3
                    or (
                        configured_marker_size is not None
                        and marker_len == configured_marker_size
                    )
                ):
                    violations.append(
                        f"{safe_path}:{number}: "
                        f"orphan conflict marker closer '{_sanitize(line)}'"
                    )
        elif diff3_match:
            marker_len = len(diff3_match.group(1))
            if open_marker_line is None:
                if (
                    marker_len >= 3
                    or (
                        configured_marker_size is not None
                        and marker_len == configured_marker_size
                    )
                ):
                    violations.append(
                        f"{safe_path}:{number}: "
                        f"orphan conflict marker separator '{_sanitize(line)}'"
                    )
            elif marker_len == open_marker_len:
                has_separator = True
        elif separator_match:
            marker_len = len(separator_match.group(1))
            if open_marker_line is not None:
                if marker_len == open_marker_len:
                    has_separator = True
            elif markdown and is_valid_setext_heading(lines, number - 1):
                pass  # valid Setext heading underline
            elif (
                marker_len >= 3
                or (
                    configured_marker_size is not None
                    and marker_len == configured_marker_size
                )
            ):
                violations.append(
                    f"{safe_path}:{number}: "
                    f"orphan conflict marker separator '{_sanitize(line)}'"
                )

    if open_marker_line is not None:
        if (
            open_marker_len >= 3
            or (
                configured_marker_size is not None
                and open_marker_len == configured_marker_size
            )
        ):
            violations.append(
                f"{safe_path}:{open_marker_line}: "
                "unclosed conflict marker opener"
            )

    return violations


def _get_repo_root() -> str:
    """Resolve the git repository root directory."""
    result = subprocess.run(
        ["git", "--no-pager", "rev-parse", "--show-toplevel"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        error_msg = result.stderr.decode(
            "utf-8", errors="replace"
        ).strip()
        raise RuntimeError(
            f"git rev-parse --show-toplevel failed: {error_msg}"
        )
    return result.stdout.decode("utf-8", errors="replace").strip()


def _probe_is_symlink(path: str):
    """Return True, False, or None when the check itself failed."""
    try:
        return os.path.islink(path)
    except OSError:
        return None


def _safe_read(
    path: str, max_size: int
) -> tuple[bytes | None, str | None]:
    """Open once without following links, verify regular, read bounded.

    Returns (data, error_message). data is None on skip or error.
    error_message is None when the file is silently skipped.
    """
    flags = os.O_RDONLY
    nofollow = hasattr(os, "O_NOFOLLOW")
    if nofollow:
        flags |= os.O_NOFOLLOW
    else:
        # Without O_NOFOLLOW the check and the open are separate calls, so
        # this narrows the window rather than closing it. A probe that
        # fails tells us nothing about the path, so refuse it.
        is_link = _probe_is_symlink(path)
        if is_link is None:
            return None, f"could not determine whether {_sanitize(path)} is a link"
        if is_link:
            return None, None

    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        return None, f"file not found: {path}"
    except IsADirectoryError:
        return None, None
    except OSError as err:
        if nofollow and err.errno == errno.ELOOP:
            return None, None  # symlink with O_NOFOLLOW
        return None, f"could not open {path}: {err}"
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return None, None
        if st.st_size > max_size:
            return None, (
                f"{path}: file size ({st.st_size} bytes) "
                f"exceeds limit ({max_size} bytes)"
            )
        data = bytearray()
        while True:
            chunk = os.read(fd, max_size + 1 - len(data))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > max_size:
                return None, (
                    f"{path}: read exceeded limit ({max_size} bytes)"
                )
        return bytes(data), None
    finally:
        os.close(fd)


def _parse_marker_size(
    size_str: str | None,
) -> int | None:
    """Parse a conflict-marker-size attribute value."""
    if not size_str or size_str in ("unspecified", "unset"):
        return None
    try:
        return int(size_str)
    except ValueError:
        return None


def get_git_attributes(
    paths: list[str],
    repo_root: str | None = None,
    cached: bool = False,
) -> dict[str, dict[str, str]]:
    """Query git attributes for marker size and encoding."""
    if not paths:
        return {}

    attributes: dict[str, dict[str, str]] = {}
    repo_paths: list[tuple[str, str]] = []

    if repo_root:
        norm_root = os.path.abspath(repo_root)
        for p in paths:
            abs_p = os.path.abspath(p) if os.path.isabs(p) else os.path.abspath(os.path.join(norm_root, p))
            try:
                if os.path.commonpath([norm_root, abs_p]) == norm_root:
                    rel_p = os.path.relpath(abs_p, norm_root)
                    # git addresses paths with forward slashes on every
                    # platform, so a Windows relpath loses every lookup.
                    rel_p = rel_p.replace(os.sep, "/")
                    if os.altsep:
                        rel_p = rel_p.replace(os.altsep, "/")
                    repo_paths.append((p, rel_p))
            except ValueError:
                pass
    else:
        repo_paths = [(p, p) for p in paths]

    if not repo_paths:
        return attributes

    chunk_size = 500
    for i in range(0, len(repo_paths), chunk_size):
        chunk = repo_paths[i : i + chunk_size]
        rel_chunk = [rel for _, rel in chunk]
        cmd = [
            "git", "--no-pager",
            "-c", "core.fsmonitor=",
            "check-attr",
            "conflict-marker-size",
            "working-tree-encoding",
            "-z", "--stdin",
        ]
        if cached:
            cmd.append("--cached")
        kwargs: dict = {
            "capture_output": True,
            "check": False,
            "input": b"\x00".join(p.encode("utf-8") for p in rel_chunk) + b"\x00"
        }
        if repo_root:
            kwargs["cwd"] = repo_root
        proc = subprocess.run(cmd, **kwargs)
        if proc.returncode != 0:
            error_msg = proc.stderr.decode(
                "utf-8", errors="replace"
            ).strip()
            raise RuntimeError(
                f"git check-attr failed (exit {proc.returncode}): "
                f"{error_msg}"
            )
        raw = proc.stdout
        parts = raw.split(b"\x00")
        raw_attrs: dict[str, dict[str, str]] = {}
        for j in range(0, len(parts) - 2, 3):
            fp = parts[j].decode("utf-8", errors="replace")
            attr = parts[j + 1].decode("utf-8", errors="replace")
            val = parts[j + 2].decode("utf-8", errors="replace")
            if fp not in raw_attrs:
                raw_attrs[fp] = {}
            raw_attrs[fp][attr] = val

        for orig_p, rel_p in chunk:
            attrs = raw_attrs.get(
                rel_p, raw_attrs.get(orig_p, {})
            )
            attributes[orig_p] = attrs
            attributes[rel_p] = attrs

    return attributes


def check_file(
    path: str,
    configured_size: int | None = None,
    encoding_hint: str | None = None,
) -> list[str]:
    """Check a single worktree file for conflict markers.

    Uses _safe_read for race-free, bounded, no-follow-symlink I/O.
    """
    raw_bytes, err = _safe_read(path, MAX_FILE_SIZE)
    if err:
        return [f"error: {_sanitize(err)}"]
    if raw_bytes is None:
        return []

    text, decode_err = decode_content(raw_bytes, encoding_hint)
    if decode_err:
        return [f"error: {path}: {decode_err}"]
    if text is None:
        return []

    return check_content(text, path, configured_size)


def get_tracked_regular_files(
    repo_root: str | None = None,
) -> list[str]:
    """Return git-tracked regular files from the index.

    Excludes symlinks (120000) and submodules (160000). Uses
    --full-name so paths are always relative to the repo root.
    """
    if repo_root is None:
        repo_root = _get_repo_root()
    cmd = [
        "git", "--no-pager",
        "-c", "core.fsmonitor=",
        "ls-files", "-s", "-z", "--full-name",
    ]
    result = subprocess.run(
        cmd, capture_output=True, check=False, cwd=repo_root
    )
    if result.returncode != 0:
        error_msg = result.stderr.decode(
            "utf-8", errors="replace"
        ).strip()
        raise RuntimeError(
            f"git ls-files failed (exit {result.returncode}): "
            f"{error_msg}"
        )

    raw = result.stdout
    if not raw:
        return []

    regular_files: list[str] = []
    for part in raw.split(b"\x00"):
        if not part:
            continue
        try:
            entry = part.decode("utf-8", errors="replace")
            meta, file_path = entry.split("\t", 1)
            mode = meta.split(" ", 1)[0]
            if mode in ("100644", "100755"):
                regular_files.append(file_path)
        except ValueError:
            continue

    skipped = _skip_worktree_paths(repo_root)
    return [f for f in regular_files if f not in skipped]


def _skip_worktree_paths(repo_root: str) -> set:
    """Return index paths marked skip-worktree, which have no local file.

    A sparse checkout omits them deliberately, so reporting them as
    missing fails a valid working tree.
    """
    result = subprocess.run(
        [
            "git", "--no-pager",
            "-c", "core.fsmonitor=",
            "ls-files", "-v", "-z", "--full-name",
        ],
        capture_output=True,
        check=False,
        cwd=repo_root,
    )
    if result.returncode != 0:
        error_msg = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"git ls-files -v failed (exit {result.returncode}): "
            f"{_sanitize(error_msg)}"
        )
    skipped = set()
    for part in result.stdout.split(b"\x00"):
        if not part:
            continue
        entry = part.decode("utf-8", errors="replace")
        # git ls-files -v tags skip-worktree entries "S", then one space,
        # then the path. A lowercase tag is assume-unchanged, which still
        # has a working-tree file and stays in scope.
        if len(entry) > 2 and entry[0] == "S" and entry[1] == " ":
            skipped.add(entry[2:])
    return skipped


def _get_index_entries(
    repo_root: str,
) -> list[tuple[str, str, str, str]]:
    """Return (path, sha, stage, mode) for all index entries."""
    result = subprocess.run(
        [
            "git", "--no-pager",
            "-c", "core.fsmonitor=",
            "ls-files", "-s", "-z", "--full-name",
        ],
        capture_output=True,
        check=False,
        cwd=repo_root,
    )
    if result.returncode != 0:
        error_msg = result.stderr.decode(
            "utf-8", errors="replace"
        ).strip()
        raise RuntimeError(
            f"git ls-files failed (exit {result.returncode}): "
            f"{error_msg}"
        )

    entries: list[tuple[str, str, str, str]] = []
    raw = result.stdout
    if not raw:
        return entries

    for part in raw.split(b"\x00"):
        if not part:
            continue
        try:
            entry = part.decode("utf-8", errors="replace")
            meta, file_path = entry.split("\t", 1)
            fields = meta.split()
            mode = fields[0]
            sha = fields[1]
            stage = fields[2] if len(fields) > 2 else "0"
            entries.append((file_path, sha, stage, mode))
        except (ValueError, IndexError):
            continue

    return entries


def _get_blob_size(sha: str, repo_root: str) -> int:
    """Query object size without buffering object data."""
    result = subprocess.run(
        [
            "git", "--no-pager",
            "-c", "core.fsmonitor=",
            "--no-replace-objects",
            "cat-file", "-s", "--", sha,
        ],
        capture_output=True,
        check=False,
        cwd=repo_root,
    )
    if result.returncode != 0:
        error_msg = result.stderr.decode(
            "utf-8", errors="replace"
        ).strip()
        raise RuntimeError(
            f"git cat-file -s {sha[:12]} failed: {error_msg}"
        )
    return int(result.stdout.decode("utf-8", errors="replace").strip())


def _read_blob(
    sha: str, repo_root: str, max_size: int = MAX_FILE_SIZE
) -> bytes:
    """Read a single blob from the git object store with size limit."""
    proc = subprocess.Popen(
        [
            "git", "--no-pager",
            "-c", "core.fsmonitor=",
            "--no-replace-objects",
            "cat-file", "blob", "--", sha,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=repo_root,
    )
    data, err = proc.communicate()
    if proc.returncode != 0:
        error_msg = err.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"git cat-file blob {sha[:12]} failed: {error_msg}"
        )
    if len(data) > max_size:
        raise RuntimeError(
            f"blob {sha[:12]} size ({len(data)} bytes) exceeds "
            f"limit ({max_size} bytes)"
        )
    return data


def _check_staged(repo_root: str) -> list[str]:
    """Check staged index blobs for conflict markers.

    Reads from the object store, not the worktree. Flags unmerged
    entries (stage > 0) as violations. Index blobs are stored in
    canonical format (UTF-8 or BOM) so working-tree-encoding is not
    applied when decoding staged blobs.
    """
    entries = _get_index_entries(repo_root)

    violations: list[str] = []
    stage0_regular: list[tuple[str, str]] = []

    for file_path, sha, stage, mode in entries:
        if stage != "0":
            violations.append(
                f"{_sanitize(file_path)}: unmerged index entry "
                f"(stage {stage})"
            )
            continue
        if mode not in ("100644", "100755"):
            continue
        stage0_regular.append((file_path, sha))

    paths = [os.path.join(repo_root, p) for p, _ in stage0_regular]
    try:
        attributes = get_git_attributes(
            paths, repo_root=repo_root, cached=True
        )
    except RuntimeError as err:
        return [f"error: {_sanitize(err)}"]

    for file_path, sha in stage0_regular:
        if len(violations) >= MAX_VIOLATIONS:
            violations.append(
                f"reached violation limit ({MAX_VIOLATIONS}), "
                "stopping"
            )
            break

        file_attrs = attributes.get(file_path, {})
        conf_size = _parse_marker_size(
            file_attrs.get("conflict-marker-size")
        )

        try:
            blob_size = _get_blob_size(sha, repo_root)
        except (RuntimeError, ValueError) as err:
            violations.append(f"error: {_sanitize(file_path)}: {_sanitize(err)}")
            continue

        if blob_size > MAX_FILE_SIZE:
            violations.append(
                f"error: {_sanitize(file_path)}: blob size "
                f"({blob_size} bytes) exceeds limit "
                f"({MAX_FILE_SIZE} bytes)"
            )
            continue

        try:
            raw_bytes = _read_blob(sha, repo_root, MAX_FILE_SIZE)
        except RuntimeError as err:
            violations.append(f"error: {_sanitize(err)}")
            continue

        # Do not apply working-tree-encoding to staged index blobs
        text, decode_err = decode_content(raw_bytes, None)
        if decode_err:
            violations.append(f"error: {_sanitize(file_path)}: {_sanitize(decode_err)}")
            continue
        if text is None:
            continue

        violations.extend(
            check_content(text, file_path, conf_size)
        )

    return violations


def main() -> int:
    """Entry point for CLI execution."""
    raw_args = sys.argv[1:]
    staged = "--staged" in raw_args
    args = [a for a in raw_args if a != "--staged"]

    try:
        repo_root = _get_repo_root()
    except RuntimeError as err:
        print(f"error: {_sanitize(err)}", file=sys.stderr)
        return 1

    if staged:
        violations = _check_staged(repo_root)
        for v in violations:
            print(v, file=sys.stderr)
        return 1 if violations else 0

    # Resolve explicit file paths to absolute before chdir
    resolved: list[str] = []
    for arg in args:
        if arg == "--all":
            resolved.append(arg)
        else:
            resolved.append(os.path.abspath(arg))

    os.chdir(repo_root)

    files: list[str] = []
    if not resolved or resolved == ["--all"]:
        try:
            files = get_tracked_regular_files(repo_root)
        except RuntimeError as err:
            print(f"error: {_sanitize(err)}", file=sys.stderr)
            return 1
    else:
        for arg in resolved:
            if arg == "--all":
                try:
                    files.extend(
                        get_tracked_regular_files(repo_root)
                    )
                except RuntimeError as err:
                    print(f"error: {_sanitize(err)}", file=sys.stderr)
                    return 1
            else:
                files.append(arg)

    try:
        attributes = get_git_attributes(files, repo_root=repo_root)
    except RuntimeError as err:
        print(f"error: {_sanitize(err)}", file=sys.stderr)
        return 1

    violations: list[str] = []
    for path in files:
        file_attrs = attributes.get(path, {})
        conf_size = _parse_marker_size(
            file_attrs.get("conflict-marker-size")
        )
        encoding = file_attrs.get("working-tree-encoding")

        violations.extend(check_file(path, conf_size, encoding))

    for v in violations:
        print(v, file=sys.stderr)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
