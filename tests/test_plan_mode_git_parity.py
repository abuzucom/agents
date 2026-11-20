#!/usr/bin/env python3
"""Pin the plan-mode Git write denial across the shell gates (issue 100).

Plan mode permits inspection only. Each shell gate denies a Git write while
`permission_mode` is plan and keeps read-only Git commands open. The three
gates share one core helper. The verdicts match across the gates.
"""
import unittest

from tests.test_gate_parity import bash, cmd, powershell

PLAN_MODE = "plan"
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


if __name__ == "__main__":
    unittest.main()
