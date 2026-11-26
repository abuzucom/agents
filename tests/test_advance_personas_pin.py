#!/usr/bin/env python3
"""The personas pin update rewrites every pin site and the caller digest."""
import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import advance_personas_pin

NEW_COMMIT = "a" * 40
NEW_VERSION = "1.1.0"
USAGE_FAILURE = 2
STATE_FAILURE = 1


class AdvancePersonasPinTest(unittest.TestCase):
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

    def run_update(self, arguments: list) -> tuple:
        """Run main() and return the exit code and stderr."""
        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            code = advance_personas_pin.main(arguments, root=self.root)
        return code, stderr.getvalue()

    def read(self, name: str) -> str:
        """Return one fixture file as text."""
        return (self.root / name).read_text(encoding="utf-8")

    def test_update_rewrites_every_pin(self):
        code, stderr = self.run_update([NEW_VERSION, NEW_COMMIT])
        self.assertEqual(code, 0, stderr)
        for name in advance_personas_pin.PIN_FILES:
            with self.subTest(name=name):
                text = self.read(name)
                self.assertNotIn(self.old_commit, text)
                self.assertIn(NEW_COMMIT, text)
        self.assertEqual(advance_personas_pin.current_pin(self.root), NEW_COMMIT)

    def test_update_rewrites_version_comments(self):
        self.run_update([NEW_VERSION, NEW_COMMIT])
        for name in advance_personas_pin.VERSION_FILES:
            with self.subTest(name=name):
                self.assertIn(NEW_VERSION, self.read(name))

    def test_manifest_digest_matches_caller(self):
        self.run_update([NEW_VERSION, NEW_COMMIT])
        manifest = json.loads(self.read(advance_personas_pin.MANIFEST))
        entry = manifest["pull_request_target"][advance_personas_pin.CALLER]
        caller = (self.root / advance_personas_pin.CALLER).read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(entry["sha256"], hashlib.sha256(caller).hexdigest())

    def test_repeat_update_is_idempotent(self):
        self.run_update([NEW_VERSION, NEW_COMMIT])
        before = {name: self.read(name) for name in advance_personas_pin.PIN_FILES}
        code, stderr = self.run_update([NEW_VERSION, NEW_COMMIT])
        self.assertEqual(code, 0, stderr)
        after = {name: self.read(name) for name in advance_personas_pin.PIN_FILES}
        self.assertEqual(before, after)

    def test_invalid_arguments_rejected(self):
        for arguments in (["1.1", NEW_COMMIT], ["01.1.0", NEW_COMMIT],
                          [NEW_VERSION, "a" * 39], [NEW_VERSION, "A" * 40],
                          [NEW_VERSION, "-" + "a" * 39]):
            with self.subTest(arguments=arguments):
                code, stderr = self.run_update(arguments)
                self.assertEqual(code, USAGE_FAILURE)
                self.assertIn("error:", stderr)

    def test_divergent_pins_refused(self):
        name = advance_personas_pin.PIN_FILES[0]
        path = self.root / name
        path.write_text(path.read_text(encoding="utf-8").replace(self.old_commit, "b" * 40, 1),
                        encoding="utf-8")
        before = {item: self.read(item) for item in advance_personas_pin.PIN_FILES}
        code, stderr = self.run_update([NEW_VERSION, NEW_COMMIT])
        self.assertEqual(code, STATE_FAILURE)
        self.assertIn("error:", stderr)
        after = {item: self.read(item) for item in advance_personas_pin.PIN_FILES}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
