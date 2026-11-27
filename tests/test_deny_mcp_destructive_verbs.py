#!/usr/bin/env python3
"""Unlisted MCP actions named with a destructive verb deny on every client."""
import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "hooks"))
import deny_mcp_github_writes as gate

DESTRUCTIVE_VERBS = ("remove", "destroy", "wipe", "purge", "drop", "erase", "revoke")
TARGET = "repository"


def build_payloads(action: str) -> dict:
    """Return one MCP payload per client for `action` on the GitHub server."""
    return {
        "claude": {"tool_name": f"mcp__github__{action}", "tool_input": {}},
        "codex": {"tool_name": f"mcp__github__{action}", "tool_input": {}},
        "gemini": {"tool_name": f"mcp_github_{action}", "tool_input": {}},
        "antigravity": {"toolCall": {"name": "call_mcp_tool", "args": {
            "ServerName": "github", "ToolName": action, "Arguments": {}}}},
    }


class DestructiveVerbTest(unittest.TestCase):
    """Each destructive verb prefix denies, whatever its letter case."""

    def test_destructive_verbs_deny(self) -> None:
        for verb in DESTRUCTIVE_VERBS:
            for action in (f"{verb}_{TARGET}", f"{verb.upper()}_{TARGET}"):
                for client, payload in build_payloads(action).items():
                    with self.subTest(client=client, action=action):
                        decision, _ = gate.write_decision(payload, client)
                        self.assertEqual(decision, "deny")

    def test_known_asked_delete_stays_ask(self) -> None:
        for client, payload in build_payloads("delete_file").items():
            with self.subTest(client=client):
                self.assertEqual(gate.write_decision(payload, client)[0], "ask")


if __name__ == "__main__":
    unittest.main()
