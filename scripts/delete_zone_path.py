#!/usr/bin/env python3
"""Delete untracked paths inside this session's own zone folders.

Usage: python scripts/delete_zone_path.py --session <id> <path> [<path> ...]

The command execution gate asks before this helper runs. The helper repeats
every path check at delete time through directory descriptors. Each path
component opens relative to its parent and follows no link. A swap of any
component to a link after the gate check refuses the delete. A final link
gets removed itself and its target stays.

Exit codes:
- 0: every operand got deleted.
- 1: the walk or the delete refused an operand.
- 2: the input, the tracked state, or the platform refused the call.
"""
import functools
import os
import shutil
import stat
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
EXIT_DELETED = 0
EXIT_WALK_REFUSED = 1
EXIT_INPUT_REFUSED = 2
SESSION_OPTION = "--session"
MINIMUM_ARGUMENTS = 3
# A zone name, the session id, and at least one name below the session folder.
MINIMUM_COMPONENTS = 3
CURRENT_DIRECTORY = "."
DESCRIPTOR_FUNCTIONS = (os.open, os.stat, os.unlink, os.rmdir)
USAGE = "usage: delete_zone_path.py --session <id> <path> [<path> ...]"


@functools.lru_cache(maxsize=1)
def _zone_modules() -> tuple:
    """Import and return the shared zone check and Git probe modules from hooks/."""
    sys.path.insert(0, str(REPOSITORY_ROOT / "hooks"))
    import _git_probe
    import _zones
    return _zones, _git_probe


def safe_deletion_supported() -> bool:
    """Return whether the platform can delete through descriptors without following links."""
    return (hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")
            and all(function in os.supports_dir_fd for function in DESCRIPTOR_FUNCTIONS)
            and os.stat in os.supports_follow_symlinks
            and bool(getattr(shutil.rmtree, "avoids_symlink_attacks", False)))


def _directory_flags() -> int:
    """Return the open flags for one directory component that must not be a link."""
    return os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY


def _components(operand: str, session_id: str):
    """Return the path components of a zone operand, or None for any other operand."""
    zones, _probe = _zone_modules()
    if not zones.literal_operand(operand):
        return None
    parts = operand.split("/")
    if len(parts) < MINIMUM_COMPONENTS or parts[0] not in zones.ZONES:
        return None
    if parts[1] != session_id or any(part in ("", CURRENT_DIRECTORY) for part in parts):
        return None
    return parts


def _delete_one(root_descriptor: int, parts: list) -> bool:
    """Walk to the parent of the last component through descriptors and delete it."""
    descriptors = []
    try:
        current = root_descriptor
        for name in parts[:-1]:
            current = os.open(name, _directory_flags(), dir_fd=current)
            descriptors.append(current)
        last = parts[-1]
        status = os.stat(last, dir_fd=current, follow_symlinks=False)
        if stat.S_ISDIR(status.st_mode):
            shutil.rmtree(last, dir_fd=current)
        else:
            os.unlink(last, dir_fd=current)
        return True
    except OSError as error:
        print(f"delete_zone_path: walk or delete failed ({type(error).__name__}). "
              "Check that the path exists and holds no link.", file=sys.stderr)
        return False
    finally:
        for descriptor in descriptors:
            os.close(descriptor)


def _validated_components(root: str, session_id: str, operands: list):
    """Return the component lists for every operand, or None when any check fails."""
    if not safe_deletion_supported():
        print("delete_zone_path: this platform lacks descriptor deletion. Nothing got deleted.",
              file=sys.stderr)
        return None
    zones, probe = _zone_modules()
    if not zones.valid_session_id(session_id) or not operands:
        return None
    components = [_components(operand, session_id) for operand in operands]
    if any(parts is None for parts in components):
        return None
    tracked = probe.tracked_paths(root, operands)
    if tracked is None or tracked:
        return None
    return components


def delete_zone_paths(root: str, session_id: str, operands: list) -> int:
    """Delete each operand below the session's own zone folders and return an exit code."""
    components = _validated_components(root, session_id, operands)
    if components is None:
        print("delete_zone_path: the operands or session id failed the zone check. "
              "Nothing got deleted.", file=sys.stderr)
        return EXIT_INPUT_REFUSED
    try:
        root_descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    except OSError as error:
        print(f"delete_zone_path: the repository root failed to open ({type(error).__name__}).",
              file=sys.stderr)
        return EXIT_WALK_REFUSED
    try:
        for index, parts in enumerate(components, 1):
            if not _delete_one(root_descriptor, parts):
                print(f"delete_zone_path: operand {index} refused.", file=sys.stderr)
                return EXIT_WALK_REFUSED
    finally:
        os.close(root_descriptor)
    return EXIT_DELETED


def main(argv=None) -> int:
    """Parse the session option and operands, then delete inside the repository zones."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) < MINIMUM_ARGUMENTS or arguments[0] != SESSION_OPTION:
        print(USAGE, file=sys.stderr)
        return EXIT_INPUT_REFUSED
    return delete_zone_paths(str(REPOSITORY_ROOT), arguments[1], arguments[2:])


if __name__ == "__main__":
    sys.exit(main())
