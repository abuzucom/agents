#!/usr/bin/env python3
"""Check tracked files for unresolved git merge conflict markers.

A portable, path-generic checker: copy this file into any repo and run
it in CI or pre-commit hooks. Flags unresolved merge conflict markers
(`<<<<<<<`, `=======`, `>>>>>>>`) in source and documentation files.
Exits 1 on any violation (blocking), 0 if clean.
"""
import re
import sys
from pathlib import Path

CONFLICT_MARKER = re.compile(r"^(<{7}|={7}|>{7})( |$)")


def check_file(path: str) -> list[str]:
    """Return violations found in a single file."""
    violations = []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as error:
        return [f"warning: could not read {path}: {error}"]

    for number, line in enumerate(text.splitlines(), 1):
        if CONFLICT_MARKER.match(line):
            violations.append(f"{path}:{number}: unresolved conflict marker '{line}'")
    return violations


def main() -> int:
    files = sys.argv[1:]
    if not files:
        print("usage: check_conflict_markers.py <file> ...", file=sys.stderr)
        return 1

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
