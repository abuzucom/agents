#!/usr/bin/env python3
"""Keep the persona label caller and its exemption manifest entry in step.

The trusted compliance scan reads `.compliance-tree-exemptions.json` from the
base branch. A caller edit without a matching manifest digest fails that scan
after merge. This test catches the drift on the pull request branch.
"""
import hashlib
import json
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / ".compliance-tree-exemptions.json"
CALLER = ".github/workflows/persona-review-labels.yml"


class PersonaCallerManifestTest(unittest.TestCase):
    """The manifest entry names the caller digest and every caller wrapper pin."""

    def setUp(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.entry = manifest["pull_request_target"][CALLER]
        self.caller_bytes = (ROOT / CALLER).read_bytes()

    def test_manifest_digest_matches_caller(self):
        self.assertEqual(self.entry["sha256"], hashlib.sha256(self.caller_bytes).hexdigest())

    def test_manifest_workflows_match_caller(self):
        workflow = yaml.safe_load(self.caller_bytes.decode("utf-8"))
        targets = {job["uses"] for job in workflow["jobs"].values()}
        self.assertEqual(set(self.entry["reusable_workflows"]), targets)


if __name__ == "__main__":
    unittest.main()
