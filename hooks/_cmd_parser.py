#!/usr/bin/env python3
"""Parse CMD command boundaries without executing command text."""
from dataclasses import dataclass


MAX_COMMAND_CHARACTERS = 65536
COMMAND_SEPARATORS = frozenset({"&", "|", "(", ")", "\n", "\r"})


@dataclass(frozen=True)
class CmdParseResult:
    """Store one exclusive parser state and its complete command segments."""

    status: str
    segments: tuple[tuple[str, ...], ...] = ()


def contains_dynamic_expansion(command_text: str) -> bool:
    """Return whether CMD expansion can change command structure."""
    escaped = False
    percent_open = False
    exclamation_open = False
    for current_character in command_text:
        if escaped:
            escaped = False
            continue
        if current_character == "^":
            escaped = True
            continue
        if current_character == "%":
            if percent_open:
                return True
            percent_open = True
            continue
        if current_character == "!":
            if exclamation_open:
                return True
            exclamation_open = True
    return percent_open or exclamation_open


def append_token(
    token_characters: list[str],
    command_tokens: list[str],
) -> None:
    """Append one completed token and clear its character buffer."""
    if not token_characters:
        return
    command_tokens.append("".join(token_characters))
    token_characters.clear()


def append_segment(
    command_tokens: list[str],
    command_segments: list[tuple[str, ...]],
) -> None:
    """Append one nonempty command segment and clear its token buffer."""
    if not command_tokens:
        return
    command_segments.append(tuple(command_tokens))
    command_tokens.clear()


def parse_cmd_command(command_text: str) -> CmdParseResult:
    """Return bounded CMD segments or one fail-closed parser state."""
    if not isinstance(command_text, str):
        return CmdParseResult("malformed")
    if len(command_text) > MAX_COMMAND_CHARACTERS:
        return CmdParseResult("input_too_large")
    if not command_text.strip():
        return CmdParseResult("empty")
    if contains_dynamic_expansion(command_text):
        return CmdParseResult("dynamic")
    return scan_cmd_characters(command_text)


def scan_cmd_characters(command_text: str) -> CmdParseResult:
    """Scan CMD quoting, escaping, tokens, and command separators once."""
    command_segments: list[tuple[str, ...]] = []
    command_tokens: list[str] = []
    token_characters: list[str] = []
    inside_quotes = False
    escaped = False
    for current_character in command_text:
        if escaped:
            token_characters.append(current_character)
            escaped = False
            continue
        if current_character == "^":
            escaped = True
            continue
        if current_character == '"':
            inside_quotes = not inside_quotes
            continue
        if not inside_quotes and current_character in COMMAND_SEPARATORS:
            append_token(token_characters, command_tokens)
            append_segment(command_tokens, command_segments)
            continue
        if not inside_quotes and current_character.isspace():
            append_token(token_characters, command_tokens)
            continue
        token_characters.append(current_character)
    if escaped or inside_quotes:
        return CmdParseResult("malformed")
    append_token(token_characters, command_tokens)
    append_segment(command_tokens, command_segments)
    if not command_segments:
        return CmdParseResult("empty")
    return CmdParseResult("complete", tuple(command_segments))
