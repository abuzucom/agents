#!/usr/bin/env python3
"""Check that release notes collect the changelog since the last stable release."""
import tempfile
import unittest
from pathlib import Path

from tests.test_release_check_tag import load_release

CHANGELOG_TEXT = (
    "# Changelog\n\nPreamble text.\n\n"
    "## [2.28.0] (2026-11-20)\n\n### Added\n- Item C.\n\n"
    "## [2.27.1] (2026-11-19)\n\n### Fixed\n- Item B.\n\n"
    "## [2.26.2] (2026-11-17)\n\n### Fixed\n- Item A.\n"
)


class ChangelogSectionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = load_release()

    def collect(self, version: str, since: str | None) -> str:
        """Return the collected sections for one version and start point."""
        return self.release.changelog_sections(CHANGELOG_TEXT, version, since)

    def test_without_a_previous_stable_only_the_own_section_appears(self):
        text = self.collect("2.28.0", None)
        self.assertIn("Item C.", text)
        self.assertNotIn("Item B.", text)
        self.assertNotIn("Preamble", text)

    def test_sections_newer_than_the_previous_stable_appear_newest_first(self):
        text = self.collect("2.28.0", "2.26.2")
        self.assertIn("## [2.28.0] (2026-11-20)", text)
        self.assertIn("## [2.27.1] (2026-11-19)", text)
        self.assertLess(text.index("Item C."), text.index("Item B."))
        self.assertNotIn("Item A.", text)

    def test_previous_stable_absent_from_the_changelog_compares_by_number(self):
        text = self.collect("2.28.0", "2.27.0")
        self.assertIn("Item C.", text)
        self.assertIn("Item B.", text)
        self.assertNotIn("Item A.", text)

    def test_sections_newer_than_the_release_are_excluded(self):
        text = self.collect("2.27.1", "2.26.2")
        self.assertIn("Item B.", text)
        self.assertNotIn("Item C.", text)

    def test_previous_stable_not_older_than_the_release_is_rejected(self):
        for since in ("2.28.0", "3.0.0"):
            with self.subTest(since=since):
                with self.assertRaises(ValueError):
                    self.collect("2.28.0", since)

    def test_missing_release_section_is_rejected(self):
        with self.assertRaises(ValueError):
            self.collect("2.27.0", None)


class ReleaseNotesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = load_release()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "CHANGELOG.md").write_text(CHANGELOG_TEXT, encoding="utf-8")

    def test_notes_end_with_the_adoption_block(self):
        notes = self.release.release_notes(self.root, "2.28.0", "2.26.2")
        self.assertIn("Item C.", notes)
        self.assertIn("## Adopting this release", notes)
        self.assertLess(notes.index("Item C."), notes.index("## Adopting this release"))
        for name in self.release.asset_names("2.28.0"):
            with self.subTest(name=name):
                self.assertIn(name, notes)
        self.assertIn("SHA256SUMS.txt", notes)
        self.assertIn("gh attestation verify", notes)

    def test_notes_are_ascii(self):
        notes = self.release.release_notes(self.root, "2.28.0", None)
        notes.encode("ascii")

    def test_main_writes_notes_and_accepts_a_tag_as_since(self):
        output = self.root / "notes.md"
        status = self.release.main(
            ["notes", "2.28.0", str(output), "--since", "v2.26.2"], root=self.root)
        self.assertEqual(status, 0)
        self.assertIn("Item B.", output.read_text(encoding="utf-8"))

    def test_main_rejects_a_malformed_since(self):
        output = self.root / "notes.md"
        status = self.release.main(
            ["notes", "2.28.0", str(output), "--since", "latest"], root=self.root)
        self.assertEqual(status, 1)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
