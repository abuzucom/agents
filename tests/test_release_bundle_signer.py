#!/usr/bin/env python3
"""Check that a reused draft bundle must come from the release workflow."""
import unittest

from tests.test_release_draft_lookup import find_step
from tests.test_release_workflow_wiring import load_workflow

SIGNER_FLAG = '--signer-workflow "$GITHUB_REPOSITORY/.github/workflows/release.yml"'


class ReusedBundleSignerTest(unittest.TestCase):
    def test_reused_bundle_verify_pins_the_release_workflow(self):
        job = load_workflow()["jobs"]["release"]
        text = find_step(job, "Save attestation bundle")["run"]
        verify_lines = [line for line in text.splitlines()
                        if "gh attestation verify" in line]
        self.assertEqual(len(verify_lines), 1)
        self.assertIn(SIGNER_FLAG, verify_lines[0])


if __name__ == "__main__":
    unittest.main()
