#!/usr/bin/env python3
"""Cover the euler pull request quality review wiring."""
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "quality-review-pr.yml"
# Euler 0.9.0. The uses: pin and quality_ref must name this one commit.
PINNED_COMMIT = "940c53a39b7cc7345b1f6232d43bec7c4d7623df"
REUSABLE_WORKFLOW = "abuzucom/euler/.github/workflows/quality-review.yml"
FULL_SHA = re.compile(r"[0-9a-f]{40}")
UPSTREAM_WORKFLOWS = ("Convention Sync Check", "Immutable Compliance")


class QualityReviewWiringTest(unittest.TestCase):
    """Keep the euler caller workflow pinned, gated, and fork safe."""

    def setUp(self):
        self.text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.workflow = yaml.safe_load(self.text)
        self.jobs = self.workflow["jobs"]

    def test_workflow_parses_and_exists(self):
        self.assertTrue(WORKFLOW_PATH.is_file())
        self.assertIsInstance(self.workflow, dict)

    def test_upstream_workflow_names_exist_in_this_repository(self):
        # A workflow_run trigger naming a missing workflow never fires.
        names = set()
        for path in (ROOT / ".github" / "workflows").glob("*.yml"):
            parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
            names.add(parsed.get("name"))
        for upstream in UPSTREAM_WORKFLOWS:
            self.assertIn(upstream, names)

    def test_triggers_after_tests_and_compliance(self):
        # PyYAML 1.1 parses a bare `on:` key as the boolean True, so match the
        # trigger block as raw text instead of indexing the parsed mapping.
        self.assertIn("workflow_run:", self.text)
        self.assertIn(
            'workflows: ["Convention Sync Check", "Immutable Compliance"]',
            self.text,
        )
        self.assertIn("types: [completed]", self.text)

    def test_review_waits_for_both_upstream_workflows(self):
        review_if = self.jobs["review"]["if"]
        self.assertIn("needs.resolve.outputs.tests_passed == 'true'", review_if)
        self.assertIn(
            "needs.resolve.outputs.compliance_passed == 'true'", review_if)
        self.assertIn(
            "needs.resolve.outputs.already_reviewed == 'false'", review_if)
        script = self.jobs["resolve"]["steps"][0]["with"]["script"]
        for upstream in UPSTREAM_WORKFLOWS:
            self.assertIn(f"'{upstream}'", script)

    def test_review_job_pins_workflow_and_quality_ref_to_one_commit(self):
        review_job = self.jobs["review"]
        self.assertEqual(
            review_job["uses"], f"{REUSABLE_WORKFLOW}@{PINNED_COMMIT}")
        self.assertEqual(review_job["with"]["quality_ref"], PINNED_COMMIT)
        self.assertTrue(FULL_SHA.fullmatch(PINNED_COMMIT))

    def test_review_job_maps_only_the_provider_secret(self):
        self.assertEqual(
            self.jobs["review"]["secrets"],
            {"MODEL_API_KEY": "${{ secrets.OLLAMA_API_KEY }}"},
        )
        self.assertNotIn("secrets: inherit", self.text)

    def test_review_job_fails_closed_on_block_or_needs_human(self):
        self.assertTrue(self.jobs["review"]["with"]["fail_on_block"])

    def test_only_same_repository_pull_requests_reach_the_review(self):
        self.assertIn(
            "needs.resolve.outputs.same_repository == 'true'",
            self.jobs["review"]["if"],
        )
        reusable_calls = [
            name for name, job in self.jobs.items()
            if str(job.get("uses", "")).startswith(REUSABLE_WORKFLOW)
        ]
        self.assertEqual(reusable_calls, ["review"])

    def test_fork_pull_requests_receive_a_skip_check_and_no_secret(self):
        fork_job = self.jobs["fork-review-skipped"]
        self.assertNotIn("secrets", fork_job)
        self.assertIn(
            "needs.resolve.outputs.same_repository == 'false'", fork_job["if"])
        self.assertIn("name: 'quality-review'", self.text)
        self.assertIn("conclusion: 'skipped'", self.text)

    def test_jobs_declare_least_privilege_permissions(self):
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        self.assertNotIn("write", self.jobs["resolve"]["permissions"].values())
        self.assertEqual(
            self.jobs["fork-review-skipped"]["permissions"],
            {"checks": "write"},
        )

    def test_github_script_actions_are_pinned_to_full_commit_shas(self):
        for job_name in ("resolve", "fork-review-skipped"):
            step = self.jobs[job_name]["steps"][0]
            action, _, revision = step["uses"].partition("@")
            self.assertEqual(action, "actions/github-script")
            self.assertTrue(FULL_SHA.fullmatch(revision.split()[0]))


if __name__ == "__main__":
    unittest.main()
