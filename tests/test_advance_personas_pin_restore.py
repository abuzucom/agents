#!/usr/bin/env python3
"""A failed restore after a failed replace reports a partial write.

The update stages every pin site, then replaces each one. When a replace
fails, the update restores each file it already replaced. A restore that
also fails leaves mixed pins. The update then exits 3, names each file it
could not restore, and gives the git recovery command. It never claims
that no file changed.
"""
import contextlib
import io
import os
import pathlib
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
PARTIAL_FAILURE = 3
FAILING_REPLACE_CALL = 3


class RestoreFailureTest(unittest.TestCase):
    """Run the update against a copy of the real pin sites."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in advance_personas_pin.PIN_FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def test_failed_restore_reports_partial(self):
        real_replace = os.replace
        real_write_bytes = pathlib.Path.write_bytes
        replaced = []

        def fail_third(source, target):
            if len(replaced) + 1 == FAILING_REPLACE_CALL:
                raise OSError("disk full")
            real_replace(source, target)
            replaced.append(Path(target))

        def fail_first_restore(path, data):
            if replaced and Path(path) == replaced[0]:
                raise OSError("read-only file system")
            return real_write_bytes(path, data)

        stderr = io.StringIO()
        with patch.object(advance_personas_pin.os, "replace", side_effect=fail_third), \
                patch.object(pathlib.Path, "write_bytes", fail_first_restore), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            code = advance_personas_pin.main(["1.1.0", NEW_COMMIT], root=self.root)
        message = stderr.getvalue()
        self.assertEqual(code, PARTIAL_FAILURE, message)
        unrestored = replaced[0].relative_to(self.root).as_posix()
        self.assertIn(unrestored, message)
        self.assertIn("git checkout --", message)
        self.assertNotIn("No file changed", message)
        self.assertNotIn("original bytes", message)


if __name__ == "__main__":
    unittest.main()
