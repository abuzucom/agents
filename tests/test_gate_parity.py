#!/usr/bin/env python3
"""Assert the Bash, PowerShell, and CMD gates reach the same verdicts.

Parity is a promise unless something checks it. This session watched
scripts/check_commit_message.py diverge between two repositories until a
merge commit exposed it, so the shared corpus is a test rather than a
convention: a fix landing in one gate and not the other fails here.

Each row pairs a command with its equivalent in the other shell. Where a
form exists in only one shell, the pair repeats the same string, which
still asserts that both gates read it identically.
"""
import importlib.util
import json
import os
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate_corpus

REPO_ROOT = Path(__file__).resolve().parent.parent
BASH_HOOK = REPO_ROOT / "hooks" / "block_destructive_bash.py"
POWERSHELL_HOOK = REPO_ROOT / "hooks" / "block_destructive_powershell.py"
CMD_HOOK = REPO_ROOT / "hooks" / "block_destructive_cmd.py"
CORE_PATH = REPO_ROOT / "hooks" / "_gate_core.py"
_HOOK_WORKERS = {}


def hook_worker(hook: Path):
    """Return one process-local persistent worker for `hook`."""
    worker = _HOOK_WORKERS.get(hook)
    if worker is None:
        worker = gate_corpus.HookWorker(hook)
        _HOOK_WORKERS[hook] = worker
    return worker


def _decision(hook: Path, tool: str, command, mode: str = "default",
              cwd: str = "") -> str:
    """Return the permission decision one gate reaches for `command`."""
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "permission_mode": mode,
        "tool_input": {"command": command},
    }
    if cwd:
        payload["cwd"] = cwd
    _code, stdout, _stderr = hook_worker(hook).invoke(payload)
    try:
        return json.loads(stdout)["hookSpecificOutput"]["permissionDecision"]
    except (ValueError, KeyError):
        return ""


def bash(command, mode: str = "default") -> str:
    return _decision(BASH_HOOK, "Bash", command, mode)


def powershell(command, mode: str = "default") -> str:
    return _decision(POWERSHELL_HOOK, "PowerShell", command, mode)


def cmd(command, mode: str = "default", cwd: str = "") -> str:
    return _decision(CMD_HOOK, "Cmd", command, mode, cwd)


class GitParityTest(unittest.TestCase):
    """git decisions come from the shared core, so they cannot differ."""

    COMMANDS = (
        "git push --force",
        "git push -f origin main",
        "git reset --hard",
        "git push --force-with-lease",
        "git push --force-with-lease=main:abc123",
        "git push --mirror",
        "git push --delete origin feat/x",
        "git push origin +HEAD:main",
        "git push origin :main",
        "git push --prune origin",
        "git commit --amend",
        "git rebase -i HEAD~3",
        "git filter-branch --tree-filter true HEAD",
        "git -C /repo push --force",
        "git status",
        "git log --oneline -5",
        "git push origin feat/x",
        "git push -u origin feat/x",
    )

    def test_all_gates_agree_on_git(self):
        for command in self.COMMANDS:
            with self.subTest(command=command):
                self.assertEqual(bash(command), powershell(command))
                self.assertEqual(bash(command), cmd(command))

    def test_inline_config_and_repo_location_forms_agree(self):
        with tempfile.TemporaryDirectory() as root:
            git_dir = Path(root) / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text(
                '[diff "x"]\n\ttextconv = /tmp/evil\n', encoding="utf-8")
            commands = (
                "git -c core.pager=/tmp/evil status",
                "git -ccore.pager=/tmp/evil log",
                "git -c core.pager=/tmp/evil -c core.pager= status",
                "git --git-dir .git --work-tree . show HEAD",
                "git -C . diff",
            )
            for command in commands:
                with self.subTest(command=command):
                    self.assertEqual(
                        _decision(BASH_HOOK, "Bash", command, cwd=root),
                        _decision(POWERSHELL_HOOK, "PowerShell", command, cwd=root),
                    )
                    self.assertEqual(
                        _decision(BASH_HOOK, "Bash", command, cwd=root),
                        cmd(command, cwd=root),
                    )


class MalformedParityTest(unittest.TestCase):
    """All gates must fail closed on the same malformed inputs."""

    def test_non_string_commands_agree(self):
        for value in (None, 5, ["rm"], {"a": 1}):
            with self.subTest(value=value):
                self.assertEqual(bash(value), powershell(value))
                self.assertEqual(bash(value), cmd(value))

    def test_unattended_modes_agree(self):
        for mode in ("bypassPermissions", "dontAsk", "", "unknown-mode"):
            with self.subTest(mode=mode):
                self.assertEqual(
                    bash("git push --force-with-lease", mode),
                    powershell("git push --force-with-lease", mode))
                self.assertEqual(
                    bash("git push --force-with-lease", mode),
                    cmd("git push --force-with-lease", mode))


class CmdParityTest(unittest.TestCase):
    """Shared destructive behavior reaches one verdict in all three gates."""

    CASES = (
        ("rm -rf build", "Remove-Item -Recurse build", "rd /s /q build", "ask"),
        ("rm -rf C:\\", "Remove-Item -Recurse C:\\", "rd /s /q C:\\", "deny"),
        (
            "echo x > tests/test_auth.py",
            "Write-Output x > tests/test_auth.py",
            "echo x > tests\\test_auth.py",
            "ask",
        ),
    )

    def test_shared_behavior_agrees(self):
        for bash_command, powershell_command, cmd_command, expected in self.CASES:
            with self.subTest(command=cmd_command):
                self.assertEqual(bash(bash_command), expected)
                self.assertEqual(powershell(powershell_command), expected)
                self.assertEqual(cmd(cmd_command), expected)


class BoundaryParityTest(unittest.TestCase):
    """Each boundary class, in both spellings, reaches the same verdict."""

    PAIRS = (
        ("true\nrm -rf /tmp/x", "Write-Output x\nRemove-Item -Recurse /tmp/x"),
        ("true; rm -rf /tmp/x", "Write-Output x; Remove-Item -Recurse /tmp/x"),
        ("true && rm -rf /tmp/x", "Test-Path x && Remove-Item -Recurse /tmp/x"),
        ("true || rm -rf /tmp/x", "Test-Path x || Remove-Item -Recurse /tmp/x"),
        ("echo x | xargs rm -rf /tmp/x", "Get-Process | Remove-Item -Recurse /tmp/x"),
        ("rm -rf /", "Remove-Item -Recurse /"),
        ("rm -rf $HOME", "Remove-Item -Recurse $HOME"),
        ("rm -rf ~", "Remove-Item -Recurse ~"),
        ("rm -rf /tmp/scratch", "Remove-Item -Recurse /tmp/scratch"),
        ("rm build.log", "Remove-Item build.log"),
        ("ls -la", "Get-ChildItem"),
        ("echo x > tests/test_auth.py", "Write-Output x > tests/test_auth.py"),
        ("echo x > src/app.js", "Write-Output x > src/app.js"),
        ("cmd /c rd /s /q C:/work", "cmd /c rd /s /q C:/work"),
        # Grouping that puts a command where a program name goes. The
        # PowerShell gate read its own & { ... } and the Bash gate did not
        # read { ... ; }; the Bash gate read $( ... ) and the PowerShell
        # gate did not. Each gap was invisible until both spellings sat
        # in one row.
        ("{ rm -rf /tmp/x; }", "& { Remove-Item -Recurse -Force /tmp/x }"),
        ("{ git push --force; }", "& { git push --force }"),
        ("echo `rm -rf /tmp/x`",
         "Write-Output $(Remove-Item -Recurse -Force /tmp/x)"),
        ("rm -rf build", "Remove-Item -Recurse -Force (Join-Path $a build)"),
        ("echo {a,b}.txt", "Write-Output {a,b}.txt"),
    )

    def test_equivalent_commands_agree(self):
        for bash_command, powershell_command in self.PAIRS:
            with self.subTest(bash=bash_command):
                self.assertEqual(bash(bash_command), powershell(powershell_command))


class PowerShellPolicyParityTest(unittest.TestCase):
    """Shared high-risk program decisions apply through either shell gate."""

    CASES = (
        ("Invoke-Expression 'Get-Date'", "deny"),
        ("pwsh -Command 'Get-ChildItem'", "deny"),
        ("Add-Type -TypeDefinition 'public class X {}'", "deny"),
        ("Set-MpPreference -DisableRealtimeMonitoring true", "deny"),
        ("Register-ScheduledTask -TaskName x -Action y", "deny"),
        ("Copy-Item source.database '\\\\server\\share'", "deny"),
        ("Start-Process notepad.exe", "ask"),
        ("Import-Module Pester", "ask"),
        ("Get-Credential", "ask"),
        ("Invoke-WebRequest https://example.test/data.json", "ask"),
        ("Get-ChildItem .", ""),
    )

    def test_shared_policy_commands_match_expected_verdicts(self):
        for command, expected in self.CASES:
            with self.subTest(command=command):
                self.assertEqual(bash(command), expected)
                self.assertEqual(powershell(command), expected)


class CoreOwnershipTest(unittest.TestCase):
    """Every decision function lives in the core, not in one gate."""

    def test_git_environment_classifier_is_public(self):
        spec = importlib.util.spec_from_file_location("gate_core_public", CORE_PATH)
        core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(core)
        self.assertTrue(core.is_relevant_git_environment("GIT_DIR"))
        self.assertFalse(core.is_relevant_git_environment("PATH"))

    def test_no_gate_defines_its_own_verdict_helpers(self):
        shared = ("delete_verdict", "git_verdict", "push_verdict",
                  "is_root_target", "strongest", "is_test_path",
                  "cmd_delete_verdict", "sanitize",
                  "is_relevant_git_environment")
        for hook in (BASH_HOOK, POWERSHELL_HOOK, CMD_HOOK):
            source = hook.read_text(encoding="utf-8")
            for name in shared:
                with self.subTest(hook=hook.name, function=name):
                    self.assertNotIn(
                        f"def {name}(", source,
                        f"{hook.name} redefines {name}; it belongs to the core "
                        "so the gates cannot drift")


if __name__ == "__main__":
    unittest.main()
