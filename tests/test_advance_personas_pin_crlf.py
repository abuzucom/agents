#!/usr/bin/env python3
"""The pin update records the digest of the caller as Git stores it.

The trusted compliance scan hashes the caller blob. `text: auto` stores that
blob with LF line endings. A Windows checkout holds CRLF instead, so the
update must hash the caller after normalizing CRLF to LF.
"""
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
CRLF = b"\r\n"
LF = b"\n"


class CrlfCheckoutDigestTest(unittest.TestCase):
    """Run the update against a CRLF copy of the real pin sites."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in advance_personas_pin.PIN_FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
            content = target.read_bytes().replace(CRLF, LF)
            target.write_bytes(content.replace(LF, CRLF))

    def test_crlf_caller_digest_uses_lf(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = advance_personas_pin.main(["1.1.0", NEW_COMMIT], root=self.root)
        self.assertEqual(code, 0)
        manifest = json.loads((self.root / advance_personas_pin.MANIFEST).read_bytes())
        entry = manifest["pull_request_target"][advance_personas_pin.CALLER]
        caller = (self.root / advance_personas_pin.CALLER).read_bytes()
        self.assertIn(CRLF, caller)
        self.assertEqual(entry["sha256"], hashlib.sha256(caller.replace(CRLF, LF)).hexdigest())


if __name__ == "__main__":
    unittest.main()
