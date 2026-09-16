"""Test the shared Cloudflare Pages deployment allowance."""
import unittest
import json
import subprocess
import sys
from pathlib import Path

from hooks import _gate_core


class CloudflarePagesPolicyTest(unittest.TestCase):
    """Verify the allowlist and its denial boundaries."""

    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]

    def verdict(self, *arguments: str) -> tuple:
        return _gate_core.cloudflare_pages_verdict(
            "wrangler", list(arguments), str(self.root))

    def hook_verdict(self, tool_name: str, command: str) -> tuple:
        """Run one real shell gate and return its exit code and decision."""
        hook_name = {
            "Bash": "block_destructive_bash.py",
            "PowerShell": "block_destructive_powershell.py",
            "Cmd": "block_destructive_cmd.py",
        }[tool_name]
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "permission_mode": "default",
            "cwd": str(self.root),
            "tool_input": {"command": command},
        }
        result = subprocess.run(
            [sys.executable, str(self.root / "hooks" / hook_name)],
            input=json.dumps(payload),
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        decision = ""
        if result.stdout.strip():
            decision = json.loads(result.stdout)["hookSpecificOutput"][
                "permissionDecision"
            ]
        return result.returncode, decision

    def test_real_gates_reach_pages_policy(self) -> None:
        """Exercise the shared Pages policy through every shell gate."""
        for tool_name in ("Bash", "PowerShell", "Cmd"):
            with self.subTest(tool_name=tool_name):
                allowed = self.hook_verdict(
                    tool_name,
                    "wrangler pages deploy hooks --project-name site",
                )
                denied = self.hook_verdict(tool_name, "wrangler deploy hooks")
                self.assertEqual(allowed, (0, ""))
                self.assertEqual(denied, (2, "deny"))

    def test_allows_named_pages_deployment(self) -> None:
        self.assertEqual(
            self.verdict("pages", "deploy", "hooks", "--project-name", "time-chime"),
            ("", ""),
        )

    def test_allows_preview_branch(self) -> None:
        self.assertEqual(
            self.verdict("pages", "deploy", "hooks", "--project-name=site",
                         "--branch", "preview"),
            ("", ""),
        )

    def test_rejects_other_wrangler_commands(self) -> None:
        self.assertEqual(self.verdict("deploy", "dist" )[0], "deny")
        self.assertEqual(self.verdict("pages", "project", "list")[0], "deny")
        self.assertEqual(self.verdict("pages", "secret", "put", "KEY")[0], "deny")

    def test_rejects_missing_or_extra_options(self) -> None:
        self.assertEqual(self.verdict("pages", "deploy", "hooks")[0], "deny")
        self.assertEqual(
            self.verdict("pages", "deploy", "hooks", "--project-name", "site",
                         "--commit-dirty")[0], "deny")

    def test_rejects_paths_outside_workspace(self) -> None:
        self.assertEqual(
            self.verdict("pages", "deploy", "..", "--project-name", "site")[0],
            "deny",
        )

    def test_rejects_ambiguous_values(self) -> None:
        self.assertEqual(
            self.verdict("pages", "deploy", "hooks", "--project-name", "$NAME")[0],
            "deny",
        )


if __name__ == "__main__":
    unittest.main()
