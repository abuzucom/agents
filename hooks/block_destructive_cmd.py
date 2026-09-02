#!/usr/bin/env python3
"""Gate CMD commands through behavior-based operation policies."""
import json
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import _cmd_parser as cmd_parser
    import _gate_core as core
except ImportError as error:  # pragma: no cover
    failure_reason = f"shared CMD parser or core import failed ({error})"
    print(failure_reason, file=sys.stderr)
    sys.exit(2)


GATE = "block_destructive_cmd.py"
CMD_TOOL_NAMES = frozenset({"Cmd", "CMD", "CommandPrompt"})
STORAGE_DESTRUCTION_PROGRAMS = frozenset({"diskpart", "format"})
SENSITIVE_DISCOVERY_PROGRAMS = frozenset({
    "arp",
    "driverquery",
    "getmac",
    "ipconfig",
    "netstat",
    "route",
    "systeminfo",
    "tasklist",
    "whoami",
})
REMOTE_EXECUTION_PROGRAMS = frozenset({"psexec", "winrs"})
SCRIPT_SUFFIXES = (".bat", ".cmd")
INTERPRETER_PROGRAMS = frozenset({
    "bash",
    "cmd",
    "csh",
    "dash",
    "fish",
    "ksh",
    "powershell",
    "pwsh",
    "sh",
    "tcsh",
    "zsh",
})


def normalize_cmd_program(program_token: str) -> str:
    """Return a case-insensitive CMD executable name."""
    program_name = os.path.basename(program_token).casefold()
    return program_name.removesuffix(".exe")


def classify_curl_transfer(arguments: tuple[str, ...]) -> tuple[str, str]:
    """Classify curl transfer direction from behavior flags."""
    upload_long_options = (
        "--upload-file",
        "--form",
        "--data",
        "--data-binary",
        "--json",
    )
    for argument in arguments:
        if argument in ("-T", "-F", "-d"):
            return "deny", "curl uploads local data to a remote endpoint"
        lowered_argument = argument.casefold()
        for option_name in upload_long_options:
            if lowered_argument == option_name:
                return "deny", "curl uploads local data to a remote endpoint"
            if lowered_argument.startswith(option_name + "="):
                return "deny", "curl uploads local data to a remote endpoint"
    return "ask", "curl accesses an external network endpoint"


def classify_interpreter(
    program_name: str,
    arguments: tuple[str, ...],
) -> tuple[str, str]:
    """Classify shell transitions, command strings, and fixed scripts."""
    lowered_arguments = tuple(argument.casefold() for argument in arguments)
    payload_flags = frozenset({"/c", "/k", "-c", "-command", "-encodedcommand"})
    if any(argument in payload_flags for argument in lowered_arguments):
        return "deny", f"{program_name} executes a command-string payload"
    return "ask", f"{program_name} changes the active command interpreter"


def classify_service_or_task(
    program_name: str,
    arguments: tuple[str, ...],
) -> tuple[str, str]:
    """Classify service and scheduled-task persistence operations."""
    lowered_arguments = tuple(argument.casefold() for argument in arguments)
    if program_name == "sc":
        mutating_operations = {"config", "create", "delete", "failure", "start"}
        if lowered_arguments and lowered_arguments[0] in mutating_operations:
            return "deny", "sc changes persistent service execution"
        return "ask", "sc reads service configuration"
    mutating_flags = {"/change", "/create", "/delete", "/end", "/run"}
    if any(argument in mutating_flags for argument in lowered_arguments):
        return "deny", "schtasks changes persistence or starts scheduled code"
    return "ask", "schtasks reads scheduled-task state"


def classify_cmd_segment(command_tokens: tuple[str, ...]) -> tuple[str, str]:
    """Return the strongest policy verdict for one CMD command segment."""
    if not command_tokens:
        return "", ""
    program_token = command_tokens[0]
    program_name = normalize_cmd_program(program_token)
    arguments = command_tokens[1:]
    if program_name in STORAGE_DESTRUCTION_PROGRAMS:
        return "deny", f"{program_name} partitions or formats storage"
    if program_name in ("del", "erase", "rd", "rmdir"):
        return core.cmd_delete_verdict(program_name, list(arguments))
    if program_name in ("sc", "schtasks"):
        return classify_service_or_task(program_name, arguments)
    if program_name in REMOTE_EXECUTION_PROGRAMS:
        return "deny", f"{program_name} enables remote command execution"
    if program_name in SENSITIVE_DISCOVERY_PROGRAMS:
        return "ask", f"{program_name} enumerates sensitive host state"
    if program_name == "curl":
        return classify_curl_transfer(arguments)
    if program_name in INTERPRETER_PROGRAMS:
        return classify_interpreter(program_name, arguments)
    if program_name in ("call", "for"):
        return "deny", f"{program_name} can hide nested command execution"
    if program_token.casefold().endswith(SCRIPT_SUFFIXES):
        return "ask", "a fixed local batch script executes code"
    return "", ""


def classify_cmd_command(command_text: str) -> tuple[str, str]:
    """Return the strongest verdict across one parsed CMD command."""
    parse_result = cmd_parser.parse_cmd_command(command_text)
    if parse_result.status == "empty":
        return "", ""
    if parse_result.status != "complete":
        return "deny", f"CMD command parsing stopped at {parse_result.status} input"
    strongest_verdict = ("", "")
    for command_segment in parse_result.segments:
        segment_verdict = classify_cmd_segment(command_segment)
        strongest_verdict = core.strongest(strongest_verdict, segment_verdict)
        if strongest_verdict[0] == "deny":
            return strongest_verdict
    return strongest_verdict


def main() -> int:
    """Read one hook payload and emit its CMD policy decision."""
    payload = core.read_payload()
    if payload is None:
        return core.emit(
            GATE,
            "deny",
            "the hook payload cannot be read, so the gate cannot clear it",
        )
    if payload.get("tool_name") not in CMD_TOOL_NAMES:
        return 0
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return core.emit(GATE, "deny", "the CMD tool input is malformed")
    command_text = core.require_str(tool_input.get("command", ""))
    if command_text is None:
        return core.emit(GATE, "deny", "the CMD command field is not a string")
    decision, decision_reason = classify_cmd_command(command_text)
    if not decision:
        return 0
    return core.decide(GATE, payload, decision, decision_reason)


if __name__ == "__main__":
    sys.exit(main())
