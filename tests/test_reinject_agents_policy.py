#!/usr/bin/env python3
"""Tests for complete AGENTS.md lifecycle reinjection."""
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = REPO_ROOT / "hooks" / "reinject_agents_policy.py"
POLICY_PATH = REPO_ROOT / "AGENTS.md"
CLAUDE_SETTINGS = REPO_ROOT / ".claude" / "settings.json"
CODEX_HOOKS = REPO_ROOT / ".codex" / "hooks.json"
GEMINI_SETTINGS = REPO_ROOT / ".gemini" / "settings.json"
ANTIGRAVITY_HOOKS = REPO_ROOT / ".agents" / "hooks.json"


def load_hook_module():
    """Import the lifecycle hook from its repository path."""
    spec = importlib.util.spec_from_file_location("reinject_agents_policy", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_hook(client: str, payload: dict, *arguments: str) -> subprocess.CompletedProcess:
    """Run one client adapter with trusted project-root variables."""
    environment = dict(os.environ)
    environment["CLAUDE_PROJECT_DIR"] = str(REPO_ROOT)
    environment["GEMINI_PROJECT_DIR"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(HOOK_PATH), "--client", client, *arguments],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )


class PolicyContentTest(unittest.TestCase):
    """Every adapter receives the complete canonical policy."""

    @classmethod
    def setUpClass(cls):
        cls.hook = load_hook_module()
        cls.policy = POLICY_PATH.read_text(encoding="utf-8")

    def test_claude_chunks_reconstruct_exact_policy(self):
        chunks = self.hook.split_policy(self.policy, self.hook.CLAUDE_CHUNK_COUNT)
        self.assertEqual("".join(chunks), self.policy)
        self.assertTrue(all(len(chunk) <= self.hook.MAX_CHUNK_CHARS for chunk in chunks))

    def test_codex_receives_complete_policy(self):
        payload = {"hook_event_name": "SessionStart", "cwd": str(REPO_ROOT)}
        result = run_hook("codex", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(context.endswith(self.policy))

    def test_gemini_preserves_request_and_adds_policy(self):
        payload = {
            "hook_event_name": "BeforeModel",
            "cwd": str(REPO_ROOT),
            "llm_request": {
                "model": "gemini-test",
                "messages": [{"role": "user", "content": "hello"}],
                "config": {"temperature": 0},
            },
        }
        result = run_hook("gemini", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        request = json.loads(result.stdout)["hookSpecificOutput"]["llm_request"]
        self.assertEqual(request["messages"][1]["content"], "hello")
        self.assertTrue(request["messages"][0]["content"].endswith(self.policy))

    def test_antigravity_receives_ephemeral_policy(self):
        payload = {
            "conversationId": "test-conversation",
            "workspacePaths": [str(REPO_ROOT)],
            "invocationNum": 0,
        }
        result = run_hook("antigravity", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        message = json.loads(result.stdout)["injectSteps"][0]["ephemeralMessage"]
        self.assertTrue(message.endswith(self.policy))


class LifecycleWiringTest(unittest.TestCase):
    """Committed client settings must activate every lifecycle adapter."""

    def test_claude_registers_compact_and_subagent_chunks(self):
        settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
        starts = settings["hooks"]["SessionStart"]
        self.assertIn("compact", starts[0]["matcher"])
        subagents = settings["hooks"]["SubagentStart"]
        commands = [hook for group in subagents for hook in group["hooks"]]
        self.assertEqual(len(commands), load_hook_module().CLAUDE_CHUNK_COUNT)

    def test_codex_disables_context_spilling(self):
        settings = json.loads(CODEX_HOOKS.read_text(encoding="utf-8"))
        starts = settings["hooks"]["SessionStart"][0]["hooks"]
        self.assertEqual(starts[0]["additionalContextLimit"], 0)
        self.assertIn("SubagentStart", settings["hooks"])

    def test_gemini_registers_before_every_model(self):
        settings = json.loads(GEMINI_SETTINGS.read_text(encoding="utf-8"))
        self.assertIn("BeforeModel", settings["hooks"])
        self.assertIn("BeforeTool", settings["hooks"])

    def test_antigravity_registers_every_invocation(self):
        settings = json.loads(ANTIGRAVITY_HOOKS.read_text(encoding="utf-8"))
        policy = settings["agents-policy"]
        self.assertIn("PreInvocation", policy)
        self.assertIn("PreToolUse", policy)


if __name__ == "__main__":
    unittest.main()
