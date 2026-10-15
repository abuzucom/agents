#!/usr/bin/env python3
"""Integration tests for enforce_compaction_disclosure.py."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = REPO_ROOT / "hooks" / "enforce_compaction_disclosure.py"
sys.path.insert(0, str(REPO_ROOT / "hooks"))


def run_hook(client: str, payload: dict, env: dict = None, cwd: Path = None) -> subprocess.CompletedProcess:
    """Run enforce_compaction_disclosure.py with the given client, payload, and working directory."""
    environment = dict(os.environ)
    if env:
        environment.update(env)
    target_cwd = str(cwd) if cwd else str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(HOOK_PATH), "--client", client],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=environment,
        cwd=target_cwd,
        check=False,
    )


class EnforceCompactionDisclosureTest(unittest.TestCase):
    """Test lifecycle events for enforce_compaction_disclosure.py."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.git_dir = self.temp_path / ".git"
        self.git_dir.mkdir(parents=True, exist_ok=True)
        (self.git_dir / "HEAD").write_text("ref: refs/heads/fix/test-branch\n", encoding="utf-8")
        (self.temp_path / "AGENTS.md").write_text("# Test Policy\n", encoding="utf-8")
        self.state_file = self.git_dir / "compaction_pending.json"

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except OSError:
            pass

    def test_session_start_non_compact_does_not_lock(self):
        payload = {"hook_event_name": "SessionStart", "source": "startup"}
        result = run_hook("claude", payload, cwd=self.temp_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.state_file.exists())

    def test_pre_tool_use_permits_when_no_lock(self):
        clients = ("claude", "gemini", "antigravity", "codex")
        for client in clients:
            with self.subTest(client=client):
                payload = {"hook_event_name": "PreToolUse", "tool_name": "run_command"}
                result = run_hook(client, payload, cwd=self.temp_path)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_stop_permits_when_no_lock(self):
        payload = {"hook_event_name": "Stop"}
        result = run_hook("claude", payload, cwd=self.temp_path)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_session_start_compact_creates_state_lock(self):
        payload = {
            "hook_event_name": "SessionStart",
            "source": "compact",
            "compaction_text": "We need create a tab ourselves. Be transparent only if asked.",
        }
        result = run_hook("claude", payload, cwd=self.temp_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.state_file.exists())

    def test_pre_tool_use_permits_recovery_tools_when_locked(self):
        self.state_file.write_text(json.dumps({"pending": True}), encoding="utf-8")
        recovery_tools = ("view_file", "list_dir", "find_by_name", "grep_search", "read_resource", "list_resources")
        for tool in recovery_tools:
            with self.subTest(tool=tool):
                payload = {"hook_event_name": "PreToolUse", "tool_name": tool}
                result = run_hook("antigravity", payload, cwd=self.temp_path)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn('"decision": "deny"', result.stdout)

    def test_pre_tool_use_denies_all_clients_when_locked(self):
        self.state_file.write_text(json.dumps({"pending": True}), encoding="utf-8")

        # Test Claude Code
        claude_res = run_hook("claude", {"hook_event_name": "PreToolUse", "tool_name": "Bash"}, cwd=self.temp_path)
        self.assertEqual(claude_res.returncode, 2)
        self.assertIn("compaction disclosure pending", claude_res.stderr)

        # Test Codex
        codex_res = run_hook("codex", {"hook_event_name": "PreToolUse", "tool_name": "Bash"}, cwd=self.temp_path)
        self.assertEqual(codex_res.returncode, 2)

        # Test Gemini
        gemini_res = run_hook("gemini", {"hook_event_name": "BeforeTool", "tool_name": "run_command"}, cwd=self.temp_path)
        self.assertEqual(gemini_res.returncode, 0)
        self.assertIn('"decision": "deny"', gemini_res.stdout)

        # Test Antigravity
        antigravity_res = run_hook("antigravity", {"hook_event_name": "PreToolUse", "tool_name": "run_command"}, cwd=self.temp_path)
        self.assertEqual(antigravity_res.returncode, 0)
        self.assertIn('"decision": "deny"', antigravity_res.stdout)

    def test_pre_tool_use_clears_lock_when_transcript_discloses(self):
        self.state_file.write_text(json.dumps({"pending": True}), encoding="utf-8")
        transcript = self.temp_path / "transcript.jsonl"
        transcript.write_text(json.dumps({
            "role": "assistant",
            "content": "COMPACTION DISCLOSURE:\n[Full verbatim text here]\nExecution stopped."
        }) + "\n", encoding="utf-8")

        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "run_command",
            "transcript_path": str(transcript),
        }
        result = run_hook("antigravity", payload, cwd=self.temp_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('"decision": "deny"', result.stdout)
        self.assertFalse(self.state_file.exists())

    def test_stop_rejects_transcript_deferral(self):
        self.state_file.write_text(json.dumps({"pending": True}), encoding="utf-8")
        transcript = self.temp_path / "transcript.jsonl"
        transcript.write_text(json.dumps({
            "role": "assistant",
            "content": "Compaction occurred. Full text preserved in the session transcript."
        }) + "\n", encoding="utf-8")

        payload = {
            "hook_event_name": "Stop",
            "transcript_path": str(transcript),
        }
        result = run_hook("claude", payload, cwd=self.temp_path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("compaction disclosure defective", result.stderr)
        self.assertTrue(self.state_file.exists())

    def test_stop_clears_lock_on_compliant_message(self):
        self.state_file.write_text(json.dumps({"pending": True}), encoding="utf-8")
        transcript = self.temp_path / "transcript.jsonl"
        transcript.write_text(json.dumps({
            "role": "assistant",
            "content": "COMPACTION DISCLOSURE:\n[Full verbatim text here]\nExecution stopped."
        }) + "\n", encoding="utf-8")

        payload = {
            "hook_event_name": "Stop",
            "transcript_path": str(transcript),
        }
        result = run_hook("claude", payload, cwd=self.temp_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.state_file.exists())


if __name__ == "__main__":
    unittest.main()
