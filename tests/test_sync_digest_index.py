#!/usr/bin/env python3
"""Cover the per-version digest index that sync.py maintains.

The index maps each released version to the digests of its policy and
shared gate files. A report matches an adopter's files against it to name
the adopted version. These tests build a synthetic tree, so a failure here
belongs to the index logic and not to the repository contents.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# scripts/ is never on the path, so the file lists come from the module
# that defines them rather than a restated copy.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import sync

REPO_ROOT = Path(__file__).resolve().parent.parent
SYNC = REPO_ROOT / "scripts" / "sync.py"
INDEX_NAME = "policy-digests.json"
FIRST_VERSION = "1.2.0"
SECOND_VERSION = "1.3.0"
SHA256_HEX_LENGTH = 64


def run_sync(cwd: Path, *args) -> subprocess.CompletedProcess:
    """Run the sync.py copy inside `cwd` with the given flags."""
    return subprocess.run(
        [sys.executable, str(cwd / "scripts" / "sync.py"), *args],
        capture_output=True, text=True, check=False)


def write_changelog(root: Path, version: str) -> None:
    """Write a changelog whose newest release heading names `version`."""
    (root / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [{version}] (2026-01-01)\n\n### Added\n- Item.\n",
        encoding="utf-8")


def read_index(root: Path) -> dict:
    """Return the parsed digest index of the synthetic tree."""
    return json.loads((root / INDEX_NAME).read_text(encoding="utf-8"))


class IndexFixture(unittest.TestCase):
    """A synthetic source repository with an empty digest index."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "scripts").mkdir()
        (self.root / "scripts" / "sync.py").write_text(
            SYNC.read_text(encoding="utf-8"), encoding="utf-8")
        (self.root / "AGENTS.md").write_text("# Policy\n", encoding="utf-8")
        tracked = list(sync.ADOPTER_POLICY_FILES) + list(sync.SHARED_FILES)
        for name in tracked:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {name}\nbody = 1\n", encoding="utf-8")
        write_changelog(self.root, FIRST_VERSION)
        (self.root / INDEX_NAME).write_text(
            json.dumps({"versions": {}}) + "\n", encoding="utf-8")


class WriteIndexTest(IndexFixture):
    """A plain sync run records the current version's digests."""

    def test_sync_records_the_current_version(self):
        result = run_sync(self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        entry = read_index(self.root)["versions"][FIRST_VERSION]
        shared_name = sync.SHARED_FILES[0]
        expected = hashlib.sha256(
            f"# {shared_name}\nbody = 1\n".encode("utf-8")).hexdigest()
        self.assertEqual(entry["shared"][shared_name], expected)
        self.assertEqual(sorted(entry["shared"]), sorted(sync.SHARED_FILES))

    def test_sync_records_the_policy_files(self):
        run_sync(self.root)
        entry = read_index(self.root)["versions"][FIRST_VERSION]
        expected = hashlib.sha256(b"# Policy\n").hexdigest()
        self.assertEqual(entry["policy"]["AGENTS.md"], expected)
        self.assertIn("docs/agent-policy/adoption.md", entry["policy"])

    def test_the_orientation_stub_stays_out_of_the_index(self):
        """Every adopter rewrites the orientation file, so it never matches."""
        run_sync(self.root)
        entry = read_index(self.root)["versions"][FIRST_VERSION]
        self.assertNotIn("docs/project-orientation.md", entry["policy"])

    def test_a_new_version_keeps_the_earlier_entry(self):
        run_sync(self.root)
        before = read_index(self.root)["versions"][FIRST_VERSION]
        write_changelog(self.root, SECOND_VERSION)
        (self.root / sync.SHARED_FILES[0]).write_text(
            "# changed\nbody = 2\n", encoding="utf-8")
        result = run_sync(self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        versions = read_index(self.root)["versions"]
        self.assertEqual(versions[FIRST_VERSION], before)
        self.assertNotEqual(versions[SECOND_VERSION], before)

    def test_a_tree_without_an_index_gains_none(self):
        """Adopters copy sync.py. Only the source repository holds an index."""
        (self.root / INDEX_NAME).unlink()
        result = run_sync(self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / INDEX_NAME).exists())


class CheckIndexTest(IndexFixture):
    """--check fails when the index no longer describes the tree."""

    def setUp(self):
        super().setUp()
        run_sync(self.root)

    def test_a_current_index_passes(self):
        result = run_sync(self.root, "--check")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_changed_shared_file_fails(self):
        (self.root / sync.SHARED_FILES[0]).write_text(
            "# changed\nbody = 2\n", encoding="utf-8")
        result = run_sync(self.root, "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn(INDEX_NAME, result.stderr)

    def test_a_changed_policy_document_fails(self):
        (self.root / "docs/agent-policy/github.md").write_text(
            "# changed\n", encoding="utf-8")
        result = run_sync(self.root, "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn(INDEX_NAME, result.stderr)

    def test_a_version_without_an_entry_fails(self):
        write_changelog(self.root, SECOND_VERSION)
        result = run_sync(self.root, "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn(SECOND_VERSION, result.stderr)

    def test_an_unreadable_changelog_version_fails(self):
        (self.root / "CHANGELOG.md").write_text(
            "# Changelog\n\nNo release heading.\n", encoding="utf-8")
        result = run_sync(self.root, "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("CHANGELOG.md", result.stderr)

    def test_an_invalid_index_fails(self):
        (self.root / INDEX_NAME).write_text("not json\n", encoding="utf-8")
        result = run_sync(self.root, "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn(INDEX_NAME, result.stderr)

    def test_a_tree_without_an_index_passes(self):
        (self.root / INDEX_NAME).unlink()
        result = run_sync(self.root, "--check")
        self.assertEqual(result.returncode, 0, result.stderr)


def run_git(cwd: Path, *args) -> None:
    """Run one Git command in the synthetic tree with a fixed identity."""
    identity = ["-c", "user.name=Fixture", "-c",
                "user.email=fixture@example.invalid"]
    subprocess.run(["git", "-C", str(cwd), *identity, *args],
                   capture_output=True, text=True, check=True)


class BackfillIndexTest(IndexFixture):
    """--backfill-digests adds an entry for every version in Git history."""

    def setUp(self):
        super().setUp()
        run_git(self.root, "init", "--quiet")
        run_sync(self.root, "--write-shared")
        run_git(self.root, "add", "--all")
        run_git(self.root, "commit", "--quiet", "-m", "first")
        self.first_shared = json.loads(
            (self.root / "shared-files.json").read_text(encoding="utf-8"))
        write_changelog(self.root, SECOND_VERSION)
        (self.root / "AGENTS.md").write_text("# Policy two\n", encoding="utf-8")
        (self.root / sync.SHARED_FILES[0]).write_text(
            "# changed\nbody = 2\n", encoding="utf-8")
        run_sync(self.root, "--write-shared")
        run_git(self.root, "add", "--all")
        run_git(self.root, "commit", "--quiet", "-m", "second")

    def test_backfill_adds_every_committed_version(self):
        result = run_sync(self.root, "--backfill-digests")
        self.assertEqual(result.returncode, 0, result.stderr)
        versions = read_index(self.root)["versions"]
        self.assertEqual(sorted(versions), [FIRST_VERSION, SECOND_VERSION])

    def test_backfill_hashes_each_revision_own_policy(self):
        run_sync(self.root, "--backfill-digests")
        versions = read_index(self.root)["versions"]
        first = hashlib.sha256(b"# Policy\n").hexdigest()
        second = hashlib.sha256(b"# Policy two\n").hexdigest()
        self.assertEqual(versions[FIRST_VERSION]["policy"]["AGENTS.md"], first)
        self.assertEqual(
            versions[SECOND_VERSION]["policy"]["AGENTS.md"], second)
        self.assertNotIn("docs/project-orientation.md",
                         versions[FIRST_VERSION]["policy"])

    def test_backfill_reuses_each_revision_own_shared_manifest(self):
        run_sync(self.root, "--backfill-digests")
        versions = read_index(self.root)["versions"]
        self.assertEqual(
            versions[FIRST_VERSION]["shared"], self.first_shared["shared"])
        self.assertNotEqual(
            versions[SECOND_VERSION]["shared"], self.first_shared["shared"])

    def test_backfill_keeps_an_existing_entry(self):
        marker = {"policy": {"AGENTS.md": "0" * SHA256_HEX_LENGTH}, "shared": {}}
        (self.root / INDEX_NAME).write_text(
            json.dumps({"versions": {FIRST_VERSION: marker}}),
            encoding="utf-8")
        result = run_sync(self.root, "--backfill-digests")
        self.assertEqual(result.returncode, 0, result.stderr)
        versions = read_index(self.root)["versions"]
        self.assertEqual(versions[FIRST_VERSION], marker)
        self.assertIn(SECOND_VERSION, versions)

    def test_backfill_twice_changes_nothing(self):
        run_sync(self.root, "--backfill-digests")
        before = (self.root / INDEX_NAME).read_text(encoding="utf-8")
        run_sync(self.root, "--backfill-digests")
        after = (self.root / INDEX_NAME).read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_backfill_without_an_index_fails(self):
        (self.root / INDEX_NAME).unlink()
        result = run_sync(self.root, "--backfill-digests")
        self.assertEqual(result.returncode, 1)
        self.assertIn(INDEX_NAME, result.stderr)


class LiveIndexTest(unittest.TestCase):
    """This repository's committed index describes its current release."""

    def test_the_committed_index_matches_this_tree(self):
        self.assertTrue((REPO_ROOT / INDEX_NAME).is_file())
        result = run_sync(REPO_ROOT, "--check")
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
