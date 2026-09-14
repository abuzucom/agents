"""Test the blocking SemVer changelog checker."""
import importlib.util
import unittest
from pathlib import Path

CHECKER_PATH = Path(__file__).resolve().parent.parent / "scripts" / "check_changelog.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_changelog", CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load_checker()


class ChangelogCheckerTest(unittest.TestCase):
    """Exercise changelog rules through the checker API."""

    def test_valid_versioned_changelog_passes(self):
        text = """# Changelog\n\n## [2.0.0] (2026-09-13)\n\n### Added\n- Add linked policy loading.\n\n## [1.14.0] (2026-09-12)\n\n### Fixed\n- Fix a gate.\n"""
        self.assertEqual(checker.find_violations(text), [])

    def test_unreleased_heading_fails(self):
        text = "# Changelog\n\n## [Unreleased]\n\n- Pending change.\n"
        findings = checker.find_violations(text)
        self.assertTrue(any("Unreleased" in finding for finding in findings))

    def test_invalid_version_order_fails(self):
        text = """# Changelog\n\n## [1.0.0] (2026-09-13)\n\n- New.\n\n## [2.0.0] (2026-09-12)\n\n- Old.\n"""
        findings = checker.find_violations(text)
        self.assertTrue(any("descending" in finding for finding in findings))

    def test_missing_versioned_entry_fails(self):
        text = "# Changelog\n\n## [2.0.0] (2026-09-13)\n"
        findings = checker.find_violations(text)
        self.assertTrue(any("entry" in finding for finding in findings))

    def test_malformed_changelog_fails(self):
        findings = checker.find_violations("not a changelog")
        self.assertTrue(any("no versioned" in finding for finding in findings))


if __name__ == "__main__":
    unittest.main()
