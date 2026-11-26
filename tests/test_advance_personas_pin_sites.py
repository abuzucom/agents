#!/usr/bin/env python3
"""The personas pin update requires every pin site and writes all or nothing.

A missing `uses:` pin, `personas_ref`, test constant, or manifest key stops
the update before any write. A failed replacement restores every original.
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import advance_personas_pin

NEW_COMMIT = "a" * 40
STATE_FAILURE = 1
FAILING_REPLACE_CALL = 3


class PinSiteHarness(unittest.TestCase):
    """Copy the real pin sites into a temporary root."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in advance_personas_pin.PIN_FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.old_commit = advance_personas_pin.current_pin(self.root)

    def snapshot(self) -> dict:
        """Return the bytes of every pin site."""
        return {name: (self.root / name).read_bytes() for name in advance_personas_pin.PIN_FILES}

    def run_update(self) -> tuple:
        """Run the update and return the exit code and stderr."""
        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            code = advance_personas_pin.main(["1.1.0", NEW_COMMIT], root=self.root)
        return code, stderr.getvalue()

    def drop_line(self, name: str, marker: str) -> None:
        """Remove the first line of one fixture file that contains a marker."""
        path = self.root / name
        lines = path.read_bytes().decode("utf-8").splitlines(keepends=True)
        index = next(i for i, line in enumerate(lines) if marker in line)
        del lines[index]
        path.write_bytes("".join(lines).encode("utf-8"))


class MissingPinSiteTest(PinSiteHarness):
    """A missing pin site exits 1 and changes no file."""

    def assert_refused_unchanged(self) -> None:
        """Assert the update exits 1 and leaves every pin site as it was."""
        before = self.snapshot()
        code, stderr = self.run_update()
        self.assertEqual(code, STATE_FAILURE, stderr)
        self.assertIn("error:", stderr)
        self.assertEqual(self.snapshot(), before)

    def test_missing_personas_ref_refused(self):
        self.drop_line(advance_personas_pin.CALLER, "personas_ref:")
        self.assert_refused_unchanged()

    def test_missing_uses_pin_refused(self):
        self.drop_line(advance_personas_pin.WORKFLOW_FILES[1], "uses: abuzucom/agents-personas")
        self.assert_refused_unchanged()

    def test_missing_test_constant_refused(self):
        name = advance_personas_pin.TEST_FILES[0]
        path = self.root / name
        content = path.read_bytes().decode("utf-8")
        path.write_bytes(content.replace("PINNED_COMMIT = ", "OTHER_COMMIT = ", 1).encode("utf-8"))
        self.assert_refused_unchanged()

    def test_missing_manifest_key_refused(self):
        self.drop_line(advance_personas_pin.MANIFEST, "havel-privacy-review.yml@")
        self.assert_refused_unchanged()


class AtomicWriteTest(PinSiteHarness):
    """A failed replacement restores every pin site. A replacement keeps each mode."""

    @unittest.skipIf(os.name == "nt", "Windows has no POSIX permission bits")
    def test_replace_keeps_file_mode(self):
        modes = {name: (self.root / name).stat().st_mode for name in advance_personas_pin.PIN_FILES}
        code, stderr = self.run_update()
        self.assertEqual(code, 0, stderr)
        for name, mode in modes.items():
            with self.subTest(name=name):
                self.assertEqual((self.root / name).stat().st_mode, mode)

    def test_failed_replace_restores_originals(self):
        before = self.snapshot()
        real_replace = os.replace
        calls = []

        def fail_third(source, target):
            calls.append(target)
            if len(calls) == FAILING_REPLACE_CALL:
                raise OSError("disk full")
            real_replace(source, target)

        with patch.object(advance_personas_pin.os, "replace", side_effect=fail_third):
            code, stderr = self.run_update()
        self.assertEqual(code, STATE_FAILURE, stderr)
        self.assertIn("restored", stderr)
        self.assertEqual(self.snapshot(), before)
        leftovers = [path for path in self.root.rglob("*") if path.name.startswith(".pin-")]
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
