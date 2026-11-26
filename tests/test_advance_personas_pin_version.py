#!/usr/bin/env python3
"""A version change at the current personas commit still rewrites the version.

A personas tag can move to a new version name on the same commit. The update
must rewrite every version phrase. A repeat with both values unchanged must
change no file.
"""
import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import advance_personas_pin

NEW_VERSION = "1.0.1"


class SameCommitVersionTest(unittest.TestCase):
    """Run the update with the current commit and a new version."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in advance_personas_pin.PIN_FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.commit = advance_personas_pin.current_pin(self.root)
        self.version = advance_personas_pin.current_version(self.root)

    def run_update(self, version: str) -> int:
        """Run the update at the current commit and return the exit code."""
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return advance_personas_pin.main([version, self.commit], root=self.root)

    def test_same_commit_new_version_rewritten(self):
        self.assertEqual(self.run_update(NEW_VERSION), 0)
        self.assertEqual(advance_personas_pin.current_version(self.root), NEW_VERSION)
        for name in advance_personas_pin.VERSION_FILES:
            with self.subTest(name=name):
                text = (self.root / name).read_bytes().decode("utf-8")
                self.assertIn(NEW_VERSION, text)
                self.assertNotIn(f"agents-personas {self.version}.", text)

    def test_unchanged_state_writes_nothing(self):
        before = {name: (self.root / name).read_bytes() for name in advance_personas_pin.PIN_FILES}
        self.assertEqual(self.run_update(self.version), 0)
        after = {name: (self.root / name).read_bytes() for name in advance_personas_pin.PIN_FILES}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
