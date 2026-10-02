"""Classify shell programs and repository workflows for the branch hook.

The branch hook imports this module for every shell command it inspects.
Denials and consent prompts from this module name this file, so a blocked
program points at the command allowlist rather than at branch naming.
"""
import os

# The importing hook puts hooks/ on sys.path and fails closed when these are absent.
import _gate_core as core
import _bash_parser as bash_parser

GATE = "_command_execution_gate.py"
INSPECTABLE_PROGRAMS = frozenset({
    "echo", "printf", "pwd", "cat", "head", "tail", "wc", "ls", "dir",
    "get-content", "get-childitem", "get-location", "write-output",
    "touch", "tee", "cp", "mv", "set-content", "add-content", "out-file",
    "copy-item", "move-item", "copy", "move", "type", "true", "false",
})
WORKFLOW_SCRIPT_ARGUMENTS = {
    "scripts/run_tests.py": ((),),
    "scripts/read_git_state.py": tuple((mode,) for mode in ("branch", "status", "remote", "revision", "all")),
    "scripts/sync.py": ((), ("--check",), ("--check-shared",), ("--write-shared",), ("--print-adoptable",)),
    "scripts/check_action_pins.py": ((),),
    "scripts/check_gate_adoption.py": ((),),
}
READ_ONLY_WORKFLOW_ARGUMENTS = {
    "scripts/run_tests.py": ((),),
    "scripts/read_git_state.py": WORKFLOW_SCRIPT_ARGUMENTS["scripts/read_git_state.py"],
    "scripts/sync.py": (("--check",), ("--check-shared",), ("--print-adoptable",)),
    "scripts/check_action_pins.py": ((),),
    "scripts/check_gate_adoption.py": ((),),
}
SEARCH_FLAGS = frozenset({
    "-n", "--line-number", "-l", "--files-with-matches", "-i", "--ignore-case",
    "-F", "--fixed-strings", "--files", "--hidden", "-g", "--glob", "-e", "--regexp", "--",
})
MAX_WORKFLOW_ARGUMENTS = 64
MAKE_TARGETS = ("lint", "test", "check", "sync", "identity")
MAKE_ARGUMENTS = ([], ["PYTHON=python"], ["PYTHON=python3"])
PYTHON_PROGRAMS = ("python", "python3", "python.exe", "python3.exe")
SHELL_OPERATORS = (";", "&", "&&", "|", "||", "(", ")")
WORKFLOW_FORBIDDEN_CHARACTERS = "<>%!^\0"
# Prefix wrappers that only adjust the environment or skip shell lookup.
TRANSPARENT_WRAPPERS = ("env", "command", "exec")


def segment_program_reason(segment: list) -> str:
    """Return why one command segment runs an uninspectable program, or ""."""
    executable, _assignments, complete = bash_parser.strip_prefixes(segment)
    if not complete:
        return "Command wrapper could not be inspected"
    if not executable:
        return ""
    program = core.normalize_windows_command_name(executable[0])
    if executable[0].casefold() not in (program, program + ".exe"):
        return "A script or executable path cannot claim an inspectable program name"
    # Prefix options can change cwd or remove inherited configuration.
    prefix_count = len(segment) - len(executable)
    if any(token in bash_parser.WRAPPERS and token not in TRANSPARENT_WRAPPERS
           for token in segment[:prefix_count]):
        return "Command wrapper has opaque input or execution context"
    if any(token.startswith("-") for token in segment[:prefix_count]):
        return "Command wrapper changes unresolved execution settings"
    if program != "git" and program not in INSPECTABLE_PROGRAMS:
        return "Opaque command execution requires an inspectable operation"
    return ""


def arguments_reason(executable: list) -> str:
    """Return why non-Git arguments depend on shell expansion, or ""."""
    if any(core.is_ambiguous(token) for token in executable):
        return "Command arguments contain unresolved expansion"
    return ""


def _python_workflow(tokens: list, project_dir: str) -> bool:
    """Recognize bounded repository scripts and unittest module invocations."""
    if tokens[1:3] == ["-m", "unittest"]:
        modules = [token for token in tokens[3:] if token not in ("-v", "-q")]
        return bool(modules) and all(
            token.startswith("tests.") and all(part.isidentifier() for part in token.split("."))
            for token in modules)
    path = core.resolved_under(project_dir, tokens[1])
    if path is None or not os.path.isfile(path):
        return False
    if tokens[1] == "scripts/trusted_gh.py" and tokens[2:3] == ["run"]:
        decision, _reason = core.forge_verdict("gh", tokens[3:], project_dir)
        return bool(tokens[3:]) and decision != "deny"
    return tuple(tokens[2:]) in WORKFLOW_SCRIPT_ARGUMENTS.get(tokens[1], ())


def _literal_tokens(command: str) -> list:
    """Return the tokens of one literal invocation without wrappers or redirection."""
    if "\n" in command or "\r" in command or len(command) > bash_parser.MAX_COMMAND_CHARACTERS:
        return []
    tokens, complete = bash_parser._tokenize_line(command)
    if not complete or not 1 < len(tokens) <= MAX_WORKFLOW_ARGUMENTS:
        return []
    if any(core.is_ambiguous(token) or token in SHELL_OPERATORS
           or any(character in token for character in WORKFLOW_FORBIDDEN_CHARACTERS)
           for token in tokens):
        return []
    return tokens


def workflow_needs_consent(command: str, project_dir: str) -> bool:
    """Limit workflow consent to one literal invocation without wrappers or redirection."""
    tokens = _literal_tokens(command)
    if not tokens:
        return False
    if tokens[0] in PYTHON_PROGRAMS:
        return _python_workflow(tokens, project_dir)
    if tokens[0] == "make":
        return tokens[1] in MAKE_TARGETS and tokens[2:] in MAKE_ARGUMENTS
    if tokens[0] == "rg":
        return all(not token.startswith("-") or token in SEARCH_FLAGS for token in tokens[1:])
    return False


def read_only_workflow(command: str, project_dir: str) -> bool:
    """Return whether a consent-routed workflow only inspects the repository."""
    if not workflow_needs_consent(command, project_dir):
        return False
    tokens, _complete = bash_parser._tokenize_line(command)
    if tokens[0] == "rg" or tokens[1:3] == ["-m", "unittest"]:
        return True
    return tuple(tokens[2:]) in READ_ONLY_WORKFLOW_ARGUMENTS.get(tokens[1], ())
