#!/usr/bin/env python3
"""Enforce a configured, allowed git identity on commits.

A portable, path-generic checker: copy this file into any repo and use it
as a pre-commit hook, a `pull_request` CI step, or a Claude Code hook
through hooks/enforce_git_identity.py. Three modes:

  no flags        the identity the next commit would use, read from config
  --unpushed      commits on HEAD absent from every remote-tracking ref
  --base/--head   commits in a range, for CI on a pull request

The default mode is the reliable one. With `user.name` or `user.email`
unset, git builds an identity from the account name and hostname, prints
its automatic-identity warning, and commits anyway. This mode fails first,
before the guess reaches a commit object.

Limitation: the commit modes cannot recover that signal, because a commit
object records no mark saying its author field was built rather than
configured. They apply the allowlist only.

The default allowlist accepts GitHub noreply addresses, which link a commit
to its account and publish no private address. The committer may also be
`noreply@github.com`, which is what GitHub itself sets on squash merges.
Override with --allow for a repo that commits under another convention.

Blocking: exits 1 on any violation, 2 on a usage error.
"""
import argparse
import os
import re
import subprocess
import sys

NOREPLY = re.compile(
    r"\A(?:[0-9]+\+)?[A-Za-z0-9-]+(?:\[bot\])?@users\.noreply\.github\.com\Z",
    re.IGNORECASE,
)
NOREPLY_LOGIN = re.compile(
    r"\A(?:[0-9]+\+)?(?P<login>[A-Za-z0-9-]+)@users\.noreply\.github\.com\Z",
    re.IGNORECASE,
)
GITHUB_COMMITTER = "noreply@github.com"

# Git treats each of these as an explicitly given identity, in this order.
# A checker that read only user.email would block harnesses and CI systems
# that supply one through the environment instead.
NAME_SOURCES = (
    ("env", "GIT_AUTHOR_NAME"),
    ("env", "GIT_COMMITTER_NAME"),
    ("config", "user.name"),
)
EMAIL_SOURCES = (
    ("env", "GIT_AUTHOR_EMAIL"),
    ("env", "GIT_COMMITTER_EMAIL"),
    ("config", "user.email"),
    ("env", "EMAIL"),
)

COMMIT_SEP = "\x1e"
FIELD_SEP = "\x1f"
GH_TIMEOUT_SECONDS = 5

FIX_MESSAGE = (
    "fix: ask the user which name and email to commit under, then set them:\n"
    "  git config user.name  '<login>'\n"
    "  git config user.email '<id>+<login>@users.noreply.github.com'\n"
    "Do not invent an identity, and do not copy one out of this repository's\n"
    "history. An authenticated gh is not a git identity."
)


def _config(key: str) -> str:
    """Return a git config value, or an empty string when it is unset."""
    result = subprocess.run(
        ["git", "config", "--get", key], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _first_explicit(sources: tuple) -> str:
    """Return the first value git would treat as an explicitly given field."""
    for kind, key in sources:
        value = os.environ.get(key, "").strip() if kind == "env" else _config(key)
        if value:
            return value
    return ""


def worktree_identity() -> dict:
    """Return the identity the next commit would use, and what git would guess."""
    name = _first_explicit(NAME_SOURCES)
    email = _first_explicit(EMAIL_SOURCES)
    return {
        "label": "worktree",
        "author_email": email,
        "committer_email": email,
        "unset_name": not name,
        "unset_email": not email,
    }


def log_identities(revisions: list) -> list:
    """Return one identity record per commit reachable by `revisions`."""
    fmt = FIELD_SEP.join(["%H", "%ae", "%ce"])
    result = subprocess.run(
        ["git", "log", *revisions, f"--format={fmt}{COMMIT_SEP}"],
        capture_output=True,
        text=True,
        check=True,
    )
    identities = []
    for record in result.stdout.split(COMMIT_SEP):
        record = record.strip("\n")
        if not record:
            continue
        sha, author_email, committer_email = record.split(FIELD_SEP, 2)
        identities.append(
            {
                "label": sha[:12],
                "author_email": author_email,
                "committer_email": committer_email,
                "unset_name": False,
                "unset_email": False,
            }
        )
    return identities


def unpushed_identities() -> list:
    """Return identity records for commits on HEAD absent from every remote."""
    result = subprocess.run(["git", "remote"], capture_output=True, text=True, check=False)
    if not result.stdout.strip():
        return []
    return log_identities(["HEAD", "--not", "--remotes"])


def _allowed(email: str, pattern: re.Pattern) -> bool:
    """Return True when `email` matches the allowlist pattern."""
    return bool(pattern.match(email.strip()))


def find_violations(identities: list, pattern: re.Pattern = NOREPLY) -> list:
    """Return one message per unset field or disallowed address."""
    violations = []
    for identity in identities:
        label = identity["label"]
        if identity["unset_email"]:
            violations.append(
                f"{label}: user.email is unset, so git builds one from this "
                "machine's account name and hostname and commits on a warning"
            )
        if identity["unset_name"]:
            violations.append(
                f"{label}: user.name is unset, so git builds one from this "
                "machine's account and commits on a warning"
            )
        if identity["unset_email"] or identity["unset_name"]:
            continue
        author = identity["author_email"]
        if not _allowed(author, pattern):
            violations.append(f"{label}: author email '{author}' is not an allowed address")
        committer = identity["committer_email"]
        if committer.strip().lower() == GITHUB_COMMITTER:
            continue
        if not _allowed(committer, pattern):
            violations.append(
                f"{label}: committer email '{committer}' is not an allowed address"
            )
    return violations


def gh_advisory(email: str) -> str:
    """Return a note about the gh-authenticated account. Never blocks."""
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            check=False,
            timeout=GH_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "note: gh is unavailable, so the account behind this identity is unverified"
    login = result.stdout.strip()
    if result.returncode != 0 or not login:
        return "note: gh is not authenticated, so the account behind this identity is unverified"
    match = NOREPLY_LOGIN.match(email.strip())
    if not match:
        return (
            f"note: gh is authenticated as '{login}', but the configured address is "
            "not a noreply address for that account"
        )
    if match.group("login").lower() != login.lower():
        return f"note: gh is authenticated as '{login}' but commits would be authored as '{email}'"
    return ""


def config_only_advisory() -> str:
    """Return a note when git may still auto-detect an identity on this machine."""
    if _config("user.useConfigOnly").lower() == "true":
        return ""
    return (
        "note: user.useConfigOnly is not true, so git auto-detects an identity "
        "when user.email is unset. Set it once per machine: "
        "git config --global user.useConfigOnly true"
    )


def select_identities(args: argparse.Namespace) -> list:
    """Return the identity records the requested mode covers."""
    if args.base:
        return log_identities([f"{args.base}..{args.head}"])
    if args.unpushed:
        return unpushed_identities()
    return [worktree_identity()]


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="", help="base ref (exclusive); pairs with --head")
    parser.add_argument("--head", default="", help="head ref (inclusive); pairs with --base")
    parser.add_argument(
        "--unpushed", action="store_true", help="check commits absent from every remote"
    )
    parser.add_argument("--allow", default="", help="regex of allowed emails; overrides the default")
    parser.add_argument(
        "--advise",
        action="store_true",
        help="report the gh account and user.useConfigOnly; never changes the exit code",
    )
    return parser


def _print_advisories(identities: list) -> None:
    """Print the non-blocking machine and account notes."""
    email = identities[0]["author_email"] if identities else ""
    for note in (config_only_advisory(), gh_advisory(email)):
        if note:
            print(note)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if bool(args.base) != bool(args.head):
        parser.error("--base and --head must be given together")
    pattern = re.compile(args.allow) if args.allow else NOREPLY

    try:
        identities = select_identities(args)
    except subprocess.CalledProcessError as error:
        print(f"error: git log failed: {error}", file=sys.stderr)
        return 1
    except OSError:
        print("note: git is unavailable, so there is nothing to check")
        return 0

    if args.advise:
        _print_advisories(identities)

    violations = find_violations(identities, pattern)
    if violations:
        for message in violations:
            print(message, file=sys.stderr)
        print(FIX_MESSAGE, file=sys.stderr)
        return 1
    if args.base or args.unpushed:
        print(f"no identity violations found in {len(identities)} commit(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
