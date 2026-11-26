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

Exit 0 means every pin site names the commit. Exit 1 means a pin site is
missing, the pin sites disagree, or a write failed. Exit 1 leaves every file
as it was. Exit 2 means a usage error.
"""
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
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
# A wrapper runs from its uses: pin and loads policy from personas_ref. Both
# fields and the test constants must name one commit.
PERSONAS_REF_PIN = re.compile(r'personas_ref: "([0-9a-f]{40})"')
TEST_CONSTANT_PIN = re.compile(r'PINNED_COMMIT = "([0-9a-f]{40})"')
PIN_PATTERNS = {name: (WRAPPER_PIN, PERSONAS_REF_PIN) for name in WORKFLOW_FILES}
PIN_PATTERNS.update({name: (TEST_CONSTANT_PIN,) for name in TEST_FILES})
PIN_PATTERNS[MANIFEST] = (WRAPPER_PIN,)
CALLER_VERSION = re.compile(r"# agents-personas ([0-9]+\.[0-9]+\.[0-9]+)\.")
# Each version mention sits in one of these fixed phrases.
VERSION_PHRASES = ("agents-personas {}.", "version {}.")


STAGING_PREFIX = ".pin-"


class PinStateError(ValueError):
    """The pin sites disagree, lack the current pin, or miss a site."""


class PinWriteError(OSError):
    """A replacement failed after staging. Every replaced file was restored."""


def validate_pin_sites(root: Path) -> None:
    """Raise PinStateError unless every expected pin site exists.

    Each wrapper call needs a `uses:` pin and a `personas_ref`. Each wiring
    test needs one constant. The manifest keys must match the caller pins.
    """
    for name in WORKFLOW_FILES:
        text = read_site(root, name)
        uses = WRAPPER_PIN.findall(text)
        refs = PERSONAS_REF_PIN.findall(text)
        if not uses or len(uses) != len(refs):
            raise PinStateError(f"{name} holds {len(uses)} uses: pins and {len(refs)} "
                                "personas_ref values. Each wrapper call needs both")
    for name in TEST_FILES:
        if len(TEST_CONSTANT_PIN.findall(read_site(root, name))) != 1:
            raise PinStateError(f"{name} needs exactly one PINNED_COMMIT constant")
    caller_targets = {match.group(0) for match in WRAPPER_PIN.finditer(read_site(root, CALLER))}
    manifest = json.loads(read_site(root, MANIFEST))
    manifest_targets = set(manifest["pull_request_target"][CALLER]["reusable_workflows"])
    if manifest_targets != caller_targets:
        raise PinStateError(f"{MANIFEST} workflow keys differ from the {CALLER} uses: pins")


def read_site(root: Path, name: str) -> str:
    """Return one pin site with its line endings exactly as stored."""
    return (root / name).read_bytes().decode("utf-8")


def stage_site(root: Path, name: str, text: str) -> Path:
    """Write one pin site to a temporary file beside its target and return the path."""
    target = root / name
    descriptor, temp_name = tempfile.mkstemp(prefix=STAGING_PREFIX, dir=target.parent)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(text.encode("utf-8"))
    # mkstemp creates mode 0600. The replace must keep the target's mode.
    os.chmod(temp_name, stat.S_IMODE(target.stat().st_mode))
    return Path(temp_name)


def replace_sites(root: Path, staged: dict, originals: dict) -> None:
    """Move each staged file over its target, or restore every replaced target on failure."""
    replaced = []
    try:
        for name, temp_path in staged.items():
            os.replace(temp_path, root / name)
            replaced.append(name)
    except OSError as error:
        for name in replaced:
            (root / name).write_bytes(originals[name])
        raise PinWriteError(f"replacing {name} failed ({error}); restored "
                            f"{len(replaced)} replaced files") from error


def write_sites(root: Path, updated: dict) -> None:
    """Write every pin site or none. Staging stays beside each target for an atomic replace."""
    originals = {name: (root / name).read_bytes() for name in updated}
    staged = {}
    try:
        for name, text in updated.items():
            staged[name] = stage_site(root, name, text)
        replace_sites(root, staged, originals)
    finally:
        for temp_path in staged.values():
            temp_path.unlink(missing_ok=True)


def current_pin(root: Path) -> str:
    """Return the one personas commit that every uses: pin, personas_ref, and test constant names."""
    pins = set()
    for name, patterns in PIN_PATTERNS.items():
        text = read_site(root, name)
        for pattern in patterns:
            pins.update(pattern.findall(text))
    if len(pins) != 1:
        raise PinStateError(f"pin sites name {len(pins)} commits; align every pin site by hand first")
    return pins.pop()


def current_version(root: Path) -> str:
    """Return the personas version that the caller comment names."""
    match = CALLER_VERSION.search(read_site(root, CALLER))
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
    """Return the manifest text with the caller digest replaced.

    The trusted compliance scan hashes the caller blob. `text: auto` stores
    that blob with LF endings, so a CRLF checkout hashes after normalizing.
    """
    entry = json.loads(manifest_text)["pull_request_target"][CALLER]
    digest = hashlib.sha256(caller_text.replace("\r\n", "\n").encode("utf-8")).hexdigest()
    return manifest_text.replace(entry["sha256"], digest)


def plan_update(root: Path, version: str, commit: str) -> dict:
    """Return the new text of every changed pin site without writing."""
    validate_pin_sites(root)
    old_commit = current_pin(root)
    old_version = current_version(root)
    # A tag can name a new version on the same commit. Only an unchanged
    # commit and version leave every file as it is.
    if (old_commit, old_version) == (commit, version):
        return {}
    pins, versions = (old_commit, commit), (old_version, version)
    updated = {}
    for name in PIN_FILES:
        updated[name] = rewrite_text(name, read_site(root, name), pins, versions)
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
    except (OSError, KeyError, UnicodeDecodeError, json.JSONDecodeError, PinStateError) as error:
        print(f"error: {error}. No file changed.", file=sys.stderr)
        return STATE_FAILURE
    try:
        write_sites(root, updated)
    except PinWriteError as error:
        print(f"error: {error}. Every pin site holds its original bytes.", file=sys.stderr)
        return STATE_FAILURE
    except OSError as error:
        print(f"error: staging failed ({error}). No file changed.", file=sys.stderr)
        return STATE_FAILURE
    print(f"pinned agents-personas {version} at {commit} in {len(updated)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
