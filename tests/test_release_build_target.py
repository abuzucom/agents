#!/usr/bin/env python3
"""Check that a build target naming an existing file fails cleanly."""
import tempfile
import unittest
from pathlib import Path

from tests.test_release_assets import CURRENT_VERSION
from tests.test_release_check_tag import ROOT, load_release


class BuildTargetFileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = load_release()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.target = Path(temporary.name) / "assets"
        self.target.write_text("not a folder\n", encoding="utf-8")

    def test_build_rejects_file_target(self):
        with self.assertRaises(ValueError) as raised:
            self.release.build_assets(ROOT, CURRENT_VERSION, self.target)
        self.assertIn("not a folder", str(raised.exception))

    def test_build_failure_status(self):
        status = self.release.main(["build", CURRENT_VERSION, str(self.target)], root=ROOT)
        self.assertEqual(status, 1)
        self.assertEqual(self.target.read_text(encoding="utf-8"), "not a folder\n")


if __name__ == "__main__":
    unittest.main()
