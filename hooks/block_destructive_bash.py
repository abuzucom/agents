#!/usr/bin/env python3
"""Gate destructive and history-rewriting Bash commands via a PreToolUse hook.

Not part of AGENTS.md, which stays tool-agnostic and is synced to non-Claude
tools verbatim. This is a Claude-Code-specific hook under hooks/, wired via
`.claude/settings.json` (live in this repo) or
hooks/claude-code-settings.example.json (for adopting repos). It reads the
PreToolUse JSON payload from stdin and checks only Bash tool calls.

The command is tokenized and normalized before any decision. Matching the raw
string matches spelling rather than meaning, and every destructive command has
many spellings: `rm -Rf` for `rm -rf`, `git -C dir push --force` for
`git push --force`, `--force-with-lease=main:<oid>` for `--force-with-lease`,
`git push origin +HEAD:main` for a forced push with no flag at all. A gate
that reads the string lets each of those through while appearing to work.

Two outcomes, because two different rules are in play:

`deny` covers commands with no legitimate form in this workflow: a recursive
`rm` aimed at `/`, `~`, or `$HOME`, a bare `git push --force`/`-f`, and
`git reset --hard`. It prints the reason on stderr and exits 2, so the block
holds wherever stdout JSON is ignored.

`ask` covers acts that are legitimate with the user's consent and forbidden
without it: a recursive `rm` against any other target, the
`--force-with-lease` family, `git push --mirror`, `git push --delete`, a
forced (`+`) refspec, `git commit --amend`, `git rebase`, and
`git filter-branch`. Routing these through the permission prompt puts the
decision where AGENTS.md puts it, with the human, at the act. Rule 2 carries
no scope qualifier, so a scratch directory the session created itself is
gated like any other target, and a lease does not make a history rewrite
consented to.

Ambiguity fails closed. A command that will not tokenize, or a `git` whose
subcommand is hidden behind a variable, is gated rather than waved through:
the gate cannot clear what it cannot read.

An `ask` needs a human to answer it. When `permission_mode` reports an
unattended session, or a mode this hook does not recognize, the ask becomes a
deny: absence of a human is absence of consent.

Still a heuristic, not a sandbox. It does not execute the shell, so a command
hidden behind an alias, a wrapper script, or a variable holding the program
name is invisible to it.
"""
import json
import os
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import _gate_core as core
except ImportError as error:  # pragma: no cover - exercised by the adoption test
    # Fail closed. Claude Code treats any non-zero exit other than 2 as a
    # non-blocking error, so an unhandled ImportError would wave the command
    # through in exactly the repos that installed this gate.
    _REASON = f"hooks/_gate_core.py could not be imported ({error}), so the gate cannot clear this command"
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": _REASON,
    }}))
    print(_REASON, file=sys.stderr)
    sys.exit(2)

GATE = "block_destructive_bash.py"
GATED_KEYWORDS = ("rm", "git")
OPERATOR_CHARS = frozenset("&|;")
GROUPING = frozenset({"(", ")", "\n"})
WRAPPERS = frozenset({"sudo", "doas", "env", "time", "nohup", "nice", "command", "xargs"})


def _tokenize(command: str):
    """Return the command's tokens, or None when it cannot be parsed."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return None


def _is_separator(token: str) -> bool:
    """Return True if the token separates one command from the next."""
    return token in GROUPING or (bool(token) and set(token) <= OPERATOR_CHARS)


def _segments(tokens: list) -> list:
    """Split tokens into the individual commands the shell would run."""
    segments = [[]]
    for token in tokens:
        if _is_separator(token):
            segments.append([])
        else:
            segments[-1].append(token)
    return [segment for segment in segments if segment]


def _is_env_assignment(token: str) -> bool:
    """Return True if the token is a leading VAR=value assignment."""
    if token.startswith("-") or "=" not in token:
        return False
    return token.split("=", 1)[0].isidentifier()


def _strip_prefixes(tokens: list) -> list:
    """Drop leading environment assignments and command wrappers."""
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if _is_env_assignment(token) or os.path.basename(token) in WRAPPERS:
            index += 1
            continue
        break
    return tokens[index:]


def _rm_targets(args: list) -> tuple:
    """Return (recursive, operands) for an rm argument list."""
    recursive = False
    operands = []
    parsing = True
    for token in args:
        if parsing and token == "--":
            parsing = False
        elif parsing and token.startswith("--"):
            recursive = recursive or token == "--recursive"
        elif parsing and core.is_short_group(token):
            recursive = recursive or "r" in token or "R" in token
        else:
            operands.append(token)
    return recursive, operands


def _rm_verdict(args: list) -> tuple:
    """Return (decision, reason) for an rm argument list."""
    recursive, operands = _rm_targets(args)
    return core.delete_verdict(recursive, operands, "recursive rm")


def _segment_verdict(tokens: list) -> tuple:
    """Return (decision, reason) for one command segment."""
    tokens = _strip_prefixes(tokens)
    if not tokens:
        return "", ""
    program = os.path.basename(tokens[0])
    if program == "rm":
        return _rm_verdict(tokens[1:])
    if program == "git":
        return core.git_verdict(tokens[1:])
    return "", ""


def classify(command: str) -> tuple:
    """Return the strongest (decision, reason) across the command's segments."""
    tokens = _tokenize(command)
    if tokens is None:
        return core.unparseable_verdict(command, GATED_KEYWORDS)
    verdict = ("", "")
    for segment in _segments(tokens):
        verdict = core.strongest(verdict, _segment_verdict(segment))
    return verdict


def find_reason(command: str) -> str:
    """Return why `command` is denied outright, or an empty string if it is not."""
    decision, reason = classify(command)
    return reason if decision == "deny" else ""


def find_consent_reason(command: str) -> str:
    """Return why `command` needs the user's consent, or an empty string."""
    decision, reason = classify(command)
    return reason if decision == "ask" else ""


def emit(decision: str, reason: str) -> int:
    """Print the gate's decision and return the exit code it needs."""
    return core.emit(GATE, decision, reason)


def main() -> int:
    payload = core.read_payload()
    if payload is None:
        return emit("deny", "the hook payload could not be parsed, so the gate cannot clear this command")
    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return emit("deny", "the tool input is malformed, so the gate cannot read this command")
    decision, reason = classify(tool_input.get("command", ""))
    if not decision:
        return 0
    return core.decide(GATE, payload, decision, reason)


if __name__ == "__main__":
    sys.exit(main())
