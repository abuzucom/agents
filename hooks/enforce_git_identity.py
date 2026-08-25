#!/usr/bin/env python3
"""Enforce a configured git identity through Claude Code hooks.

Not part of AGENTS.md, which stays tool-agnostic and is synced to non-Claude
tools verbatim. This is a Claude-Code-specific hook under hooks/, wired via
`.claude/settings.json` (live in this repo) or
hooks/claude-code-settings.example.json (for adopting repos). One file serves
two hook events, dispatched on `hook_event_name` in the stdin payload:

`SessionStart` runs scripts/check_git_identity.py with `--advise` before the
session does any git work, and on a violation injects a stop-and-ask
instruction into the session context. Claude Code ignores a non-zero exit
from a SessionStart hook, so injected context is the only lever it has.

`PreToolUse` on the `Bash` matcher is the blocking half: it exits 2 on a
`git commit` while the identity is unset or disallowed, and on a `git push`
while either the working-tree config or any commit that push would publish
fails the same check. It never runs `--advise`, which makes a network call.

The two events cover a failure no instruction fixes: with `user.email` unset,
git builds an identity from the account name and hostname, prints its
"configured automatically" warning, and commits anyway. A session that reads
that warning in command output has already made the commit.

`git config` is never blocked, so the fix stays reachable. Run it as its own
tool call: this hook reads config state before the shell runs, so a chained
`git config ... && git commit ...` is evaluated before the config lands.

Known gap: `git merge`, `git revert`, `git cherry-pick`, `git rebase`, and
`git am` also write commits and are not matched. Matching them would block
`git merge --ff-only` and most rebases, which create no commit.
"""
import json
import os
import re
import subprocess
import sys

CHECKER_PATH = os.path.join("scripts", "check_git_identity.py")
BLOCKED_COMMANDS = (
    (r"\bgit\s+commit\b", "git commit"),
    (r"\bgit\s+push\b", "git push"),
)
PUSH_LABEL = "git push"


def _read_payload() -> dict:
    """Return the hook's stdin JSON, or an empty dict when stdin carries none."""
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        return {}


def _project_dir(payload: dict) -> str:
    """Return the repository root, preferring Claude Code's own variable."""
    return os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()


def run_checker(project_dir: str, extra_args: list):
    """Run scripts/check_git_identity.py, or return None when the repo has no copy."""
    checker = os.path.join(project_dir, CHECKER_PATH)
    if not os.path.isfile(checker):
        return None
    return subprocess.run(
        [sys.executable, checker, *extra_args],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )


def find_violation(project_dir: str, extra_args: list) -> str:
    """Return the checker's complaint about the identity, or an empty string.

    An absent checker yields an empty string: a repo that has not copied
    scripts/check_git_identity.py has no identity policy for this hook to
    enforce.
    """
    result = run_checker(project_dir, extra_args)
    if result is None or result.returncode == 0:
        return ""
    return result.stderr.strip() or "the git identity does not meet this repo's policy"


def check_args(label: str) -> list:
    """Return the checker invocations that gate `label`."""
    if label == PUSH_LABEL:
        return [[], ["--unpushed"]]
    return [[]]


def build_warning(violation: str, advisory: str) -> str:
    """Return the session-context text for a bad or unset git identity."""
    lines = [
        "STOP: GIT IDENTITY VIOLATION. DO NOT COMMIT OR PUSH YET.",
        "",
        violation,
        "",
        "With user.name or user.email unset, git builds an identity from this",
        "machine's account name and hostname, prints a warning, and commits",
        "anyway. That leaves a permanent commit authored by an address nobody",
        "chose, linked to no account. An authenticated gh does not supply it:",
        "git and gh read separate configuration.",
        "",
        "Take this action before any commit or push:",
        "1. Ask the user which name and email to commit under. Do not invent",
        "   one, and do not copy one out of this repository's history.",
        "2. Set it in this repository as its own tool call:",
        "     git config user.name  '<login>'",
        "     git config user.email '<id>+<login>@users.noreply.github.com'",
        "",
        "A PreToolUse hook blocks git commit and git push until the identity",
        "is set and allowed, so proceeding without that action fails.",
    ]
    if advisory:
        lines.extend(["", advisory])
    return "\n".join(lines)


def blocked_command(command: str) -> str:
    """Return the git write operation found in `command`, or an empty string."""
    for pattern, label in BLOCKED_COMMANDS:
        if re.search(pattern, command):
            return label
    return ""


def _handle_session_start(project_dir: str) -> int:
    """Inject a stop-and-ask instruction into the session context."""
    result = run_checker(project_dir, ["--advise"])
    if result is None or result.returncode == 0:
        return 0
    violation = result.stderr.strip() or "the git identity does not meet this repo's policy"
    warning = build_warning(violation, result.stdout.strip())
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": warning,
        },
        "systemMessage": warning,
    }
    print(json.dumps(output))
    return 0


def _handle_pre_tool_use(payload: dict, project_dir: str) -> int:
    """Block a commit or push while the git identity is unset or disallowed."""
    if payload.get("tool_name") != "Bash":
        return 0
    command = payload.get("tool_input", {}).get("command", "")
    label = blocked_command(command)
    if not label:
        return 0
    for extra_args in check_args(label):
        violation = find_violation(project_dir, extra_args)
        if not violation:
            continue
        print(
            f"blocked by hooks/enforce_git_identity.py: {label} with an unset or "
            f"disallowed git identity.\n"
            f"{violation}\n"
            f"Ask the user which name and email to commit under, then set them "
            f"with git config as a separate tool call. Do not invent an identity.",
            file=sys.stderr,
        )
        return 2
    return 0


def main() -> int:
    payload = _read_payload()
    project_dir = _project_dir(payload)
    event = payload.get("hook_event_name", "SessionStart")
    if event == "PreToolUse":
        return _handle_pre_tool_use(payload, project_dir)
    return _handle_session_start(project_dir)


if __name__ == "__main__":
    sys.exit(main())
