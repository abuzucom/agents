#!/usr/bin/env python3
"""Check the tag release workflow wiring and its write permissions."""
import unittest

import yaml

from tests.test_release_check_tag import ROOT, load_release

WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
ATTEST_PIN = "actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6"


def load_workflow() -> dict:
    """Return the parsed release workflow."""
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def read_triggers(workflow: dict) -> dict:
    """Return the trigger map. PyYAML reads the bare `on` key as True."""
    return workflow.get("on", workflow.get(True))


def list_run_text(job: dict) -> str:
    """Return every run script of one job joined in step order."""
    return "\n".join(str(step.get("run", "")) for step in job["steps"])


class ReleaseWorkflowWiringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = load_release()
        cls.workflow = load_workflow()

    def test_only_a_pushed_v_tag_starts_the_workflow(self):
        self.assertEqual(read_triggers(self.workflow), {"push": {"tags": ["v*"]}})
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})

    def test_release_job_permissions_equal_the_constant(self):
        job = self.workflow["jobs"]["release"]
        self.assertEqual(job["permissions"], dict(self.release.RELEASE_JOB_PERMISSIONS))

    def test_only_the_release_job_can_write(self):
        for name, job in self.workflow["jobs"].items():
            with self.subTest(job=name):
                writes = [scope for scope, level in job.get("permissions", {}).items()
                          if level == "write"]
                self.assertEqual(bool(writes), name == "release")

    def test_release_needs_the_tag_check(self):
        self.assertEqual(self.workflow["jobs"]["release"]["needs"], "check-tag")

    def test_tag_check_runs_the_helper_sync_check_and_main_ancestry(self):
        text = list_run_text(self.workflow["jobs"]["check-tag"])
        self.assertIn('python scripts/release.py check-tag "$GITHUB_REF_NAME"', text)
        self.assertIn("python scripts/sync.py --check", text)
        self.assertIn('git merge-base --is-ancestor "$GITHUB_SHA" origin/main', text)

    def test_every_checkout_persists_no_credentials(self):
        for name, job in self.workflow["jobs"].items():
            for step in job["steps"]:
                if str(step.get("uses", "")).startswith("actions/checkout@"):
                    with self.subTest(job=name):
                        self.assertIs(step["with"]["persist-credentials"], False)

    def test_attestation_uses_the_pinned_action(self):
        steps = self.workflow["jobs"]["release"]["steps"]
        attest = [step for step in steps
                  if str(step.get("uses", "")).startswith("actions/attest@")]
        self.assertEqual(len(attest), 2)
        for step in attest:
            with self.subTest(step=step.get("name")):
                self.assertEqual(step["uses"], ATTEST_PIN)

    def test_release_only_fills_a_draft(self):
        text = list_run_text(self.workflow["jobs"]["release"])
        self.assertIn("gh release create", text)
        self.assertIn("--draft", text)
        self.assertIn("--generate-notes", text)
        self.assertNotIn("gh release edit", text)
        self.assertNotIn("--prerelease", text)
        self.assertNotIn("--latest", text)

    def test_release_runs_no_reviewer_workflow(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("abuzucom/euler", text)
        self.assertNotIn("abuzucom/foucault", text)


if __name__ == "__main__":
    unittest.main()
