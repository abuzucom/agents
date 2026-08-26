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
import re
import sys

INTERACTIVE_MODES = frozenset({"default", "plan", "acceptEdits", "auto"})
AMBIGUOUS_MARKERS = ("$", "`")
FILESYSTEM_ROOTS = frozenset({"/", "//", "/*"})
# Directories whose removal takes the machine with them. These deny rather
# than ask: putting "delete /etc?" in front of a person is not consent, it
# is an invitation to a mistake nobody can undo.
SYSTEM_ROOTS = frozenset({
    "/", "/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/lib32",
    "/lib64", "/libx32", "/media", "/mnt", "/opt", "/proc", "/root",
    "/run", "/sbin", "/srv", "/sys", "/temp", "/tmp", "/usr", "/var",
    "/system", "/library", "/applications", "/volumes", "/users",
    "/private", "/cores",
})

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


def _is_drive_root(token: str) -> bool:
    """Return True for the root of any drive or share.

    C:\\, D:/, \\\\server\\share, and the bare drive letter C: all name a
    whole volume. No workflow deletes one, so these deny rather than ask:
    an agent has no business putting that choice in front of a person.
    """
    candidate = token.strip().strip('"').strip("'")
    if candidate.startswith("\\\\") or candidate.startswith("//"):
        parts = [part for part in candidate.replace("\\", "/").split("/") if part]
        return len(parts) <= 2
    stripped = candidate.rstrip("\\/")
    return len(stripped) == 2 and stripped[1] == ":" and stripped[0].isalpha()


def _is_system_root(token: str) -> bool:
    """Return True if the token names a system directory itself.

    A path inside one is an ordinary recursive delete and still asks. The
    directory itself is not a target any workflow has.
    """
    candidate = token.strip().strip('"').strip("'").replace("\\", "/")
    if not candidate:
        return False
    # normpath collapses . and .. and duplicate separators, so /usr/. and
    # /home/.. reach the same verdict as /usr and /.
    normalized = os.path.normpath(candidate).lower()
    if not normalized.startswith("/"):
        return False
    return normalized in SYSTEM_ROOTS


def is_root_target(token: str) -> bool:
    """Return True if the token names the filesystem root or a home directory."""
    if _is_system_root(token) or _is_drive_root(token):
        return True
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


READ_SUBCOMMANDS = frozenset({"status", "diff", "log", "show", "blame",
                              "grep", "shortlog", "whatchanged"})


KNOWN_SUBCOMMANDS = frozenset({
    "push", "reset", "commit", "rebase", "filter-branch", "add", "checkout",
    "switch", "restore", "merge", "fetch", "pull", "clone", "branch", "tag",
    "remote", "stash", "config", "init", "rm", "mv", "cherry-pick", "revert",
    "bisect", "worktree", "submodule", "describe", "rev-parse", "ls-files",
    "cat-file", "hash-object", "check-attr", "replace", "update-index",
    "apply", "am", "format-patch", "archive", "gc", "reflog", "notes",
}) | READ_SUBCOMMANDS


def cleared_config_keys(args: list) -> set:
    """Return the config keys this invocation neutralizes with -c key=."""
    cleared = set()
    for index, token in enumerate(args):
        if token == "-c" and index + 1 < len(args):
            setting = args[index + 1]
        elif token.startswith("-c") and len(token) > 2:
            setting = token[2:]
        else:
            continue
        key, separator, value = setting.partition("=")
        if separator and not value:
            cleared.add(key.strip().lower())
    return cleared


def git_verdict(args: list, cwd: str = "") -> tuple:
    """Return (decision, reason) for a git argument list."""
    subcommand, rest = git_subcommand(args)
    if not subcommand or is_ambiguous(subcommand):
        return "ask", "git with an unresolved subcommand: the gate cannot tell what this runs"
    if subcommand in READ_SUBCOMMANDS:
        return repo_executes_on_read(cwd, cleared_config_keys(args))
    if subcommand not in KNOWN_SUBCOMMANDS:
        expansion = resolve_alias(cwd, subcommand)
        if not expansion:
            return "ask", (f"git {sanitize(subcommand)}: not a git subcommand "
                           "and not a declared alias, so the gate cannot tell "
                           "what this runs")
        if expansion.startswith("!"):
            # A shell alias. Classify the text; never expand or run it.
            return "ask", (f"git {sanitize(subcommand)} is a shell alias, "
                           "which the gate cannot read as a git command")
        return git_verdict(expansion.split() + rest, cwd)
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
    """Fail closed when a command naming one of `keywords` will not tokenize.

    A command the gate cannot parse but which names a drive root or a
    system directory denies rather than asks. `rm -rf C:\\` ends in an
    unterminated escape, and no reading of it is one to put to a person.
    """
    if not any(keyword in command for keyword in keywords):
        return "", ""
    for word in command.replace("\\", "/").split():
        if is_root_target(word) or is_root_target(word.rstrip("/") + "/"):
            return "deny", ("this command could not be parsed and names a "
                            "root or system directory")
    return "ask", "this command could not be parsed, so the gate cannot clear it"


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


TEST_DIR_PARTS = frozenset({"tests", "test", "__tests__", "spec"})
TEST_NAME = re.compile(
    r"^test_.+\.(py|js|mjs|cjs|ts|jsx|tsx|ipynb)$"
    r"|_test\.(py|js|mjs|cjs|ts|go|rb)$"
    r"|\.(test|spec)\.(js|mjs|cjs|jsx|ts|tsx)$",
    re.IGNORECASE,
)
# Commands whose named operand is a file they overwrite in place.
WRITE_PROGRAMS = {"tee": 0, "sed": -1, "cp": -1, "mv": -1}


def strip_windows_decorations(name: str) -> str:
    """Return the filename Windows opens for `name`.

    An NTFS alternate data stream (`test_x.py:evil`) writes into the same
    file, and Windows discards a trailing dot or space.
    """
    base = name.split(":", 1)[0] if ":" in name[2:] else name
    return base.rstrip(". ")


def is_test_path(path: str) -> bool:
    """Return True if `path` names a test file by directory or filename."""
    normalized = os.path.normpath(path).replace("\\", "/").replace(os.sep, "/")
    parts = [part.lower() for part in normalized.split("/")]
    if TEST_DIR_PARTS.intersection(parts[:-1]):
        return True
    return bool(TEST_NAME.search(strip_windows_decorations(parts[-1])))


def test_write_verdict(program: str, args: list, redirect_targets: list) -> tuple:
    """Return (decision, reason) for a command that writes to a test file.

    A redirect or an in-place edit reaches a test file where no Edit or
    Write matcher can see it, so Rule 3 would apply to the same act
    through one tool and not the other.
    """
    targets = list(redirect_targets)
    position = WRITE_PROGRAMS.get(os.path.basename(program).lower())
    if position is not None:
        operands = [token for token in args if not token.startswith("-")]
        if operands:
            targets.append(operands[position])
    for target in targets:
        if is_test_path(target):
            return "ask", ("writes to an existing test file, which Rule 3 "
                           "puts in front of the user at the act")
    return "", ""


MAX_CONFIG_BYTES = 256 * 1024
# Keys whose value names a program git runs during an ordinary read.
EXEC_CAPABLE_KEYS = frozenset({
    "core.fsmonitor", "core.pager", "core.editor", "core.sshcommand",
    "core.hookspath", "core.alternaterefscommand", "core.askpass",
    "diff.external", "log.showsignature", "gpg.program",
    "uploadpack.packobjectshook", "sequence.editor", "pager.diff",
})
# Sections where any driver name carries an exec-capable key.
EXEC_CAPABLE_SUBSECTIONS = {
    "filter": ("clean", "smudge", "process"),
    "diff": ("textconv", "command"),
    "gpg": ("program",),
    "merge": ("driver",),
}


def parse_git_config(cwd: str):
    """Return {"section.key": value} from .git/config, or None on failure.

    The file is read, never queried through `git config`: running git to
    decide whether running git is safe is the bug this exists to close.
    Format is git's own, which configparser does not implement, so it is
    parsed here. None means the caller must fail closed.
    """
    path = os.path.join(cwd or ".", ".git", "config")
    try:
        if os.path.getsize(path) > MAX_CONFIG_BYTES:
            return None
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError):
        return None

    entries = {}
    section = ""
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped[0] in "#;":
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            head = stripped[1:-1].strip()
            name, _, subsection = head.partition(" ")
            section = f"{name.lower()}.{subsection.strip(chr(34))}" if subsection else name.lower()
            continue
        key, separator, value = stripped.partition("=")
        if not separator:
            continue
        entries[f"{section}.{key.strip().lower()}"] = value.strip()
    return entries


def _exec_capable_key(entries: dict) -> str:
    """Return the first exec-capable key present, or an empty string."""
    for name, value in entries.items():
        if name in EXEC_CAPABLE_KEYS and value.lower() not in ("", "false", "0"):
            return name
        parts = name.split(".")
        if len(parts) == 3 and parts[2] in EXEC_CAPABLE_SUBSECTIONS.get(parts[0], ()):
            return name
    return ""


def repo_executes_on_read(cwd: str, cleared: set) -> tuple:
    """Return (decision, reason) for a git read in a repo that runs programs.

    `cleared` holds keys the command already neutralized with -c key=, which
    is the escape hatch: a caller who disables the knob is not gated on it.
    """
    entries = parse_git_config(cwd)
    if entries is None:
        return "ask", (".git/config could not be read, so the gate cannot "
                       "tell whether this command runs a program")
    remaining = {name: value for name, value in entries.items()
                 if name not in cleared}
    found = _exec_capable_key(remaining)
    if not found:
        return "", ""
    return "ask", (f"a git read in a repository whose config sets {found}, "
                   f"which names a program git runs")


def resolve_alias(cwd: str, subcommand: str) -> str:
    """Return what `subcommand` expands to, or an empty string."""
    entries = parse_git_config(cwd)
    if not entries:
        return ""
    return entries.get(f"alias.{subcommand.lower()}", "")
