#!/usr/bin/env python3
"""Pin the outcomes that earlier checks deliver for removed hook statements.

Each removed statement sat behind an earlier check that already handled its
input. These cases run the real hook code on those inputs, so a later change
to the earlier check cannot silently drop the outcome.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS = REPO_ROOT / "hooks"
BLOCKING_EXIT_CODE = 2
HOOK_TIMEOUT_SECONDS = 30


def cmd_decision(command: str) -> str:
    """Return allow, ask, or deny from the CMD gate for `command`."""
    payload = {
        "hook_event_name": "PreToolUse",
        "permission_mode": "default",
        "tool_name": "Cmd",
        "tool_input": {"command": command},
    }
    result = subprocess.run(
        [sys.executable, str(HOOKS / "block_destructive_cmd.py")],
        input=json.dumps(payload), cwd=REPO_ROOT, capture_output=True,
        text=True, timeout=HOOK_TIMEOUT_SECONDS, check=False,
    )
    if result.returncode == BLOCKING_EXIT_CODE:
        return "deny"
    if not result.stdout.strip():
        return "allow"
    return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]


def load_gate_adoption_hook():
    """Import hooks/enforce_gate_adoption.py from its file path."""
    spec = importlib.util.spec_from_file_location(
        "enforce_gate_adoption_preempted", HOOKS / "enforce_gate_adoption.py")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HOOKS))
    spec.loader.exec_module(module)
    return module


class CmdStorageDestructionTest(unittest.TestCase):
    """The prohibited-command check denies partition and format programs."""

    def test_diskpart_is_denied(self) -> None:
        self.assertEqual(cmd_decision("diskpart"), "deny")

    def test_format_is_denied(self) -> None:
        self.assertEqual(cmd_decision("format c: /q"), "deny")


class StagingDirectoryWriteTest(unittest.TestCase):
    """Only paths below the staging directory count as staging writes."""

    def test_staging_directory_itself_is_not_a_staging_write(self) -> None:
        hook = load_gate_adoption_hook()
        staging = str(REPO_ROOT / hook.STAGING_DIRECTORY)
        self.assertFalse(hook._staging_write("Write", {"file_path": staging}))

    def test_file_below_staging_directory_is_a_staging_write(self) -> None:
        hook = load_gate_adoption_hook()
        target = str(REPO_ROOT / hook.STAGING_DIRECTORY / "candidate" / "a.py")
        self.assertTrue(hook._staging_write("Write", {"file_path": target}))


class GateFileConsentReasonTest(unittest.TestCase):
    """A write under hooks/ asks with the Rule 22 instructions."""

    def test_hook_file_write_cites_rule_22(self) -> None:
        with tempfile.TemporaryDirectory() as project:
            target = os.path.join(project, "hooks", "new_gate.py")
            payload = {"hook_event_name": "PreToolUse", "permission_mode": "default",
                       "tool_name": "Write",
                       "tool_input": {"file_path": target, "content": "x"}}
            environment = dict(os.environ, CLAUDE_PROJECT_DIR=project)
            result = subprocess.run(
                [sys.executable, str(HOOKS / "require_consent.py")],
                input=json.dumps(payload), env=environment, capture_output=True,
                text=True, timeout=HOOK_TIMEOUT_SECONDS, check=False,
            )
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "ask")
        self.assertIn("Rule 22", output["permissionDecisionReason"])


if __name__ == "__main__":
    unittest.main()
