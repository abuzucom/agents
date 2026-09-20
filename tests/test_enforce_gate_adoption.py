#!/usr/bin/env python3
"""Test the complete-gate runtime enforcement hook."""
import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = REPOSITORY_ROOT / "hooks" / "enforce_gate_adoption.py"


def load_hook():
    """Load the hook module from its checked-in path."""
    spec = importlib.util.spec_from_file_location("enforce_gate_adoption", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GateAdoptionHookTest(unittest.TestCase):
    """The runtime gate permits only bounded recovery after a failure."""

    def setUp(self) -> None:
        self.hook = load_hook()

    def run_hook(self, payload: dict, failure: str) -> tuple[int, str]:
        """Run one Claude payload and return the result plus stderr."""
        stderr = io.StringIO()
        with patch.object(sys, "argv", [str(HOOK_PATH), "--client", "claude"]):
            with patch.object(self.hook.core, "read_payload", return_value=payload):
                with patch.object(self.hook, "_check_complete_set", return_value=failure):
                    with contextlib.redirect_stderr(stderr):
                        result = self.hook.main()
        return result, stderr.getvalue()

    def test_complete_set_allows_ordinary_tool(self) -> None:
        result, output = self.run_hook(
            {"tool_name": "Bash", "tool_input": {"command": "git status"}},
            "",
        )
        self.assertEqual(result, 0, output)

    def test_incomplete_set_allows_fixed_verifier(self) -> None:
        result, output = self.run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "python scripts/check_gate_adoption.py"},
            },
            "codex registration is absent",
        )
        self.assertEqual(result, 0, output)

    def test_incomplete_set_allows_staged_transaction(self) -> None:
        result, output = self.run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": (
                        "python scripts/complete_gate_adoption.py --candidate "
                        ".gate-staging/release-2.3.0"
                    ),
                },
            },
            "codex registration is absent",
        )
        self.assertEqual(result, 0, output)

    def test_incomplete_set_denies_unbounded_transaction(self) -> None:
        result, output = self.run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "python scripts/complete_gate_adoption.py --candidate C:/tmp",
                },
            },
            "codex registration is absent",
        )
        self.assertEqual(result, 2)
        self.assertIn("codex registration is absent", output)

    def test_incomplete_set_denies_ordinary_tool(self) -> None:
        result, output = self.run_hook(
            {"tool_name": "Bash", "tool_input": {"command": "git status"}},
            "codex registration is absent",
        )
        self.assertEqual(result, 2)
        self.assertIn("codex registration is absent", output)


if __name__ == "__main__":
    unittest.main()
