#!/usr/bin/env python3
"""Check that the release job fails on a draft lookup error other than absence."""
import unittest

from tests.test_release_workflow_wiring import load_workflow

NOT_FOUND_MESSAGE = "release not found"


def find_step(job: dict, name: str) -> dict:
    """Return the step of a job with the given name."""
    matches = [step for step in job["steps"] if step.get("name") == name]
    if len(matches) != 1:
        raise AssertionError(f"expected one step named {name!r}, found {len(matches)}")
    return matches[0]


class DraftLookupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.job = load_workflow()["jobs"]["release"]

    def test_inspect_not_found_absent(self):
        text = find_step(self.job, "Inspect existing draft")["run"]
        self.assertIn(NOT_FOUND_MESSAGE, text)
        self.assertNotIn("2>/dev/null", text)
        self.assertIn("release_exists=false", text)
        self.assertIn("release_exists=true", text)

    def test_upload_uses_inspect_result(self):
        step = find_step(self.job, "Upload to draft release")
        self.assertEqual(step["env"]["RELEASE_EXISTS"],
                         "${{ steps.draft.outputs.release_exists }}")
        self.assertNotIn("> /dev/null 2>&1", step["run"])
        self.assertIn('"$RELEASE_EXISTS"', step["run"])


if __name__ == "__main__":
    unittest.main()
