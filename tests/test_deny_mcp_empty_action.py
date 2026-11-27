#!/usr/bin/env python3
"""An `mcp__` name with an empty action denies instead of passing unchecked."""
import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "hooks"))
import deny_mcp_github_writes as gate

PREFIXED_CLIENTS = ("claude", "codex")
EMPTY_ACTION_NAMES = ("mcp__github__", "mcp__x__")
# Names without the `mcp__` prefix, including Gemini's flat `mcp_` form,
# are not Claude or Codex MCP calls.
NON_MCP_NAMES = ("Bash", "Read", "mcp_github_x")


class EmptyActionTest(unittest.TestCase):
    """The Claude and Codex reader treats a prefixed empty action as malformed."""

    def test_empty_action_denies(self) -> None:
        for client in PREFIXED_CLIENTS:
            for name in EMPTY_ACTION_NAMES:
                with self.subTest(client=client, name=name):
                    payload = {"tool_name": name, "tool_input": {}}
                    decision, reason = gate.write_decision(payload, client)
                    self.assertEqual((decision, reason), ("deny", gate.MALFORMED_REASON))

    def test_non_mcp_names_pass(self) -> None:
        for client in PREFIXED_CLIENTS:
            for name in NON_MCP_NAMES:
                with self.subTest(client=client, name=name):
                    payload = {"tool_name": name, "tool_input": {}}
                    self.assertEqual(gate.write_decision(payload, client), ("", ""))


if __name__ == "__main__":
    unittest.main()
