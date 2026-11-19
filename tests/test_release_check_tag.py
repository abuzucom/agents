#!/usr/bin/env python3
"""Check that a release tag must match the changelog and the digest index."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE_PATH = ROOT / "scripts" / "release.py"
CHANGELOG_TEXT = (
    "# Changelog\n\n"
    "## [2.27.0] (2026-11-18)\n\n### Added\n- New item.\n\n"
    "## [2.26.2] (2026-11-17)\n\n### Fixed\n- Old item.\n"
)
DIGEST_ENTRY = {"policy": {"AGENTS.md": "a" * 64}, "shared": {}}


def load_release():
    """Load scripts/release.py by path for isolated tests."""
    spec = importlib.util.spec_from_file_location("release_check_tag", RELEASE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_fixture(root: Path, changelog: str, versions: dict) -> None:
    """Write a changelog and a digest index into one fixture root."""
    (root / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    body = {"note": "fixture", "versions": versions}
    (root / "policy-digests.json").write_text(json.dumps(body), encoding="utf-8")


class CheckTagTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = load_release()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        write_fixture(self.root, CHANGELOG_TEXT, {"2.27.0": DIGEST_ENTRY})

    def test_matching_tag_has_no_problems(self):
        self.assertEqual(self.release.tag_problems("v2.27.0", self.root), [])

    def test_tag_without_prefix_is_rejected(self):
        problems = self.release.tag_problems("2.27.0", self.root)
        self.assertTrue(any("does not start with 'v'" in item for item in problems))

    def test_tag_with_a_suffix_or_bad_shape_is_rejected(self):
        for tag in ("v2.27.0-rc.1", "v2.27", "v02.27.0", "v2.27.0.1", "v"):
            with self.subTest(tag=tag):
                problems = self.release.tag_problems(tag, self.root)
                self.assertTrue(any("X.Y.Z" in item for item in problems), problems)

    def test_tag_that_differs_from_the_changelog_is_rejected(self):
        problems = self.release.tag_problems("v2.26.2", self.root)
        self.assertTrue(any("CHANGELOG.md" in item and "2.27.0" in item
                            for item in problems), problems)

    def test_missing_digest_entry_is_rejected(self):
        write_fixture(self.root, CHANGELOG_TEXT, {"2.26.2": DIGEST_ENTRY})
        problems = self.release.tag_problems("v2.27.0", self.root)
        self.assertTrue(any("policy-digests.json" in item for item in problems), problems)

    def test_missing_files_are_reported(self):
        (self.root / "CHANGELOG.md").unlink()
        (self.root / "policy-digests.json").unlink()
        problems = self.release.tag_problems("v2.27.0", self.root)
        self.assertTrue(any("CHANGELOG.md" in item for item in problems), problems)
        self.assertTrue(any("policy-digests.json" in item for item in problems), problems)

    def test_main_returns_failure_for_a_bad_tag(self):
        self.assertEqual(self.release.main(["check-tag", "v2.27.0"], root=self.root), 0)
        self.assertEqual(self.release.main(["check-tag", "v9.9.9"], root=self.root), 1)


class ParseVersionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = load_release()

    def test_valid_versions_parse_to_integers(self):
        self.assertEqual(self.release.parse_version("2.27.0"), (2, 27, 0))
        self.assertEqual(self.release.parse_version("10.0.11"), (10, 0, 11))

    def test_invalid_versions_raise(self):
        for text in ("", "2.27", "2.27.0-rc.1", "02.1.0", "2.x.0", " 2.27.0"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    self.release.parse_version(text)


if __name__ == "__main__":
    unittest.main()
