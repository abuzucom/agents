#!/usr/bin/env python3
"""Check that the release notes floor is the highest stable version."""
import subprocess
import sys
import unittest

from tests.test_release_check_tag import RELEASE_PATH, load_release
from tests.test_release_draft_lookup import find_step
from tests.test_release_workflow_wiring import load_workflow

TIMEOUT_SECONDS = 30


class SelectLatestStableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = load_release()

    def test_highest_version_wins_over_listing_order(self):
        tags = ["v2.20.0", "v2.27.0", "v2.9.10", "v2.27.1"]
        self.assertEqual(self.release.select_latest_stable(tags), "v2.27.1")

    def test_numeric_order_beats_text_order(self):
        self.assertEqual(self.release.select_latest_stable(["v2.9.0", "v2.10.0"]), "v2.10.0")

    def test_names_outside_the_version_form_are_ignored(self):
        tags = ["latest", "v3.0.0-rc.1", "release-9", "v2.1.0", " ", "v02.0.0"]
        self.assertEqual(self.release.select_latest_stable(tags), "v2.1.0")

    def test_no_stable_version_returns_empty(self):
        self.assertEqual(self.release.select_latest_stable(["latest", ""]), "")
        self.assertEqual(self.release.select_latest_stable([]), "")


class LatestStableCommandTest(unittest.TestCase):
    def run_command(self, stdin_text: str) -> subprocess.CompletedProcess:
        """Run the latest-stable subcommand with the given standard input."""
        return subprocess.run(
            [sys.executable, str(RELEASE_PATH), "latest-stable"],
            input=stdin_text, capture_output=True, text=True,
            timeout=TIMEOUT_SECONDS, check=False)

    def test_command_prints_the_highest_tag(self):
        result = self.run_command("v2.27.0\nv2.20.0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "v2.27.0\n")

    def test_command_prints_nothing_without_a_stable_tag(self):
        result = self.run_command("")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")


class NotesStepTest(unittest.TestCase):
    def test_notes_step_selects_the_floor_through_the_helper(self):
        job = load_workflow()["jobs"]["release"]
        text = find_step(job, "Write checksums and release notes")["run"]
        self.assertIn("python scripts/release.py latest-stable", text)
        self.assertNotIn("--limit 1 ", text)


if __name__ == "__main__":
    unittest.main()
