"""Plan mode permits Git reads and denies every Git write.

Each class stays small because the hook coverage runner gives every test class
one shard with a fixed time limit, and every case launches a hook.
"""
import importlib.util
import json
import os
import subprocess
import sys
import unittest

from tests.read_only_branch_support import BranchFixture, decision
from tests.test_enforce_branch_name import REPO_ROOT

FEATURE_BRANCH = "fix/example"
INVALID_BRANCH = "feature_without_prefix"
PLAN_MODE = "plan"
DEFAULT_MODE = "default"
TIMEOUT_SECONDS = 15
BLOCKING_EXIT_CODE = 2
PLAN_MODE_EXIT_TOOL = "ExitPlanMode"
GIT_WRITES = (
    'git commit -m "fix: x"', "git branch -m fix/other", "git branch -M fix/other",
    "git branch -d fix/other", "git branch -D fix/other", "git branch fix/other",
    "git switch -c fix/other", "git switch -C fix/other", "git checkout -b fix/other",
    "git merge fix/other", "git rebase main", "git reset --hard", "git push origin HEAD",
    "git tag v1", "git stash", "git cherry-pick abc", "git revert abc", "git am x.patch",
    "git apply x.patch", "git rm README.md", "git mv README.md R.md", "git add README.md",
    "git config user.name x", "git -C . commit -m x",
)
GIT_READS = (
    "git status", "git log --oneline -5", "git diff", "git show HEAD",
    "git branch --list", "git rev-parse HEAD", "git ls-files",
)
# Shell gates that see Git before the branch hook: one representative per write family.
SHELL_GATE_WRITES = ('git commit -m "fix: x"', "git branch -m fix/other", "git push origin HEAD")
SHELL_GATES = (
    ("block_destructive_bash.py", "Bash"),
    ("block_destructive_powershell.py", "PowerShell"),
    ("block_destructive_cmd.py", "Cmd"),
)


class BranchHookPlanModeWritesTest(unittest.TestCase):
    """The branch hook denies each Git write while the session plans."""

    def test_git_writes_deny_in_plan_mode(self) -> None:
        fixture = BranchFixture(self, FEATURE_BRANCH)
        for command in GIT_WRITES:
            with self.subTest(command=command):
                result = fixture.run("Bash", {"command": command}, mode=PLAN_MODE)
                self.assertEqual(decision(result), "deny", result.stderr)
                self.assertIn(PLAN_MODE_EXIT_TOOL, result.stderr)


class BranchHookPlanModeReadsTest(unittest.TestCase):
    """Git reads keep working while the session plans."""

    def test_git_reads_allow_in_plan_mode(self) -> None:
        fixture = BranchFixture(self, FEATURE_BRANCH)
        for command in GIT_READS:
            with self.subTest(command=command):
                result = fixture.run("Bash", {"command": command}, mode=PLAN_MODE)
                self.assertEqual(decision(result), "allow", result.stderr)


class BranchHookDefaultModeParityTest(unittest.TestCase):
    """Outside plan mode the branch hook keeps its recorded verdicts."""

    def test_git_writes_keep_default_mode_verdicts(self) -> None:
        # Snapshot recorded on b452348 before the plan-mode change: every write allows.
        fixture = BranchFixture(self, FEATURE_BRANCH)
        for command in GIT_WRITES + GIT_READS:
            with self.subTest(command=command):
                result = fixture.run("Bash", {"command": command}, mode=DEFAULT_MODE)
                self.assertEqual(decision(result), "allow", result.stderr)


class BranchRecoveryPlanModeTest(unittest.TestCase):
    """Branch recovery waits until the session leaves plan mode."""

    def test_recovery_rename_denies_in_plan_mode(self) -> None:
        fixture = BranchFixture(self, INVALID_BRANCH)
        result = fixture.run("Bash", {"command": "git branch -m fix/describe-the-actual-change"},
                             mode=PLAN_MODE)
        self.assertEqual(decision(result), "deny", result.stderr)
        self.assertIn(PLAN_MODE_EXIT_TOOL, result.stderr)

    def test_recovery_switch_denies_in_plan_mode(self) -> None:
        fixture = BranchFixture(self, "main")
        result = fixture.run("Bash", {"command": "git switch -c fix/describe-the-actual-change"},
                             mode=PLAN_MODE)
        self.assertEqual(decision(result), "deny", result.stderr)
        self.assertIn(PLAN_MODE_EXIT_TOOL, result.stderr)


def run_shell_gate(script: str, tool_name: str, command: str, mode: str) -> subprocess.CompletedProcess:
    """Send one shell payload to a destructive-command gate."""
    payload = {"hook_event_name": "PreToolUse", "permission_mode": mode,
               "tool_name": tool_name, "tool_input": {"command": command}}
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "hooks" / script)], input=json.dumps(payload),
        cwd=REPO_ROOT, env=dict(os.environ), capture_output=True, text=True,
        timeout=TIMEOUT_SECONDS, check=False,
    )


class ShellGatePlanModeTest(unittest.TestCase):
    """Bash, PowerShell, and CMD gates deny Git writes in plan mode with parity."""

    def test_shell_gates_deny_git_writes_in_plan_mode(self) -> None:
        for script, tool_name in SHELL_GATES:
            for command in SHELL_GATE_WRITES:
                with self.subTest(gate=script, command=command):
                    result = run_shell_gate(script, tool_name, command, PLAN_MODE)
                    self.assertEqual(result.returncode, BLOCKING_EXIT_CODE, result.stderr)
                    self.assertIn(PLAN_MODE_EXIT_TOOL, result.stderr)

    def test_shell_gates_leave_default_mode_writes_unblocked(self) -> None:
        for script, tool_name in SHELL_GATES:
            for command in SHELL_GATE_WRITES:
                with self.subTest(gate=script, command=command):
                    result = run_shell_gate(script, tool_name, command, DEFAULT_MODE)
                    self.assertNotEqual(result.returncode, BLOCKING_EXIT_CODE, result.stderr)

    def test_shell_gates_allow_git_reads_in_plan_mode(self) -> None:
        for script, tool_name in SHELL_GATES:
            with self.subTest(gate=script):
                result = run_shell_gate(script, tool_name, "git status", PLAN_MODE)
                self.assertNotEqual(result.returncode, BLOCKING_EXIT_CODE, result.stderr)


def load_core():
    """Import the shared gate core by path, since hooks/ is not a package."""
    sys.path.insert(0, str(REPO_ROOT / "hooks"))
    spec = importlib.util.spec_from_file_location("plan_mode_core", REPO_ROOT / "hooks" / "_gate_core.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PlanModeProgramResolutionTest(unittest.TestCase):
    """Plan mode finds Git behind assignments, wrappers, and wrapper options."""

    def setUp(self) -> None:
        self.core = load_core()
        self.plan_payload = {"permission_mode": PLAN_MODE}

    def test_git_behind_prefixes_still_denies(self) -> None:
        segments = (
            ["GIT_PAGER=cat", "git", "commit", "-m", "x"],
            ["env", "git", "push"],
            ["env", "-i", "git", "tag", "v1"],
            ["command", "git", "reset", "--hard"],
        )
        for segment in segments:
            with self.subTest(segment=segment):
                reason = self.core.plan_mode_git_write_reason(self.plan_payload, [segment])
                self.assertIn(PLAN_MODE_EXIT_TOOL, reason)

    def test_assignment_only_segment_is_not_git(self) -> None:
        reason = self.core.plan_mode_git_write_reason(self.plan_payload, [["FOO=1", "BAR=2"]])
        self.assertEqual(reason, "")

    def test_git_reads_behind_prefixes_pass(self) -> None:
        reason = self.core.plan_mode_git_write_reason(
            self.plan_payload, [["env", "GIT_PAGER=cat", "git", "log", "-3"]])
        self.assertEqual(reason, "")

    def test_default_mode_never_reports(self) -> None:
        reason = self.core.plan_mode_git_write_reason(
            {"permission_mode": DEFAULT_MODE}, [["git", "commit", "-m", "x"]])
        self.assertEqual(reason, "")


if __name__ == "__main__":
    unittest.main()
