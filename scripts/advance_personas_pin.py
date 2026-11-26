#!/usr/bin/env python3
"""Advance every agents-personas pin site to one tagged personas commit.

Run this after each tagged agents-personas release. The update rewrites each
`uses:` pin, each `personas_ref`, the version comments, the wiring test
constants, the review documentation, and the exemption manifest digest of
the persona label caller in one pass. Open a draft pull request with the
result. The trusted compliance scan reads the manifest from the base branch.
The caller change therefore needs an immutable-compliance merge after review.

Usage:
    python scripts/advance_personas_pin.py <version> <commit>

Exit 0 means every pin site names the commit. Exit 1 means the pin sites
disagree or lack the current pin, and no file changed. Exit 2 means a usage
error.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_FAILURE = 1
USAGE_FAILURE = 2
CALLER = ".github/workflows/persona-review-labels.yml"
MANIFEST = ".compliance-tree-exemptions.json"
WORKFLOW_FILES = (
    CALLER,
    ".github/workflows/quality-review-pr.yml",
    ".github/workflows/security-review-pr.yml",
)
TEST_FILES = (
    "tests/test_persona_label_review_wiring.py",
    "tests/test_quality_review_wiring.py",
    "tests/test_security_review_wiring.py",
)
REVIEW_DOC = "docs/pr-security-review.md"
PIN_FILES = WORKFLOW_FILES + TEST_FILES + (REVIEW_DOC, MANIFEST)
VERSION_FILES = WORKFLOW_FILES + TEST_FILES + (REVIEW_DOC,)
VERSION_PATTERN = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
WRAPPER_PIN = re.compile(r"abuzucom/agents-personas/\.github/workflows/[a-z-]+\.yml@([0-9a-f]{40})")
CALLER_VERSION = re.compile(r"# agents-personas ([0-9]+\.[0-9]+\.[0-9]+)\.")
# Each version mention sits in one of these fixed phrases.
VERSION_PHRASES = ("agents-personas {}.", "version {}.")


class PinStateError(ValueError):
    """The pin sites disagree or lack the current pin."""


def current_pin(root: Path) -> str:
    """Return the one personas commit that every wrapper pin names."""
    pins = set()
    for name in WORKFLOW_FILES + (MANIFEST,):
        pins.update(WRAPPER_PIN.findall((root / name).read_text(encoding="utf-8")))
    if len(pins) != 1:
        raise PinStateError(f"wrapper pins name {len(pins)} commits; align every pin site by hand first")
    return pins.pop()


def current_version(root: Path) -> str:
    """Return the personas version that the caller comment names."""
    match = CALLER_VERSION.search((root / CALLER).read_text(encoding="utf-8"))
    if match is None:
        raise PinStateError(f"{CALLER} lacks its agents-personas version comment")
    return match.group(1)


def rewrite_text(name: str, text: str, pins: tuple, versions: tuple) -> str:
    """Return one file with the old pin and version replaced."""
    old_commit, new_commit = pins
    if old_commit not in text:
        raise PinStateError(f"{name} does not name the current pin {old_commit}")
    text = text.replace(old_commit, new_commit)
    if name in VERSION_FILES:
        old_version, new_version = versions
        for phrase in VERSION_PHRASES:
            text = text.replace(phrase.format(old_version), phrase.format(new_version))
    return text


def rewrite_manifest_digest(manifest_text: str, caller_text: str) -> str:
    """Return the manifest text with the caller digest replaced."""
    entry = json.loads(manifest_text)["pull_request_target"][CALLER]
    digest = hashlib.sha256(caller_text.encode("utf-8")).hexdigest()
    return manifest_text.replace(entry["sha256"], digest)


def plan_update(root: Path, version: str, commit: str) -> dict:
    """Return the new text of every changed pin site without writing."""
    old_commit = current_pin(root)
    if old_commit == commit:
        return {}
    pins, versions = (old_commit, commit), (current_version(root), version)
    updated = {}
    for name in PIN_FILES:
        text = (root / name).read_text(encoding="utf-8")
        updated[name] = rewrite_text(name, text, pins, versions)
    updated[MANIFEST] = rewrite_manifest_digest(updated[MANIFEST], updated[CALLER])
    return updated


def validate_arguments(argv: list) -> tuple:
    """Return (version, commit) or raise ValueError with a usage message."""
    if len(argv) != 2:
        raise ValueError("usage: advance_personas_pin.py <version> <commit>")
    version, commit = argv
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError("version must read X.Y.Z with no leading zeros")
    if not COMMIT_PATTERN.fullmatch(commit):
        raise ValueError("commit must be a full lowercase 40-character SHA")
    return version, commit


def main(argv: list | None = None, root: Path = ROOT) -> int:
    """Advance every pin site, or change nothing on a usage or state error."""
    try:
        version, commit = validate_arguments(sys.argv[1:] if argv is None else argv)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return USAGE_FAILURE
    try:
        updated = plan_update(root, version, commit)
    except (OSError, KeyError, json.JSONDecodeError, PinStateError) as error:
        print(f"error: {error}. No file changed.", file=sys.stderr)
        return STATE_FAILURE
    for name, text in updated.items():
        (root / name).write_text(text, encoding="utf-8")
    print(f"pinned agents-personas {version} at {commit} in {len(updated)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
