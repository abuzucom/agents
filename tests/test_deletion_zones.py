#!/usr/bin/env python3
"""Deletes inside a session's own .scratch and .worktrees folders route to consent."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.test_command_execution_gate import _load_gate_module
from tests.test_enforce_branch_name import bash_payload, run_hook

SESSION = "session-abc_123"
OTHER_SESSION = "session-other"
GIT_TIMEOUT_SECONDS = 15
FEATURE_BRANCH = "feat/zone-test"


def _init_repository(root: Path) -> None:
    """Create a real Git repository so tracked-file checks can run."""
    subprocess.run(["git", "init", "-q", str(root)], check=True, timeout=GIT_TIMEOUT_SECONDS)


class ZoneVerdictTest(unittest.TestCase):
    """workflow_decision asks for own-zone deletes and leaves every other rm unmatched."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.gate = _load_gate_module()

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        _init_repository(self.root)
        for zone in (".scratch", ".worktrees"):
            (self.root / zone / SESSION / "run1").mkdir(parents=True)
            (self.root / zone / SESSION / "a.txt").write_text("x", encoding="utf-8")
            (self.root / zone / OTHER_SESSION).mkdir(parents=True)

    def decide(self, command: str, session_id: str = SESSION) -> str:
        return self.gate.workflow_decision(command, str(self.root), session_id=session_id)[0]

    def test_own_zone_deletes_ask(self) -> None:
        for command in (f"rm .scratch/{SESSION}/a.txt", f"rm -rf .scratch/{SESSION}/run1",
                        f"rm -r .worktrees/{SESSION}/run1", f"rm -f .worktrees/{SESSION}/a.txt",
                        f"rm -rf .scratch/{SESSION}/run1 .worktrees/{SESSION}/run1"):
            with self.subTest(command=command):
                self.assertEqual(self.decide(command), "ask")

    def test_other_targets_unmatched(self) -> None:
        for command in ("rm -rf .scratch", f"rm -rf .scratch/{SESSION}",
                        f"rm -rf .scratch/{SESSION}/", f"rm -rf .scratch/{OTHER_SESSION}/x",
                        f"rm -rf .scratch/{SESSION}/../{OTHER_SESSION}",
                        f"rm -rf .scratch/{SESSION}/*", "rm -rf hooks",
                        f"rm -rf .scratch/{SESSION}/run1 hooks", f"rm -v .scratch/{SESSION}/a.txt",
                        f"rm -rf /tmp/{SESSION}", "rm"):
            with self.subTest(command=command):
                self.assertEqual(self.decide(command), "")

    def test_missing_or_bad_session_unmatched(self) -> None:
        command = f"rm -rf .scratch/{SESSION}/run1"
        for session_id in ("", "../x", "a b", "x" * 129):
            with self.subTest(session_id=session_id):
                self.assertEqual(self.decide(command, session_id), "")
        self.assertEqual(self.gate.workflow_decision(command, str(self.root))[0], "")

    @unittest.skipIf(os.name == "nt", "Symlink creation needs privileges on Windows")
    def test_link_leaving_zone_unmatched(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / ".scratch" / SESSION / "link").symlink_to(outside)
        self.assertEqual(self.decide(f"rm -rf .scratch/{SESSION}/link/x"), "")

    def test_tracked_file_unmatched(self) -> None:
        subprocess.run(["git", "-C", str(self.root), "add", "-f", f".scratch/{SESSION}/a.txt"],
                       check=True, timeout=GIT_TIMEOUT_SECONDS)
        self.assertEqual(self.decide(f"rm .scratch/{SESSION}/a.txt"), "")

    def test_zone_delete_not_read_only(self) -> None:
        self.assertFalse(self.gate.read_only_workflow(f"rm .scratch/{SESSION}/a.txt",
                                                      str(self.root)))


class ZoneBranchHookTest(unittest.TestCase):
    """The branch hook asks for an own-zone delete and denies other rm calls."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        _init_repository(self.root)
        (self.root / ".scratch" / SESSION / "run1").mkdir(parents=True)

    def run_rm(self, command: str, branch: str = FEATURE_BRANCH, session_id=SESSION):
        payload = bash_payload(command)
        if session_id is not None:
            payload["session_id"] = session_id
        result = run_hook(payload, branch, project_dir=self.root)
        return result, json.loads(result.stdout or "{}")

    def test_own_zone_asks(self) -> None:
        result, output = self.run_rm(f"rm -rf .scratch/{SESSION}/run1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "ask")
        self.assertIn("zone", output["hookSpecificOutput"]["permissionDecisionReason"])

    def test_other_rm_denies(self) -> None:
        for command, session_id in ((f"rm -rf .scratch/{OTHER_SESSION}", SESSION),
                                    (f"rm -rf .scratch/{SESSION}/run1", None)):
            with self.subTest(command=command, session_id=session_id):
                result, _output = self.run_rm(command, session_id=session_id)
                self.assertEqual(result.returncode, 2, result.stdout)

    def test_primary_branch_denies(self) -> None:
        result, _output = self.run_rm(f"rm -rf .scratch/{SESSION}/run1", branch="main")
        self.assertEqual(result.returncode, 2, result.stdout)


if __name__ == "__main__":
    unittest.main()
