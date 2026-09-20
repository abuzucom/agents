#!/usr/bin/env python3
"""Install one verified staged gate set without exposing ordinary work."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import check_gate_adoption as adoption
except ImportError:
    from scripts import check_gate_adoption as adoption

STAGING_DIRECTORY = ".gate-staging"
EXTRA_CLIENT_CONFIGS = (".codex/config.toml",)
CHECK_TIMEOUT_SECONDS = 30


def _is_under(path: Path, parent: Path) -> bool:
    """Return whether a resolved path remains below its expected parent."""
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _candidate(root: Path, value: str) -> Path:
    """Return a verified candidate directory below the fixed staging root."""
    staging = (root / STAGING_DIRECTORY).resolve(strict=True)
    candidate = Path(value).resolve(strict=True)
    if not candidate.is_dir() or not _is_under(candidate, staging):
        raise ValueError("candidate must be a directory below .gate-staging")
    return candidate


def _candidate_paths(candidate: Path) -> list[str]:
    """Return the complete static file set required for one transaction."""
    manifest_path = candidate / adoption.SHARED_MANIFEST
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    shared = document.get("shared")
    if not isinstance(shared, dict):
        raise ValueError("candidate shared-files.json is invalid")
    paths = set(shared)
    paths.update(adoption.CLIENT_HOOKS)
    paths.update(adoption.REQUIRED_CHECKERS)
    paths.update(adoption.REQUIRED_POLICY)
    paths.update(adoption.CONFIG_PATHS)
    paths.update(relative for relative, _event, _matcher in adoption.TRANSACTION_CONFIGS.values())
    paths.update(EXTRA_CLIENT_CONFIGS)
    return sorted(paths)


def _validate_candidate(root: Path, candidate: Path) -> None:
    """Reject an incomplete candidate before any target file changes."""
    checker = root / "scripts" / "check_gate_adoption.py"
    result = subprocess.run(
        [sys.executable, "-E", "-s", str(checker), "--root", str(candidate)],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=CHECK_TIMEOUT_SECONDS,
        check=False,
    )
    if result.returncode:
        raise ValueError("candidate fails check_gate_adoption.py")


def _target_path(root: Path, relative: str) -> Path:
    """Return a non-symlink target path below the repository root."""
    path = root / relative
    if not _is_under(path.parent.resolve(strict=False), root):
        raise ValueError(f"target escapes repository: {relative}")
    if path.is_symlink():
        raise ValueError(f"target is a symlink: {relative}")
    return path


def _replace_file(source: Path, target: Path) -> None:
    """Replace one target through a same-directory temporary file."""
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"candidate artifact is not a regular file: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".gate-adoption-", dir=target.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary)
        shutil.copystat(source, temporary)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def _ordered_paths(paths: list[str]) -> list[str]:
    """Copy hook registrations last so one invocation completes the transaction."""
    transaction_paths = {relative for relative, _event, _matcher in adoption.TRANSACTION_CONFIGS.values()}
    ordinary = sorted(path for path in paths if path not in transaction_paths)
    registrations = sorted(path for path in paths if path in transaction_paths)
    return ordinary + registrations


def main(argv: list[str]) -> int:
    """Install a complete staged candidate and verify the resulting target."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--candidate", required=True)
    options = parser.parse_args(argv)
    root = Path.cwd().resolve(strict=True)
    try:
        candidate = _candidate(root, options.candidate)
        _validate_candidate(root, candidate)
        paths = _ordered_paths(_candidate_paths(candidate))
        for relative in paths:
            _replace_file(candidate / relative, _target_path(root, relative))
        _validate_candidate(root, root)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(f"gate adoption transaction failed: {error}", file=sys.stderr)
        return 1
    print("gate adoption transaction completed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
