#!/usr/bin/env python3
"""The gate classifies a UNC path from command text without filesystem access.

A UNC path names another host. The gate resolves it lexically and never
reads it. A remote `.yaml`, `.yml`, or `.json` name counts as protected
infrastructure. Device paths such as `\\\\?\\C:\\` and `\\\\.\\` stay on the
local path, except the `UNC` device forms, which also name another host.
"""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CORE_PATH = Path(__file__).resolve().parent.parent / "hooks" / "_gate_core.py"
REMOTE_MANIFESTS = (
    r"\\server\share\manifest.yaml",
    "\\\\server/share/m.json",
    r"\\?\UNC\server\share\m.yml",
    r"\\.\UNC\server\share\m.yaml",
)
LOCAL_DEVICE_PATHS = (r"\\?\C:\repo\notes.txt", r"\\.\pipe\name")
DENY = "deny"


def load_core():
    """Load the gate core by path."""
    spec = importlib.util.spec_from_file_location("gate_core_unc_paths", CORE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UncPathClassificationTest(unittest.TestCase):
    """UNC forms are recognized lexically on every platform."""

    def setUp(self):
        self.core = load_core()

    def test_remote_forms_are_unc(self):
        for path in REMOTE_MANIFESTS:
            with self.subTest(path=path):
                self.assertTrue(self.core.is_unc_path(path))

    def test_local_device_forms_stay_local(self):
        for path in LOCAL_DEVICE_PATHS:
            with self.subTest(path=path):
                self.assertFalse(self.core.is_unc_path(path))

    def test_forward_slash_form_follows_platform(self):
        self.assertTrue(self.core.is_unc_path("//server/share/m.yaml", windows=True))
        self.assertFalse(self.core.is_unc_path("//server/share/m.yaml", windows=False))
        self.assertFalse(self.core.is_unc_path("/srv/share/m.yaml", windows=True))


class UncNoFilesystemAccessTest(unittest.TestCase):
    """No gate check resolves or reads a UNC path from command text."""

    def setUp(self):
        self.core = load_core()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = os.path.realpath(temporary.name)
        real_realpath = os.path.realpath

        def guarded_realpath(path, *args, **kwargs):
            if self.core.is_unc_path(str(path)):
                raise AssertionError(f"realpath reached a UNC path: {path}")
            return real_realpath(path, *args, **kwargs)

        realpath_patch = patch.object(self.core.os.path, "realpath", side_effect=guarded_realpath)
        realpath_patch.start()
        self.addCleanup(realpath_patch.stop)

    def test_remote_manifest_protected_unread(self):
        with patch.object(self.core, "_infrastructure_manifest_text",
                          side_effect=AssertionError("the gate read a UNC path")):
            for path in REMOTE_MANIFESTS:
                with self.subTest(path=path):
                    self.assertTrue(self.core.is_protected_infrastructure_path(path, self.root))

    def test_remote_text_file_unprotected(self):
        with patch.object(self.core, "_infrastructure_manifest_text",
                          side_effect=AssertionError("the gate read a UNC path")):
            self.assertFalse(self.core.is_protected_infrastructure_path(
                r"\\server\share\notes.txt", self.root))

    def test_remote_pages_path_denied(self):
        decision, _reason = self.core.cloudflare_pages_verdict(
            "wrangler", ["pages", "deploy", r"\\server\share\dist", "--project-name", "site"],
            self.root)
        self.assertEqual(decision, DENY)

    def test_remote_write_target_unprotected(self):
        self.assertFalse(self.core._protected_path(r"\\server\share\hooks\gate.py", self.root))


if __name__ == "__main__":
    unittest.main()
