#!/usr/bin/env python3
"""Parse Bash command boundaries and executable prefixes for hook classifiers."""
import os
import shlex

OPERATOR_CHARS = frozenset("&|;")
GROUPING = frozenset({"(", ")", "\n"})
REDIRECTION_CHARS = frozenset("<>&0123456789")
WRAPPERS = frozenset({
    "sudo", "doas", "env", "time", "nohup", "nice", "command", "xargs",
    "timeout",
})
WRAPPER_VALUE_OPTIONS = {
    "sudo": frozenset({
        "-u", "-g", "-p", "-C", "-h", "-U", "-r", "-t", "--user",
        "--group", "--prompt", "--close-from", "--host", "--role", "--type",
    }),
    "doas": frozenset({"-u", "-C"}),
    "env": frozenset({"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}),
    "xargs": frozenset({
        "-n", "-I", "-L", "-P", "-s", "-d", "-E", "-a", "--max-args",
        "--replace", "--max-procs", "--delimiter", "--arg-file",
    }),
    "nice": frozenset({"-n", "--adjustment"}),
    "timeout": frozenset({"-k", "-s", "--kill-after", "--signal"}),
}


def is_env_assignment(token: str) -> bool:
    """Return True if `token` is a leading shell environment assignment."""
    if token.startswith("-") or "=" not in token:
        return False
    return token.split("=", 1)[0].isidentifier()


def is_redirection(token: str) -> bool:
    """Return True if `token` is a redirection operator."""
    return bool(token) and ("<" in token or ">" in token) and set(token) <= REDIRECTION_CHARS


def redirect_targets(tokens: list) -> list:
    """Return the files a segment redirects into."""
    targets = []
    for index, token in enumerate(tokens):
        if is_redirection(token) and index + 1 < len(tokens):
            targets.append(tokens[index + 1])
        elif ">" in token and not is_redirection(token):
            tail = token.partition(">")[2]
            if tail:
                targets.append(tail)
    return targets


def _env_split_value(token: str) -> tuple:
    """Return an env -S value and whether `token` carries one."""
    if token in ("-S", "--split-string"):
        return "", True
    for prefix in ("-S", "--split-string="):
        if token.startswith(prefix) and len(token) > len(prefix):
            return token[len(prefix):], True
    return "", False


def _expand_env_split(tokens: list, index: int):
    """Return tokens expanded through env -S, or None when not applicable."""
    value, applies = _env_split_value(tokens[index])
    if not applies:
        return None, True
    next_index = index + 1
    if not value:
        if next_index >= len(tokens):
            return [], False
        value = tokens[next_index]
        next_index += 1
    expanded, complete = _tokenize_line(value)
    if not complete or not expanded:
        return [], False
    return expanded + tokens[next_index:], True


def strip_prefixes(tokens: list) -> tuple:
    """Return executable tokens, assignments, and complete prefix parsing."""
    index = 0
    wrapper = ""
    assignments = []
    while index < len(tokens):
        token = tokens[index]
        if is_redirection(token):
            index += 2
            continue
        if is_env_assignment(token):
            assignments.append(token.split("=", 1))
            index += 1
            continue
        name = os.path.basename(token).lower()
        if name in WRAPPERS:
            wrapper = name
            index += 1
            continue
        expanded, complete = _expand_env_split(tokens, index) if wrapper == "env" else (None, True)
        if expanded is not None:
            if not complete:
                return [], assignments, False
            tokens = expanded
            index = 0
            wrapper = ""
            continue
        if wrapper and token.startswith("-"):
            takes_value = ("=" not in token
                           and token in WRAPPER_VALUE_OPTIONS.get(wrapper, frozenset()))
            index += 2 if takes_value else 1
            continue
        break
    return tokens[index:], assignments, True


def _is_separator(token: str) -> bool:
    """Return True if `token` separates commands."""
    return token in GROUPING or (bool(token) and set(token) <= OPERATOR_CHARS)


def _split_segments(tokens: list) -> list:
    """Split a token stream into command segments."""
    segments = [[]]
    for token in tokens:
        if _is_separator(token):
            segments.append([])
        else:
            segments[-1].append(token)
    return [segment for segment in segments if segment]


def _tokenize_line(line: str) -> tuple:
    """Return tokens and whether the whole line parsed."""
    lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    tokens = []
    try:
        for token in lexer:
            tokens.append(token)
    except ValueError:
        return tokens, False
    return tokens, True


def command_segments(command: str) -> tuple:
    """Return parsed segments and whether every line parsed completely."""
    segments = []
    complete = True
    for line in command.splitlines():
        tokens, parsed = _tokenize_line(line)
        segments.extend(_split_segments(tokens))
        complete = complete and parsed
    return segments, complete


def git_write_operation(command: str, resolve_git, cwd: str = "") -> list:
    """Return every effective or ambiguous Git write in `command`."""
    if not isinstance(command, str):
        return []
    contexts = []
    segments, _ = command_segments(command)
    for segment in segments:
        executable, assignments, complete = strip_prefixes(segment)
        if not complete:
            contexts.append({
                "label": "unresolved env -S command",
                "error": "env -S command text could not be inspected",
                "cwd": os.path.realpath(cwd or "."),
                "settings": [],
            })
            continue
        if not executable:
            continue
        program = os.path.basename(executable[0]).lower().removesuffix(".exe")
        if program != "git":
            continue
        context = resolve_git(executable[1:], cwd, assignments)
        if context:
            contexts.append(context)
    return contexts
