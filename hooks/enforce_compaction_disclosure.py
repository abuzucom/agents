#!/usr/bin/env python3
"""Enforce compaction disclosure and execution containment across all clients."""
import argparse
import hashlib
import json
import os
import stat
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import _gate_core as core
except ImportError as error:  # pragma: no cover
    print(f"shared gate core import failed ({error})", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

try:
    import check_compaction_deception as deception_checker
except ImportError:  # pragma: no cover
    deception_checker = None

GATE = "enforce_compaction_disclosure.py"
STATE_FILE_NAME = "compaction_pending.json"
MAX_GIT_POINTER_BYTES = 4096
FORBIDDEN_DEFERRALS = (
    "session transcript",
    "saved to transcript",
    "recorded in transcript",
    "logged to transcript",
    "in the transcript",
)


def _read_regular(path: str, limit: int) -> str:
    """Return bounded UTF-8 content from one regular non-symlink file."""
    details = os.lstat(path)
    if not stat.S_ISREG(details.st_mode) or details.st_size > limit:
        raise OSError("metadata is not a bounded regular file")
    with open(path, encoding="utf-8") as handle:
        return handle.read(limit + 1)


def _git_directory(project_dir: str) -> str:
    """Return the Git administration directory without invoking Git."""
    dot_git = os.path.join(os.path.realpath(project_dir), ".git")
    if os.path.isdir(dot_git) and not os.path.islink(dot_git):
        return os.path.realpath(dot_git)
    if not os.path.exists(dot_git):
        raise OSError("repository .git directory is missing")
    pointer = _read_regular(dot_git, MAX_GIT_POINTER_BYTES).strip()
    marker, separator, raw_path = pointer.partition(":")
    if marker.lower() != "gitdir" or not separator or not raw_path.strip():
        raise OSError("repository gitdir pointer has invalid syntax")
    target = os.path.realpath(os.path.join(os.path.dirname(dot_git), raw_path.strip()))
    if not os.path.isdir(target):
        raise OSError("repository gitdir target is not a directory")
    return target


RECOVERY_TOOLS = frozenset({
    "view_file",
    "list_dir",
    "find_by_name",
    "grep_search",
    "read_resource",
    "list_resources",
})


def _is_staging_path(target: str) -> bool:
    """Return True if target resolves below .gate-staging/."""
    try:
        resolved = os.path.realpath(target)
        root = os.path.realpath(os.getcwd())
        staging = os.path.join(root, ".gate-staging")
        return os.path.commonpath([staging, resolved]) == staging
    except (OSError, ValueError):
        return False


def _is_recovery_operation(payload: dict) -> bool:
    """Return True if payload specifies a bounded read-only or staging recovery operation."""
    tool_name = payload.get("tool_name") or payload.get("toolCall", {}).get("name", "")
    if tool_name in RECOVERY_TOOLS:
        return True
    tool_input = payload.get("tool_input") or payload.get("toolCall", {}).get("input", {})
    if isinstance(tool_input, dict):
        target_file = tool_input.get("TargetFile") or tool_input.get("file_path", "")
        if target_file and _is_staging_path(target_file):
            return True
        cmd = tool_input.get("CommandLine") or tool_input.get("command", "")
        if cmd:
            normalized_cmd = cmd.strip()
            if "read_git_state.py" in normalized_cmd or normalized_cmd == "git status --short":
                return True
    return False


def _state_file_path(project_dir: Optional[str] = None) -> str:
    """Return the absolute path to the universal compaction lock file."""
    if project_dir is not None:
        base = project_dir
    else:
        cwd = os.getcwd()
        if os.path.exists(os.path.join(cwd, ".git")):
            base = cwd
        else:
            base = str(core.policy_root())
    git_dir = _git_directory(base)
    return os.path.join(git_dir, STATE_FILE_NAME)


def _deny(client: str, reason: str) -> int:
    """Emit the native deny response for one supported client."""
    message = f"blocked by hooks/{GATE}: {reason}"
    if client in ("gemini", "antigravity"):
        print(json.dumps({"decision": "deny", "reason": message}))
        return 0
    return core.emit(GATE, "deny", reason)


def _handle_session_start(payload: dict, client: str) -> int:
    """Record compaction state lock on incoming compaction events."""
    source = payload.get("source")
    is_compact = source == "compact" or payload.get("hook_event_name") == "compact"
    if not is_compact:
        return 0
    compaction_text = (
        payload.get("compaction_text")
        or payload.get("summary")
        or payload.get("content")
        or ""
    )
    findings = []
    if deception_checker and compaction_text:
        detected = deception_checker.scan_compaction_text(compaction_text)
        findings = [
            {"category": f.category, "pattern": f.pattern, "match": f.match_text}
            for f in detected
        ]
    state = {
        "pending": True,
        "source": source,
        "client": client,
        "digest": hashlib.sha256(compaction_text.encode("utf-8")).hexdigest(),
        "findings": findings,
    }
    state_path = _state_file_path()
    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
    return 0


def _validate_assistant_message(content: str) -> bool:
    """Return True if message discloses compaction text without deferral."""
    lowered = content.lower()
    for deferral in FORBIDDEN_DEFERRALS:
        if deferral in lowered:
            return False
    return True


def _validate_transcript(transcript_path: Optional[str]) -> bool:
    """Return True if the transcript contains a valid non-deferred assistant disclosure."""
    if not isinstance(transcript_path, str) or not transcript_path or not os.path.isfile(transcript_path):
        return False
    try:
        with open(transcript_path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            role = record.get("role") or record.get("source")
            if role == "assistant":
                content = record.get("content", "")
                if isinstance(content, list):
                    text_parts = [
                        b.get("text", "") for b in content
                        if isinstance(b, dict) and b.get("type") == "text"
                    ]
                    content = "\n".join(text_parts)
                if isinstance(content, str) and content and _validate_assistant_message(content):
                    return True
                return False
    except (OSError, UnicodeError, json.JSONDecodeError):
        pass
    return False


def _handle_pre_tool_use(client: str, payload: dict) -> int:
    """Deny non-recovery tool calls while compaction disclosure is pending."""
    if _is_recovery_operation(payload):
        return 0
    state_path = _state_file_path()
    if not os.path.isfile(state_path):
        return 0
    transcript_path = payload.get("transcript_path")
    if transcript_path and _validate_transcript(transcript_path):
        try:
            os.remove(state_path)
        except OSError:
            pass
        return 0
    reason = (
        "compaction disclosure pending. Emit the complete unredacted compaction "
        "text directly to the active human, stop, and obtain plan approval before executing tools."
    )
    return _deny(client, reason)


def _handle_stop(payload: dict) -> int:
    """Verify that the assistant emitted disclosure before stopping."""
    state_path = _state_file_path()
    if not os.path.isfile(state_path):
        return 0
    transcript_path = payload.get("transcript_path")
    if transcript_path and _validate_transcript(transcript_path):
        try:
            os.remove(state_path)
        except OSError:
            pass
        return 0
    print(
        f"blocked by hooks/{GATE}: compaction disclosure defective. "
        "The agent must emit the complete unredacted compaction text directly "
        "to the active human. Defective transcript deferrals are prohibited.",
        file=sys.stderr,
    )
    return 2


def run_hook(args: argparse.Namespace, payload: dict) -> int:
    """Route lifecycle events across supported client schemas."""
    event = payload.get("hook_event_name")
    if not event:
        if "toolCall" in payload or "tool_name" in payload:
            event = "PreToolUse"
        else:
            event = "SessionStart"
    if event in ("SessionStart", "compact"):
        return _handle_session_start(payload, args.client)
    if event in ("PreToolUse", "BeforeTool"):
        return _handle_pre_tool_use(args.client, payload)
    if event in ("Stop", "SubagentStop"):
        return _handle_stop(payload)
    return 0


def main() -> int:
    """Parse client argument and dispatch lifecycle payload."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--client",
        required=True,
        choices=("claude", "codex", "gemini", "antigravity"),
    )
    args = parser.parse_args()
    try:
        payload = core.read_payload(empty_is_session_start=True)
        if payload is None:
            payload = {}
        return run_hook(args, payload)
    except (OSError, ValueError) as error:
        print(f"blocked by hooks/{GATE}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
