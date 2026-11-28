#!/usr/bin/env python3
"""The pi gate chain paths are protected before any pi file lands there.

`broker/` will hold the pi decision broker and `integrations/pi/` the pi
extension. A write to either can switch the pi gates off, so the file
tool gate, the Bash gate, and the pull request label gate treat both like
`hooks/`.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# discover -s tests puts this directory on the path. A direct
# `unittest tests.<module>` run does not.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate_corpus

REPO_ROOT = Path(__file__).resolve().parent.parent
BASH_HOOK = REPO_ROOT / "hooks" / "block_destructive_bash.py"
CONSENT_HOOK = REPO_ROOT / "hooks" / "require_consent.py"
INTEGRITY_CHECKER = REPO_ROOT / "scripts" / "check_gate_pr_integrity.py"
PI_PATHS = ("broker/pi_broker.py", "integrations/pi/agents-gate.ts")


def bash_verdict(command: str) -> str:
    """Return the Bash gate decision for `command`."""
    worker = gate_corpus.HookWorker(BASH_HOOK)
    try:
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                   "permission_mode": "default", "cwd": str(REPO_ROOT),
                   "tool_input": {"command": command}}
        _code, stdout, _stderr = worker.invoke(payload)
    finally:
        worker.close()
    if not stdout.strip():
        return ""
    return json.loads(stdout)["hookSpecificOutput"]["permissionDecision"]


class LabelGateTest(unittest.TestCase):
    """Pull requests that touch the pi chain need the approval label."""

    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("pi_path_integrity", INTEGRITY_CHECKER)
        cls.checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.checker)

    def test_pi_paths_require_approval(self) -> None:
        for path in PI_PATHS:
            with self.subTest(path=path):
                self.assertTrue(self.checker.requires_approval([path]))


class FileToolGateTest(unittest.TestCase):
    """File-tool writes below the pi chain paths route to consent."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for relative in PI_PATHS:
            (self.root / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.root / relative).write_text("text\n", encoding="utf-8")

    def decision(self, relative: str) -> str:
        """Return the consent hook decision for an Edit of `relative`."""
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Edit",
                   "permission_mode": "default", "cwd": str(self.root),
                   "tool_input": {"file_path": str(self.root / relative),
                                  "old_string": "text", "new_string": "other"}}
        environment = dict(os.environ)
        environment.pop("CLAUDE_PROJECT_DIR", None)
        result = subprocess.run(
            [sys.executable, str(CONSENT_HOOK)], input=json.dumps(payload),
            capture_output=True, text=True, check=False, env=environment)
        if not result.stdout.strip():
            return ""
        return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]

    def test_pi_path_edits_ask(self) -> None:
        for relative in PI_PATHS:
            with self.subTest(path=relative):
                self.assertEqual(self.decision(relative), "ask")


class ShellGateTest(unittest.TestCase):
    """Shell writes below the pi chain paths route to consent."""

    def test_pi_path_writes_ask(self) -> None:
        for relative in PI_PATHS:
            with self.subTest(path=relative):
                self.assertEqual(bash_verdict(f"echo x > {relative}"), "ask")


if __name__ == "__main__":
    unittest.main()
