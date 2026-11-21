#!/usr/bin/env python3
"""Check the release hardening: protection, approval environment, verify command."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from tests.test_release_check_tag import ROOT, load_release
from tests.test_release_workflow_wiring import load_workflow

INTEGRITY_PATH = ROOT / "scripts" / "check_gate_pr_integrity.py"
SIGNER_WORKFLOW = "--signer-workflow abuzucom/agents/.github/workflows/release.yml"
RELEASE_ENVIRONMENT = "release"
CHANGELOG_TEXT = "# Changelog\n\n## [2.27.0] (2026-11-18)\n\n### Added\n- Item.\n"


def load_integrity():
    """Load the gate integrity checker by path."""
    spec = importlib.util.spec_from_file_location("integrity_release", INTEGRITY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseHelperProtectionTest(unittest.TestCase):
    def test_release_helper_requires_label(self):
        integrity = load_integrity()
        for path in ("scripts/release.py", "Scripts/Release.py"):
            with self.subTest(path=path):
                self.assertTrue(integrity.requires_approval([path]))


class ReleaseEnvironmentTest(unittest.TestCase):
    def test_release_job_environment(self):
        job = load_workflow()["jobs"]["release"]
        self.assertEqual(job["environment"], RELEASE_ENVIRONMENT)

    def test_tag_check_no_environment(self):
        job = load_workflow()["jobs"]["check-tag"]
        self.assertNotIn("environment", job)


class VerifyCommandTest(unittest.TestCase):
    def test_release_notes_signer_pin(self):
        release = load_release()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "CHANGELOG.md").write_text(CHANGELOG_TEXT, encoding="utf-8")
            notes = release.release_notes(root, "2.27.0", None)
        self.assertIn(SIGNER_WORKFLOW, " ".join(notes.split()))

    def test_readme_pins_the_signer_workflow(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(SIGNER_WORKFLOW, " ".join(readme.split()))


if __name__ == "__main__":
    unittest.main()
