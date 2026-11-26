#!/usr/bin/env python3
"""The personas pin update refuses any pin site that names another commit.

A `personas_ref` or test constant that differs from the `uses:` pins would
let a wrapper run one revision while it loads policy from another.
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

NEW_COMMIT = "a" * 40
STRAY_COMMIT = "b" * 40
STATE_FAILURE = 1


class DivergentReferenceTest(unittest.TestCase):
    """Run the update against a copy of the real pin sites."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in advance_personas_pin.PIN_FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.old_commit = advance_personas_pin.current_pin(self.root)

    def replace_once(self, name: str, old: str, new: str) -> None:
        """Replace the first occurrence of one string in one fixture file."""
        path = self.root / name
        content = path.read_bytes().decode("utf-8")
        self.assertIn(old, content)
        path.write_bytes(content.replace(old, new, 1).encode("utf-8"))

    def assert_refused_unchanged(self) -> None:
        """Assert the update exits 1 and leaves every pin site as it was."""
        before = {name: (self.root / name).read_bytes() for name in advance_personas_pin.PIN_FILES}
        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            code = advance_personas_pin.main(["1.1.0", NEW_COMMIT], root=self.root)
        self.assertEqual(code, STATE_FAILURE, stderr.getvalue())
        self.assertIn("error:", stderr.getvalue())
        after = {name: (self.root / name).read_bytes() for name in advance_personas_pin.PIN_FILES}
        self.assertEqual(before, after)

    def test_divergent_personas_ref_refused(self):
        self.replace_once(advance_personas_pin.WORKFLOW_FILES[1],
                          f'personas_ref: "{self.old_commit}"', f'personas_ref: "{STRAY_COMMIT}"')
        self.assert_refused_unchanged()

    def test_divergent_test_constant_refused(self):
        self.replace_once(advance_personas_pin.TEST_FILES[0],
                          f'PINNED_COMMIT = "{self.old_commit}"', f'PINNED_COMMIT = "{STRAY_COMMIT}"')
        self.assert_refused_unchanged()

    def test_written_bytes_keep_line_endings(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            advance_personas_pin.main(["1.1.0", NEW_COMMIT], root=self.root)
        for name in advance_personas_pin.PIN_FILES:
            with self.subTest(name=name):
                content = (self.root / name).read_bytes()
                self.assertEqual(b"\r\n" in content, b"\r\n" in (ROOT / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
