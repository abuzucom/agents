#!/usr/bin/env python3
"""Every gate denial ends with the required stop-and-report response."""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / "hooks"
TIMEOUT_SECONDS = 15
REQUIRED_SUFFIX = ("Report the gate name and reason to the user. Do not retry variants. "
                   "Do not ask the user to change any gate. Then stop until the next user message.")
BLOCKING_EXIT_CODE = 2


def load_hook_module(name: str):
    """Import one hook file by path, since hooks/ is not an importable package."""
    sys.path.insert(0, str(HOOKS_DIR))
    spec = importlib.util.spec_from_file_location(f"denial_suffix_{name}", HOOKS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_hook(script: str, payload, environment: dict = None,
             arguments: tuple = ()) -> subprocess.CompletedProcess:
    """Run one real hook entrypoint against a synthetic payload."""
    return subprocess.run(
        [sys.executable, str(HOOKS_DIR / script), *arguments],
        input=json.dumps(payload), cwd=REPO_ROOT, env=environment or dict(os.environ),
        capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False,
    )


def pre_tool_use(tool_name: str, tool_input) -> dict:
    """Return one Claude PreToolUse payload."""
    return {"hook_event_name": "PreToolUse", "permission_mode": "default",
            "tool_name": tool_name, "tool_input": tool_input}


class DenialSuffixAssertions(unittest.TestCase):
    """Shared checks for one denied hook run."""

    def assert_denial_carries_suffix(self, result: subprocess.CompletedProcess) -> None:
        """Require a blocking exit and the suffix as the final stderr text."""
        self.assertEqual(result.returncode, BLOCKING_EXIT_CODE, result.stdout + result.stderr)
        self.assertTrue(result.stderr.strip().endswith(REQUIRED_SUFFIX), result.stderr)
        self.assertNotIn("then retry", result.stderr.lower())
        if result.stdout.strip():
            reason = json.loads(result.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
            self.assertTrue(reason.endswith(REQUIRED_SUFFIX), reason)


class SharedEmitterTest(DenialSuffixAssertions):
    """The shared emitters append the suffix to denials only."""

    def setUp(self) -> None:
        self.core = load_hook_module("_gate_core")

    def capture_emit(self, decision: str, reason: str) -> tuple:
        """Return (exit code, stdout, stderr) for one shared emit call."""
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = self.core.emit("example_gate.py", decision, reason)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_emit_deny_appends_suffix(self) -> None:
        code, stdout, stderr = self.capture_emit("deny", "example reason")
        self.assertEqual(code, BLOCKING_EXIT_CODE)
        self.assertTrue(stderr.strip().endswith(REQUIRED_SUFFIX))
        reason = json.loads(stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertTrue(reason.endswith(REQUIRED_SUFFIX))
        self.assertIn("example reason", reason)

    def test_emit_ask_keeps_text_without_suffix(self) -> None:
        code, stdout, _stderr = self.capture_emit("ask", "example consent reason")
        self.assertEqual(code, 0)
        reason = json.loads(stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertEqual(reason, "blocked by hooks/example_gate.py: example consent reason")

    def test_unattended_ask_denial_carries_suffix(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        payload = {"permission_mode": "bypassPermissions"}
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = self.core.decide("example_gate.py", payload, "ask", "consent reason")
        self.assertEqual(code, BLOCKING_EXIT_CODE)
        self.assertTrue(stderr.getvalue().strip().endswith(REQUIRED_SUFFIX))

    def test_branch_gate_deny_appends_suffix_for_every_client(self) -> None:
        branch_gate = load_hook_module("enforce_branch_name")
        for client in ("claude", "codex", "gemini", "antigravity"):
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                branch_gate._deny(client, "example reason")
            with self.subTest(client=client):
                text = stdout.getvalue() if client in ("gemini", "antigravity") else stderr.getvalue()
                if client in ("gemini", "antigravity"):
                    text = json.loads(text)["reason"]
                self.assertTrue(text.strip().endswith(REQUIRED_SUFFIX), text)

    def test_gate_adoption_deny_appends_suffix_for_every_client(self) -> None:
        adoption_gate = load_hook_module("enforce_gate_adoption")
        for client in ("claude", "codex", "gemini", "antigravity"):
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                adoption_gate._deny(client, "example reason")
            with self.subTest(client=client):
                combined = stdout.getvalue() + stderr.getvalue()
                self.assertIn(REQUIRED_SUFFIX, combined)


class GateEntrypointDenialTest(DenialSuffixAssertions):
    """Real hook entrypoints end each denial with the suffix."""

    def test_bash_destructive_denial(self) -> None:
        result = run_hook("block_destructive_bash.py", pre_tool_use("Bash", {"command": "rm -rf /"}))
        self.assert_denial_carries_suffix(result)

    def test_powershell_destructive_denial(self) -> None:
        result = run_hook("block_destructive_powershell.py",
                          pre_tool_use("PowerShell", {"command": "Remove-Item -Recurse -Force C:\\"}))
        self.assert_denial_carries_suffix(result)

    def test_cmd_destructive_denial(self) -> None:
        result = run_hook("block_destructive_cmd.py", pre_tool_use("Cmd", {"command": "rd /s /q C:\\"}))
        self.assert_denial_carries_suffix(result)

    def test_infrastructure_denial(self) -> None:
        environment = dict(os.environ, CLAUDE_PROJECT_DIR=str(REPO_ROOT))
        result = run_hook("block_infrastructure_access.py",
                          pre_tool_use("Read", {"file_path": "/root/.aws/credentials"}), environment)
        self.assert_denial_carries_suffix(result)

    def test_require_consent_denial(self) -> None:
        result = run_hook("require_consent.py", pre_tool_use("Edit", None))
        self.assert_denial_carries_suffix(result)

    def test_git_identity_denial(self) -> None:
        result = run_hook("enforce_git_identity.py",
                          {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": None})
        self.assert_denial_carries_suffix(result)


class BranchGateWorkflowDenialTest(DenialSuffixAssertions):
    """Opaque and npm denials from the registered branch hook carry the suffix."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        admin = self.root / ".git"
        (admin / "objects").mkdir(parents=True)
        (admin / "refs" / "heads").mkdir(parents=True)
        (admin / "HEAD").write_text("ref: refs/heads/fix/example\n", encoding="utf-8")
        (admin / "config").write_text("[core]\nbare = false\n", encoding="utf-8")
        global_config = self.root / "global.config"
        global_config.write_text("", encoding="utf-8")
        self.environment = {key: value for key, value in os.environ.items()
                            if not key.startswith("GIT_")}
        self.environment.update({"CLAUDE_PROJECT_DIR": str(self.root), "GIT_CONFIG_NOSYSTEM": "1",
                                 "GIT_CONFIG_GLOBAL": str(global_config)})

    def run_branch_hook(self, command: str) -> subprocess.CompletedProcess:
        """Send one Bash payload to the branch hook without executing it."""
        return run_hook("enforce_branch_name.py", pre_tool_use("Bash", {"command": command}),
                        self.environment, ("--client", "claude"))

    def test_opaque_program_denial(self) -> None:
        self.assert_denial_carries_suffix(self.run_branch_hook("node script.js"))

    def test_npm_project_config_denial_has_no_retry_instruction(self) -> None:
        (self.root / "package.json").write_text('{"scripts": {"test": "x"}}', encoding="utf-8")
        (self.root / ".npmrc").write_text("registry=https://example.invalid/\n", encoding="utf-8")
        result = self.run_branch_hook("npm test")
        self.assert_denial_carries_suffix(result)
        self.assertNotIn(str(self.root), result.stderr)


class SanitizedInterpolationTest(unittest.TestCase):
    """Untrusted values reach denial text only as single-line printable ASCII."""

    def test_sanitize_strips_terminal_and_invisible_characters(self) -> None:
        core = load_hook_module("_gate_core")
        hostile = "a\x1b[31mred\nnext\u202eevil\u200bzero\U000e0041tag"
        rendered = core.sanitize(hostile)
        for fragment in ("\x1b", "\n", "\u202e", "\u200b", "\U000e0041"):
            with self.subTest(fragment=repr(fragment)):
                self.assertNotIn(fragment, rendered)
        self.assertTrue(all(" " <= character <= "~" for character in rendered))


if __name__ == "__main__":
    unittest.main()
