#!/usr/bin/env python3
"""Shared decision logic for the shell gates.

Not part of AGENTS.md, which stays tool-agnostic and is synced to non-Claude
tools verbatim. This module holds everything the Bash and PowerShell gates
decide identically, so the two cannot drift: payload reading and field-type
validation, the deny and ask emission, the ask-to-deny downgrade for an
unattended session, root-target detection, and the whole git classification.

Each gate keeps only what its shell spells differently: how a command
tokenizes, where one statement ends, which wrappers and redirections lead a
command, and how a delete's flags are written. Both call in here for the
verdict.

A hook run as `python3 .../hooks/<gate>.py` gets `hooks/` as `sys.path[0]`,
so `import _gate_core` resolves with no packaging. A gate that cannot import
this module must fail closed rather than crash, because Claude Code treats a
non-zero exit other than 2 as a non-blocking error, which waves the command
through.
"""
import json
import os
import sys

INTERACTIVE_MODES = frozenset({"default", "plan", "acceptEdits", "auto"})
AMBIGUOUS_MARKERS = ("$", "`")
FILESYSTEM_ROOTS = frozenset({"/", "//", "/*"})
HOME_PREFIXES = ("~", "$HOME", "${HOME}", "$env:USERPROFILE",
                 "$Env:USERPROFILE", "%USERPROFILE%", "%HOMEPATH%")
GIT_VALUE_OPTIONS = frozenset({
    "-C", "-c", "--exec-path", "--git-dir", "--work-tree", "--namespace",
    "--config-env", "--super-prefix",
})
HISTORY_SUBCOMMANDS = {
    "rebase": "git rebase: this rewrites history",
    "filter-branch": "git filter-branch: this rewrites history",
    "filter-repo": "git filter-repo: this rewrites history",
}
STRENGTH = {"": 0, "ask": 1, "deny": 2}


def require_str(value):
    """Return `value` when it is a string, otherwise None.

    A gate that reads a field without checking its type crashes on a number
    or a list, and a crash is an exit code Claude Code ignores.
    """
    return value if isinstance(value, str) else None


def is_ambiguous(token: str) -> bool:
    """Return True if the token hides its value behind shell expansion."""
    return any(marker in token for marker in AMBIGUOUS_MARKERS)


def is_short_group(token: str) -> bool:
    """Return True if the token is a bundle of short flags such as -Rf."""
    return token.startswith("-") and not token.startswith("--") and len(token) > 1


def is_root_target(token: str) -> bool:
    """Return True if the token names the filesystem root or a home directory."""
    return token in FILESYSTEM_ROOTS or token.startswith(HOME_PREFIXES)


def strongest(first: tuple, second: tuple) -> tuple:
    """Return whichever (decision, reason) pair carries the stronger decision."""
    return second if STRENGTH[second[0]] > STRENGTH[first[0]] else first


def delete_verdict(recursive: bool, operands: list, noun: str) -> tuple:
    """Return (decision, reason) for a recursive delete over `operands`.

    Each shell parses its own flags and hands the result here, so `rm -Rf`
    and `Remove-Item -Recurse -Force` reach the same answer. `noun` carries
    the caller's own wording, so each gate names the command its user typed.
    """
    if not recursive:
        return "", ""
    if any(is_root_target(operand) for operand in operands):
        return "deny", f"{noun} targeting / or the home directory"
    return "ask", f"{noun}: Rule 2 gates every target, including one this session created"


def git_subcommand(args: list) -> tuple:
    """Return (subcommand, remaining args) after skipping git's global options."""
    index = 0
    while index < len(args):
        token = args[index]
        if not token.startswith("-"):
            return token, args[index + 1:]
        if token.split("=", 1)[0] in GIT_VALUE_OPTIONS and "=" not in token:
            index += 2
        else:
            index += 1
    return "", []


def _push_flag_reason(token: str, name: str) -> str:
    """Return why a git push flag needs consent, or an empty string."""
    if name.startswith("--force"):
        return "git push with a --force variant: a lease is not consent to rewrite pushed history"
    if name == "--mirror":
        return "git push --mirror: this overwrites and deletes published refs"
    if name == "--delete" or (is_short_group(token) and "d" in token):
        return "git push --delete: this removes a published ref"
    if name == "--prune":
        return "git push --prune: this deletes every remote ref with no local counterpart"
    return ""


def _push_operand_reason(token: str) -> str:
    """Return why a git push refspec needs consent, or an empty string.

    A refspec deletes or rewrites without carrying any flag: `+HEAD:main`
    forces, and `:main` pushes an empty source, which deletes the remote ref.
    """
    if token.startswith("+"):
        return "git push with a forced refspec: this rewrites pushed history"
    if token.startswith(":"):
        return "git push with an empty-source refspec: this deletes the remote ref"
    return ""


def push_ask_reason(token: str, name: str) -> str:
    """Return why a single git push argument needs consent, or an empty string."""
    if token.startswith("-"):
        return _push_flag_reason(token, name)
    return _push_operand_reason(token)


def push_verdict(args: list) -> tuple:
    """Return (decision, reason) for a git push argument list."""
    ask = ""
    for token in args:
        name = token.split("=", 1)[0]
        if name == "--force" or (is_short_group(token) and "f" in token):
            return "deny", "git push --force"
        ask = ask or push_ask_reason(token, name)
    return ("ask", ask) if ask else ("", "")


def git_verdict(args: list) -> tuple:
    """Return (decision, reason) for a git argument list."""
    subcommand, rest = git_subcommand(args)
    if not subcommand or is_ambiguous(subcommand):
        return "ask", "git with an unresolved subcommand: the gate cannot tell what this runs"
    if subcommand == "push":
        return push_verdict(rest)
    if subcommand == "reset" and "--hard" in rest:
        return "deny", "git reset --hard"
    if subcommand == "commit" and "--amend" in rest:
        return "ask", "git commit --amend: this rewrites a commit"
    if subcommand in HISTORY_SUBCOMMANDS:
        return "ask", HISTORY_SUBCOMMANDS[subcommand]
    return "", ""


def unparseable_verdict(command: str, keywords: tuple) -> tuple:
    """Fail closed when a command naming one of `keywords` will not tokenize."""
    if any(keyword in command for keyword in keywords):
        return "ask", "this command could not be parsed, so the gate cannot clear it"
    return "", ""


def read_payload(empty_is_session_start: bool = False):
    """Return the stdin payload, or None when it cannot be parsed.

    `empty_is_session_start` yields an empty dict for empty stdin, which
    is how a SessionStart invocation arrives. Without it that hook would
    deny every session start. A gate that answers "fine" to input it
    could not read is worse than no gate, so anything else that will not
    parse is still None.
    """
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return None
    if empty_is_session_start and not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def emit(gate: str, decision: str, reason: str) -> int:
    """Print the gate's decision and return the exit code it needs."""
    message = f"blocked by hooks/{gate}: {reason}"
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": message,
        }
    }
    print(json.dumps(output))
    if decision == "deny":
        print(message, file=sys.stderr)
        return 2
    return 0


def decide(gate: str, payload: dict, decision: str, reason: str) -> int:
    """Emit the decision, turning an ask nobody can answer into a deny."""
    if decision == "deny":
        return emit(gate, "deny", reason)
    if require_str(payload.get("permission_mode")) in INTERACTIVE_MODES:
        return emit(gate, "ask", reason)
    return emit(gate, "deny", f"{reason}. No interactive session is available to consent.")


MAX_REASON_VALUE = 160


def sanitize(value) -> str:
    """Render untrusted text as printable ASCII on a single line.

    An allowlist, not a strip. Zero-width characters, bidi overrides, and
    Unicode tag characters are not control characters, and they render
    invisibly or reverse the text around them, so a denylist of known-bad
    codepoints misses the cases that matter most. These values reach two
    readers who cannot afford to be misled: the human deciding on the
    permission prompt, and the model reading stderr as tool output.
    """
    rendered = []
    for character in str(value):
        if " " <= character <= "~":
            rendered.append(character)
        elif ord(character) <= 0xFF:
            rendered.append(f"\\x{ord(character):02x}")
        else:
            rendered.append(f"\\u{ord(character):04x}")
    text = "".join(rendered)
    if len(text) > MAX_REASON_VALUE:
        return text[:MAX_REASON_VALUE] + "...[truncated]"
    return text


def project_dir(payload: dict) -> str:
    """Return the repository root, preferring Claude Code's own variable."""
    return (os.environ.get("CLAUDE_PROJECT_DIR")
            or payload.get("cwd")
            or os.getcwd())


def resolved_under(root: str, *parts: str):
    """Return the joined path when it stays under `root`, else None.

    Joining a payload-supplied directory with a fixed relative path and
    running the result executes whatever sits at that path. Canonicalize
    first and require the result to stay inside the tree.
    """
    base = os.path.realpath(root)
    candidate = os.path.realpath(os.path.join(base, *parts))
    if candidate == base or candidate.startswith(base + os.sep):
        return candidate
    return None


CMD_DELETE_VERBS = frozenset({"del", "erase", "rd", "rmdir"})
CMD_RECURSIVE_FLAGS = frozenset({"/s"})


def cmd_delete_verdict(program: str, args: list) -> tuple:
    """Return (decision, reason) for a CMD deletion verb.

    CMD flags are slash-prefixed and case-insensitive, and rd and rmdir
    remove a directory tree whenever /s is present. del and erase take
    /s to recurse into subdirectories.
    """
    if program.lower() not in CMD_DELETE_VERBS:
        return "", ""
    recursive = False
    operands = []
    for token in args:
        if token.startswith("/"):
            recursive = recursive or token.lower() in CMD_RECURSIVE_FLAGS
        else:
            operands.append(token)
    return delete_verdict(recursive, operands, f"recursive {program.lower()}")
