#!/usr/bin/env python3
"""Check the release files, the checksum file, and the asset folder check."""
import hashlib
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from tests.test_release_check_tag import ROOT, load_release

sys.path.insert(0, str(ROOT / "scripts"))
import sync

CURRENT_VERSION = sync.read_release_version(
    (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))


class BuildAssetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = load_release()
        cls.temporary = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temporary.name) / "assets"
        cls.release.build_assets(ROOT, CURRENT_VERSION, cls.folder)
        cls.policy, cls.archive, cls.digests = (
            cls.folder / name for name in cls.release.asset_names(CURRENT_VERSION))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_folder_holds_exactly_the_three_assets(self):
        names = sorted(path.name for path in self.folder.iterdir())
        self.assertEqual(names, sorted(self.release.asset_names(CURRENT_VERSION)))

    def test_policy_asset_matches_the_adoptable_policy(self):
        expected = sync.adoptable_content(sync.policy_bytes(ROOT).decode("ascii"))
        # Bytes keep a Windows checkout's CRLF endings intact on both sides.
        self.assertEqual(self.policy.read_bytes(), expected.encode("ascii"))

    def test_archive_holds_the_shared_gate_files_and_manifest(self):
        with tarfile.open(self.archive, "r:gz") as archive:
            members = archive.getmembers()
            names = [member.name for member in members]
            self.assertEqual(names, sorted(sync.SHARED_FILES + [sync.SHARED_MANIFEST]))
            for member in members:
                with self.subTest(name=member.name):
                    self.assertTrue(member.isfile())
                    self.assertEqual((member.mtime, member.uid, member.gid), (0, 0, 0))
                    content = archive.extractfile(member).read()
                    self.assertEqual(content, (ROOT / member.name).read_bytes())

    def test_digest_asset_matches_the_index_entry(self):
        recorded = json.loads(self.digests.read_text(encoding="utf-8"))
        index = sync.read_digest_index(ROOT)
        self.assertEqual(recorded, {"version": CURRENT_VERSION, **index[CURRENT_VERSION]})

    def test_rebuild_produces_identical_bytes(self):
        with tempfile.TemporaryDirectory() as other:
            second = Path(other) / "assets"
            self.release.build_assets(ROOT, CURRENT_VERSION, second)
            for name in self.release.asset_names(CURRENT_VERSION):
                with self.subTest(name=name):
                    self.assertEqual((self.folder / name).read_bytes(),
                                     (second / name).read_bytes())

    def test_build_refuses_a_non_empty_folder(self):
        with self.assertRaises(ValueError):
            self.release.build_assets(ROOT, CURRENT_VERSION, self.folder)

    def test_build_refuses_a_version_without_a_digest_entry(self):
        with tempfile.TemporaryDirectory() as other:
            with self.assertRaises(ValueError):
                self.release.build_assets(ROOT, "999.0.0", Path(other) / "assets")


class AssetFolderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = load_release()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        for name in self.release.asset_names("2.27.0"):
            (self.folder / name).write_bytes(name.encode("ascii"))

    def test_complete_folder_has_no_problems(self):
        self.assertEqual(self.release.asset_problems(self.folder, "2.27.0"), [])

    def test_missing_and_extra_files_are_reported(self):
        (self.folder / self.release.asset_names("2.27.0")[0]).unlink()
        (self.folder / "stray.txt").write_bytes(b"x")
        problems = self.release.asset_problems(self.folder, "2.27.0")
        self.assertEqual(len(problems), 2, problems)

    def test_bundle_is_required_only_on_request(self):
        bundle = self.release.bundle_name("2.27.0")
        problems = self.release.asset_problems(self.folder, "2.27.0", require_bundle=True)
        self.assertTrue(any(bundle in item for item in problems), problems)
        (self.folder / bundle).write_bytes(b"{}")
        self.assertEqual(
            self.release.asset_problems(self.folder, "2.27.0", require_bundle=True), [])
        self.assertTrue(self.release.asset_problems(self.folder, "2.27.0"))

    def test_checksums_list_every_other_file_sorted(self):
        output = self.release.write_checksums(self.folder)
        self.assertEqual(output.name, "SHA256SUMS.txt")
        lines = output.read_text(encoding="utf-8").splitlines()
        names = sorted(self.release.asset_names("2.27.0"))
        expected = [
            f"{hashlib.sha256(name.encode('ascii')).hexdigest()}  {name}" for name in names]
        self.assertEqual(lines, expected)
        rewritten = self.release.write_checksums(self.folder)
        self.assertEqual(rewritten.read_text(encoding="utf-8").splitlines(), expected)


if __name__ == "__main__":
    unittest.main()
