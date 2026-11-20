#!/usr/bin/env python3
"""Pin the plan-mode Git write denial across the shell gates (issue 100).

Plan mode permits inspection only. Each shell gate denies a Git write while
`permission_mode` is plan and keeps read-only Git commands open. The three
gates share one core helper. The verdicts match across the gates.
"""
import tempfile
import unittest
from pathlib import Path

from tests.test_gate_parity import (BASH_HOOK, CMD_HOOK, POWERSHELL_HOOK, _decision,
                                    bash, cmd, powershell)

PLAN_MODE = "plan"
DEFAULT_MODE = "default"
# Subcommands that run a helper program through a transport, a filter, or
# a help viewer.
GIT_HELPER_COMMANDS = (
    "git ls-remote ext::sh",
    "git cat-file --textconv HEAD:README.md",
    "git help log",
)
# Reads that a configured external diff program turns into a program run.
CONFIGURED_HELPER_READS = ("git diff", "git ls-files")
GATE_HOOKS = (("bash", BASH_HOOK, "Bash"), ("powershell", POWERSHELL_HOOK, "PowerShell"),
              ("cmd", CMD_HOOK, "Cmd"))
GIT_WRITE_COMMANDS = (
    "git commit -m change",
    "git branch -m fix/rename-branch",
    "git push origin feat/x",
    "git switch -c fix/new-branch",
    "git checkout -b fix/new-branch",
    "git add README.md",
    "git -C /repo commit -m change",
)
GIT_READ_COMMANDS = (
    "git status",
    "git log --oneline -5",
    "git diff",
    "git show HEAD",
)
# Inspection subcommands with options that write files or run programs.
GIT_UNSAFE_OPTION_COMMANDS = (
    "git diff --output=changes.txt",
    "git diff --output changes.txt",
    "git grep -O cat pattern",
    "git grep -Ocat pattern",
    "git grep --open-files-in-pager=cat pattern",
    "git log --ext-diff",
    "git diff --textconv",
    "git -c core.pager=cat status",
    "git --config-env=core.pager=PAGER status",
    "git --paginate log",
    "git -p log",
    "git --exec-path=/tmp status",
    "git format-patch -o out HEAD~1",
)
GIT_SAFE_OPTION_COMMANDS = (
    "git log --oneline -5",
    "git diff --stat",
    "git show --name-only HEAD",
)
GATES = (("bash", bash), ("powershell", powershell), ("cmd", cmd))


class PlanModeGitWriteTest(unittest.TestCase):
    """Plan mode denies Git writes in every shell gate."""

    def test_git_writes_deny_in_plan_mode(self):
        for command in GIT_WRITE_COMMANDS:
            for gate_name, gate in GATES:
                with self.subTest(command=command, gate=gate_name):
                    self.assertEqual(gate(command, PLAN_MODE), "deny")

    def test_git_reads_pass_in_plan_mode(self):
        for command in GIT_READ_COMMANDS:
            for gate_name, gate in GATES:
                with self.subTest(command=command, gate=gate_name):
                    self.assertEqual(gate(command, PLAN_MODE), "")

    def test_unsafe_git_options_deny_in_plan_mode(self):
        for command in GIT_UNSAFE_OPTION_COMMANDS:
            for gate_name, gate in GATES:
                with self.subTest(command=command, gate=gate_name):
                    self.assertEqual(gate(command, PLAN_MODE), "deny")

    def test_safe_git_options_pass_in_plan_mode(self):
        for command in GIT_SAFE_OPTION_COMMANDS:
            for gate_name, gate in GATES:
                with self.subTest(command=command, gate=gate_name):
                    self.assertEqual(gate(command, PLAN_MODE), "")

    def test_default_mode_keeps_ordinary_git_writes_open(self):
        for gate_name, gate in GATES:
            with self.subTest(gate=gate_name):
                self.assertEqual(gate("git commit -m change"), "")


class PlanModeHelperTest(unittest.TestCase):
    """Plan mode denies Git reads that run a helper program."""

    def test_helper_subcommands_deny_in_plan_mode(self):
        for command in GIT_HELPER_COMMANDS:
            for gate_name, gate in GATES:
                with self.subTest(command=command, gate=gate_name):
                    self.assertEqual(gate(command, PLAN_MODE), "deny")

    def test_configured_external_diff_denies_in_plan_mode(self):
        with tempfile.TemporaryDirectory() as root:
            git_dir = Path(root) / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text(
                "[core]\n\tbare = false\n[diff]\n\texternal = /tmp/helper\n",
                encoding="utf-8")
            for command in CONFIGURED_HELPER_READS:
                for gate_name, hook, tool in GATE_HOOKS:
                    with self.subTest(command=command, gate=gate_name):
                        self.assertEqual(
                            _decision(hook, tool, command, PLAN_MODE, root), "deny")
            for gate_name, hook, tool in GATE_HOOKS:
                with self.subTest(command="git diff", gate=gate_name, mode=DEFAULT_MODE):
                    self.assertEqual(
                        _decision(hook, tool, "git diff", DEFAULT_MODE, root), "ask")

    def test_bash_pager_assignment_denies_in_plan_mode(self):
        self.assertEqual(bash("GIT_PAGER=less git log", PLAN_MODE), "deny")


if __name__ == "__main__":
    unittest.main()
