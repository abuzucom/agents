#!/usr/bin/env python3
"""Validate canonical skills and keep their client copies identical.

Each skill lives once at `skills/<name>/SKILL.md`. Clients read their own
folders, so synchronization writes byte-identical copies below every root in
SKILL_COPY_ROOTS. One of those roots sits inside the protected `.agents/`
folder. Every path component therefore gets an lstat check, and a copy lands
through a temporary file plus `os.replace`, so no symlink or partial write
can redirect or truncate a protected file.

Frontmatter follows an allowlist. A client can treat an unknown key as
configuration, such as a tool grant, so any key outside
ALLOWED_FRONTMATTER_KEYS fails.
"""
import os
import re
import stat
import tempfile
from pathlib import Path

SKILLS = (
    "pr-steward",
    "session-branch-recovery",
    "compaction-replan",
    "git-identity-recovery",
    "commit-and-draft-pr",
    "test-defect-report",
    "gate-denial-report",
    "destructive-act-authorization",
    "dependency-proposal",
    "policy-change-proposal",
    "gate-adoption",
    "session-handoff",
)
SKILL_SOURCE_ROOT = "skills"
SKILL_COPY_ROOTS = (".claude/skills", ".agents/skills")
SKILL_FILE = "SKILL.md"
SKILL_NAME_PATTERN = re.compile(r"[a-z0-9-]{1,64}")
ALLOWED_FRONTMATTER_KEYS = ("name", "description")
FRONTMATTER_FENCE = "---"
FRONTMATTER_LINE = re.compile(r"([a-z-]{1,32}): ([^\s|>][^\r\n]{0,299})")
# Real skills stay far below this. The cap bounds every read of repository data.
MAX_SKILL_BYTES = 64 * 1024


def _validated_name(name: str) -> str:
    """Return a skill name that cannot leave its folder, or raise ValueError."""
    if not SKILL_NAME_PATTERN.fullmatch(name):
        raise ValueError(f"skill name {name!r} must match {SKILL_NAME_PATTERN.pattern}")
    return name


def canonical_path(name: str) -> str:
    """Return the repository-relative canonical file for one skill."""
    return f"{SKILL_SOURCE_ROOT}/{_validated_name(name)}/{SKILL_FILE}"


def copy_paths(name: str) -> tuple:
    """Return every repository-relative client copy for one skill."""
    skill = _validated_name(name)
    return tuple(f"{root}/{skill}/{SKILL_FILE}" for root in SKILL_COPY_ROOTS)


def _frontmatter_lines(text: str) -> list | None:
    """Return the lines between the opening and closing fences, or None."""
    lines = text.split("\n")
    if lines[0] != FRONTMATTER_FENCE or FRONTMATTER_FENCE not in lines[1:]:
        return None
    return lines[1:lines.index(FRONTMATTER_FENCE, 1)]


def frontmatter_problems(name: str, text: str) -> list:
    """Return every reason the skill text breaks the frontmatter rules."""
    if not text.isascii():
        return [f"{canonical_path(name)} holds non-ASCII text"]
    lines = _frontmatter_lines(text)
    if lines is None:
        return [f"{canonical_path(name)} lacks a fenced frontmatter block"]
    fields = {}
    for line in lines:
        match = FRONTMATTER_LINE.fullmatch(line)
        if match is None or match.group(1) in fields:
            return [f"{canonical_path(name)} frontmatter line is not one single-line key"]
        fields[match.group(1)] = match.group(2)
    if tuple(sorted(fields)) != tuple(sorted(ALLOWED_FRONTMATTER_KEYS)):
        return [f"{canonical_path(name)} frontmatter keys must be exactly name and description"]
    if fields["name"] != name:
        return [f"{canonical_path(name)} frontmatter name differs from its folder"]
    return []


def _require_directory(path: Path, create: bool) -> bool:
    """Return whether a real directory exists at path, creating it on request."""
    try:
        details = path.lstat()
    except FileNotFoundError:
        if not create:
            return False
        os.mkdir(path)
        details = path.lstat()
    if not stat.S_ISDIR(details.st_mode):
        raise ValueError(f"{path.name} is not a real directory")
    return True


def _parent_directory(root: Path, relative: str, create: bool) -> Path | None:
    """Validate each parent component of relative, or return None when absent."""
    current = root
    _require_directory(current, create=False)
    for part in Path(relative).parent.parts:
        current = current / part
        if not _require_directory(current, create):
            return None
    return current


def _read_regular(root: Path, relative: str) -> bytes | None:
    """Return the bytes of a regular file, None when absent, or raise ValueError."""
    parent = _parent_directory(root, relative, create=False)
    if parent is None:
        return None
    path = parent / Path(relative).name
    try:
        details = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(details.st_mode) or details.st_size > MAX_SKILL_BYTES:
        raise ValueError(f"{relative} is not a regular file within the size cap")
    return path.read_bytes()


def _write_atomic(root: Path, relative: str, content: bytes) -> None:
    """Write content to relative through a temporary file and os.replace."""
    parent = _parent_directory(root, relative, create=True)
    target = parent / Path(relative).name
    if _read_regular(root, relative) == content:
        return
    descriptor, temporary = tempfile.mkstemp(prefix=".skill-", dir=parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        _parent_directory(root, relative, create=False)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _canonical_bytes(root: Path, name: str) -> tuple:
    """Return (bytes or None, problems) for one canonical skill."""
    relative = canonical_path(name)
    content = _read_regular(root, relative)
    if content is None:
        return None, [f"{relative} is absent"]
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return None, [f"{relative} is not UTF-8"]
    problems = frontmatter_problems(name, text)
    return (None if problems else content), problems


def _copy_problems(root: Path, name: str, content: bytes) -> list:
    """Return absent or stale findings for the copies of one skill."""
    problems = []
    for relative in copy_paths(name):
        actual = _read_regular(root, relative)
        if actual is None:
            problems.append(f"{relative} is absent")
        elif actual != content:
            problems.append(f"{relative} is stale; run python scripts/sync.py")
    return problems


def skill_problems(root: Path, skills: tuple = SKILLS) -> list:
    """Return every canonical and copy finding without writing anything."""
    problems = []
    for name in skills:
        try:
            content, found = _canonical_bytes(root, name)
            problems.extend(found)
            if content is not None:
                problems.extend(_copy_problems(root, name, content))
        except (OSError, ValueError) as error:
            problems.append(f"{name}: unsafe skill path ({error})")
    return problems


def sync_skills(root: Path, skills: tuple = SKILLS) -> list:
    """Write every stale or absent copy and return the findings that blocked a write."""
    problems = []
    for name in skills:
        try:
            content, found = _canonical_bytes(root, name)
            problems.extend(found)
            if content is None:
                continue
            for relative in copy_paths(name):
                _write_atomic(root, relative, content)
        except (OSError, ValueError) as error:
            problems.append(f"{name}: unsafe skill path ({error})")
    return problems
