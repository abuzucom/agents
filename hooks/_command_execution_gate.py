"""Classify shell programs and repository workflows for the branch hook.

The branch hook imports this module for every shell command it inspects.
Denials and consent prompts from this module name this file, so a blocked
program points at the command allowlist rather than at branch naming.
"""
import json
import os
import stat

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
NPM_PROGRAM = "npm"
NPM_MANIFEST = "package.json"
NPM_LOCKFILES = ("package-lock.json", "npm-shrinkwrap.json")
NPM_TEST_SCRIPT = "test"
# `npm run` accepts only these names. Other scripts stay opaque.
NPM_RUN_SCRIPTS = frozenset({"lint", "typecheck", "build"})
NPM_ARGUMENT_SEPARATOR = "--"
MAX_PACKAGE_MANIFEST_BYTES = 1024 * 1024


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


def _regular_project_file(project_dir: str, relative: str) -> str:
    """Return the path of a regular, non-symlink file directly under the project, or ""."""
    path = os.path.join(os.path.realpath(project_dir), relative)
    try:
        details = os.lstat(path)
    except OSError:
        return ""
    return path if stat.S_ISREG(details.st_mode) else ""


def _package_scripts(project_dir: str):
    """Return the scripts object from a bounded package.json, or None when unusable.

    A manifest without a `scripts` key yields an empty dict, so `npm ci` still
    qualifies. A missing, oversized, symlinked, or malformed manifest yields None.
    """
    path = _regular_project_file(project_dir, NPM_MANIFEST)
    if not path or os.path.getsize(path) > MAX_PACKAGE_MANIFEST_BYTES:
        return None
    try:
        with open(path, encoding="utf-8") as manifest_file:
            manifest = json.loads(manifest_file.read(MAX_PACKAGE_MANIFEST_BYTES + 1))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(manifest, dict):
        return None
    scripts = manifest.get("scripts", {})
    return scripts if isinstance(scripts, dict) else None


def _defines_script(scripts: dict, name: str) -> bool:
    """Return whether package.json defines one script as a command string."""
    return isinstance(scripts.get(name), str)


def _test_paths_exist(arguments: list, project_dir: str) -> bool:
    """Accept no arguments, or `--` followed by existing files inside the project."""
    if not arguments:
        return True
    if arguments[0] != NPM_ARGUMENT_SEPARATOR or len(arguments) < 2:
        return False
    for argument in arguments[1:]:
        if argument.startswith("-"):
            return False
        path = core.resolved_under(project_dir, argument)
        if path is None or not os.path.isfile(path):
            return False
    return True


def _npm_workflow(tokens: list, project_dir: str) -> bool:
    """Recognize the fixed npm workflows a repository declares in package.json."""
    scripts = _package_scripts(project_dir)
    if scripts is None:
        return False
    if tokens[1:] == ["ci"]:
        return any(_regular_project_file(project_dir, name) for name in NPM_LOCKFILES)
    if tokens[1] == NPM_TEST_SCRIPT:
        return _defines_script(scripts, NPM_TEST_SCRIPT) and _test_paths_exist(tokens[2:], project_dir)
    if len(tokens) == 3 and tokens[1] == "run" and tokens[2] in NPM_RUN_SCRIPTS:
        return _defines_script(scripts, tokens[2])
    return False


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
    if tokens[0] == NPM_PROGRAM:
        return _npm_workflow(tokens, project_dir)
    return False


def read_only_workflow(command: str, project_dir: str) -> bool:
    """Return whether a consent-routed workflow only inspects the repository."""
    if not workflow_needs_consent(command, project_dir):
        return False
    tokens, _complete = bash_parser._tokenize_line(command)
    # npm ci, test, and build write node_modules, caches, and outputs.
    if tokens[0] == NPM_PROGRAM:
        return False
    if tokens[0] == "rg" or tokens[1:3] == ["-m", "unittest"]:
        return True
    return tuple(tokens[2:]) in READ_ONLY_WORKFLOW_ARGUMENTS.get(tokens[1], ())
