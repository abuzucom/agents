"""Hardened read-only Git calls for the zone delete check.

Repository configuration can name commands Git runs, such as
core.fsmonitor. The probe disables that hook, keeps an allowlisted
environment, takes no optional locks, bounds time and output, and treats
every failure as unknown. Callers then fail closed.

This module uses only the standard library and imports no gate module.
"""
import os
import subprocess

GIT_TIMEOUT_SECONDS = 5
MAX_OUTPUT_BYTES = 256 * 1024
# Only these variables reach Git. GIT_OPTIONAL_LOCKS=0 keeps a read from
# contending for the index lock with another session's commit.
ENVIRONMENT_KEYS = ("PATH", "SYSTEMROOT", "HOME", "USERPROFILE", "TMPDIR", "TEMP", "TMP")
FIXED_ENVIRONMENT = {"GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}


def _environment() -> dict:
    """Return the allowlisted environment for a probe call."""
    environment = {key: os.environ[key] for key in ENVIRONMENT_KEYS if key in os.environ}
    environment.update(FIXED_ENVIRONMENT)
    return environment


def tracked_paths(project_dir: str, paths: list):
    """Return the tracked files at or below the given repository-relative paths.

    Returns None when Git fails, times out, or prints more than the cap.
    """
    command = ["git", "-C", project_dir, "-c", "core.fsmonitor=false", "ls-files", "-z",
               "--", *paths]
    try:
        result = subprocess.run(command, capture_output=True, check=False,
                                timeout=GIT_TIMEOUT_SECONDS, env=_environment())
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or len(result.stdout) > MAX_OUTPUT_BYTES:
        return None
    try:
        text = result.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return frozenset(name for name in text.split("\0") if name)
