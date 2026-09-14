#!/usr/bin/env python3
"""Block malformed or unversioned changelogs."""
import argparse
import re
import sys
from pathlib import Path

try:
    from scripts.trusted_git import run_git
except ModuleNotFoundError:
    from trusted_git import run_git

VERSION_PATTERN = re.compile(r"^## \[(\d+)\.(\d+)\.(\d+)\](?:-([0-9A-Za-z.-]+))? \((\d{4}-\d{2}-\d{2})\)$")
HEADING_PATTERN = re.compile(r"^## \[(.+)\] (.+)$")
UNRELEASED_PATTERN = re.compile(r"^## \[Unreleased\]$")


def _version_key(match: re.Match[str]) -> tuple[int, int, int]:
    """Return the numeric ordering key for a version heading."""
    return tuple(int(match.group(index)) for index in range(1, 4))


def find_violations(text: str) -> list[str]:
    """Return blocking findings for one changelog document."""
    lines = text.splitlines()
    headings: list[tuple[int, re.Match[str]]] = []
    findings: list[str] = []
    for line_number, line in enumerate(lines, 1):
        if UNRELEASED_PATTERN.fullmatch(line):
            findings.append(f"line {line_number}: [Unreleased] is not allowed")
        if not line.startswith("## ["):
            continue
        match = VERSION_PATTERN.fullmatch(line)
        if match:
            headings.append((line_number, match))
            continue
        if HEADING_PATTERN.fullmatch(line):
            findings.append(f"line {line_number}: invalid version heading")
    if not headings:
        findings.append("changelog has no versioned release heading")
        return findings
    versions = [_version_key(match) for _, match in headings]
    if versions != sorted(versions, reverse=True):
        findings.append("version headings must be in descending order")
    if len(set(versions)) != len(versions):
        findings.append("version headings must be unique")
    for index, (line_number, _match) in enumerate(headings):
        end = headings[index + 1][0] - 1 if index + 1 < len(headings) else len(lines)
        if not any(line.strip() for line in lines[line_number:end]):
            findings.append(f"line {line_number}: release needs a versioned entry")
    return findings


def check_file(path: Path) -> int:
    """Print findings for a changelog path and return a process code."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        print(f"error: cannot read {path}: {error}", file=sys.stderr)
        return 1
    findings = find_violations(text)
    for finding in findings:
        print(f"error: {path}: {finding}", file=sys.stderr)
    if findings:
        return 1
    print(f"valid changelog: {path}")
    return 0


def _first_version(text: str) -> tuple[int, int, int] | None:
    """Return the first release version in changelog text."""
    for line in text.splitlines():
        match = VERSION_PATTERN.fullmatch(line)
        if match:
            return _version_key(match)
    return None


def check_staged(repository: Path) -> int:
    """Require a changed versioned changelog entry for staged changes."""
    try:
        staged = run_git(
            repository, ["diff", "--cached", "--name-only", "--diff-filter=ACMRT"],
            check=True,
        ).stdout.splitlines()
        if not staged:
            return 0
        current = run_git(repository, ["show", ":CHANGELOG.md"], check=True).stdout
        previous_result = run_git(
            repository, ["show", "HEAD:CHANGELOG.md"], check=False,
        )
    except (OSError, UnicodeError, ValueError):
        print("error: cannot inspect staged changelog", file=sys.stderr)
        return 1
    findings = find_violations(current)
    current_version = _first_version(current)
    previous_version = _first_version(previous_result.stdout)
    if "CHANGELOG.md" not in staged:
        findings.append("staged changes require a versioned CHANGELOG.md entry")
    elif current_version == previous_version:
        findings.append("CHANGELOG.md version must advance with staged changes")
    for finding in findings:
        print(f"error: CHANGELOG.md: {finding}", file=sys.stderr)
    return 1 if findings else 0


def main() -> int:
    """Run the changelog checker."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="CHANGELOG.md")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    if args.staged:
        return check_staged(Path(args.repo).resolve())
    return check_file(Path(args.path))


if __name__ == "__main__":
    sys.exit(main())
