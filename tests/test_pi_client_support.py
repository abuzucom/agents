#!/usr/bin/env python3
"""The client-aware hooks accept `--client pi` with Claude input and output shapes.

pi reaches these hooks through a project extension that maps pi tool names
to the Claude names and sends a Claude-shaped payload. pi has a native
consent prompt, so an ask stays an ask in an interactive session. Nothing
registers pi in this repository yet. These tests cover the hook side only.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from tests.read_only_branch_support import BLOCKING_EXIT_CODE, BranchFixture, decision

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / "hooks"
CLIENT = "pi"
INVALID_BRANCH = "claude/pi-client-fixture"
RECOVERY_COMMAND = "git branch -m fix/recovered"
HOOK_TIMEOUT_SECONDS = 30
USAGE_ERROR_TEXT = "invalid choice"
UNKNOWN_CLIENT_TEXT = "unknown --client value"
MCP_DELETE = "mcp__github__delete_repository"
MCP_COMMENT = "mcp__github__add_issue_comment"
COMPACTION_SOURCE = "compact"
ADOPTION_HEADER = "MANDATORY AGENTS.md RE-ADOPTION"


def run_hook(name: str, payload: dict) -> subprocess.CompletedProcess:
    """Run one hook with `--client pi` and a JSON payload on stdin."""
    return subprocess.run(
        [sys.executable, str(HOOKS / name), "--client", CLIENT],
        input=json.dumps(payload), cwd=ROOT, capture_output=True, text=True,
        timeout=HOOK_TIMEOUT_SECONDS, check=False)


def tool_payload(tool_name: str, tool_input: dict, mode: str = "default") -> dict:
    """Return one Claude-shaped pre-tool payload."""
    return {"hook_event_name": "PreToolUse", "permission_mode": mode,
            "tool_name": tool_name, "tool_input": tool_input, "cwd": str(ROOT)}


class ClientChoiceTest(unittest.TestCase):
    """Each client-aware hook accepts pi as a client value."""

    def test_gate_hooks_accept_pi(self) -> None:
        payload = tool_payload("Read", {"file_path": str(ROOT / "README.md")})
        for name in ("enforce_gate_adoption.py", "enforce_anti_delegation.py",
                     "deny_mcp_github_writes.py"):
            with self.subTest(hook=name):
                result = run_hook(name, payload)
                self.assertNotIn(USAGE_ERROR_TEXT, result.stderr)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), "")


class McpGateTest(unittest.TestCase):
    """pi MCP names use the `mcp__` prefix and pi asks natively."""

    def test_destructive_mcp_call_denies(self) -> None:
        result = run_hook("deny_mcp_github_writes.py", tool_payload(MCP_DELETE, {}))
        self.assertEqual(result.returncode, BLOCKING_EXIT_CODE)
        self.assertIn("blocked by hooks/deny_mcp_github_writes.py", result.stderr)
        self.assertNotIn(UNKNOWN_CLIENT_TEXT, result.stderr)

    def test_issue_comment_asks_interactively(self) -> None:
        result = run_hook("deny_mcp_github_writes.py", tool_payload(MCP_COMMENT, {}))
        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]
        self.assertEqual(verdict, "ask")

    def test_unattended_comment_denies(self) -> None:
        result = run_hook("deny_mcp_github_writes.py",
                          tool_payload(MCP_COMMENT, {}, mode="dontAsk"))
        self.assertEqual(result.returncode, BLOCKING_EXIT_CODE)
        self.assertIn("No interactive session", result.stderr)


class BranchGateTest(unittest.TestCase):
    """An invalid branch blocks pi tools and asks before the recovery rename."""

    def setUp(self) -> None:
        self.fixture = BranchFixture(self, INVALID_BRANCH)

    def test_invalid_branch_blocks_pi(self) -> None:
        result = self.fixture.shell("git status", client=CLIENT)
        self.assertNotIn(USAGE_ERROR_TEXT, result.stderr)
        self.assertEqual(decision(result, CLIENT), "deny")
        self.assertIn("blocked by hooks/enforce_branch_name.py", result.stderr)

    def test_recovery_rename_asks_interactively(self) -> None:
        result = self.fixture.shell(RECOVERY_COMMAND, client=CLIENT)
        self.assertEqual(decision(result, CLIENT), "ask")

    def test_unattended_recovery_denies(self) -> None:
        result = self.fixture.hook.run("Bash", {"command": RECOVERY_COMMAND},
                                       client=CLIENT, mode="dontAsk")
        self.assertNotIn(USAGE_ERROR_TEXT, result.stderr)
        self.assertEqual(decision(result, CLIENT), "deny")


class ReinjectionTest(unittest.TestCase):
    """pi receives the complete policy as lifecycle context."""

    def test_session_start_carries_policy(self) -> None:
        result = run_hook("reinject_agents_policy.py",
                          {"hook_event_name": "SessionStart", "cwd": str(ROOT)})
        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(context.startswith(ADOPTION_HEADER), context[:80])
        self.assertIn((ROOT / "AGENTS.md").read_text(encoding="utf-8")[:200], context)

    def test_compaction_prepends_directive(self) -> None:
        result = run_hook("reinject_agents_policy.py",
                          {"hook_event_name": "SessionStart", "source": COMPACTION_SOURCE,
                           "cwd": str(ROOT)})
        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(context.startswith("COMPACTION EVENT DETECTED"), context[:80])
        self.assertIn(ADOPTION_HEADER, context)


if __name__ == "__main__":
    unittest.main()
