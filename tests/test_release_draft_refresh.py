#!/usr/bin/env python3
"""Check that the upload step rechecks the draft and refreshes its notes."""
import unittest

from tests.test_release_draft_lookup import find_step
from tests.test_release_workflow_wiring import load_workflow

UPLOAD_STEP = "Upload to draft release"
DRAFT_GUARD = "require_draft"


def read_upload_lines() -> list[str]:
    """Return the stripped lines of the upload step script."""
    job = load_workflow()["jobs"]["release"]
    return [line.strip() for line in find_step(job, UPLOAD_STEP)["run"].splitlines()]


def find_line_index(lines: list[str], fragment: str) -> int:
    """Return the index of the first line holding the fragment."""
    for index, line in enumerate(lines):
        if fragment in line:
            return index
    raise AssertionError(f"no upload step line holds {fragment!r}")


class DraftRecheckTest(unittest.TestCase):
    def test_guard_reads_the_draft_state_and_fails_closed(self):
        text = "\n".join(read_upload_lines())
        self.assertIn(f"{DRAFT_GUARD}()", text)
        self.assertIn("--json isDraft", text)
        self.assertIn("exit 1", text)

    def test_guard_runs_before_each_upload(self):
        lines = read_upload_lines()
        upload = find_line_index(lines, "gh release upload")
        self.assertEqual(lines[upload - 1], DRAFT_GUARD)

    def test_guard_runs_before_the_notes_refresh(self):
        lines = read_upload_lines()
        edit = find_line_index(lines, "gh release edit")
        guard_calls = [index for index, line in enumerate(lines) if line == DRAFT_GUARD]
        self.assertTrue(any(index < edit for index in guard_calls))


class DraftNotesRefreshTest(unittest.TestCase):
    def test_existing_draft_receives_the_current_notes(self):
        text = "\n".join(read_upload_lines())
        self.assertIn("releases/generate-notes", text)
        self.assertIn('gh release edit "$tag" --repo "$repo" --notes-file', text)

    def test_refreshed_notes_start_with_the_built_notes(self):
        lines = read_upload_lines()
        built = find_line_index(lines, 'cat "$RUNNER_TEMP/release-notes.md"')
        generated = find_line_index(lines, 'printf \'%s\\n\' "$generated"')
        self.assertLess(built, generated)


if __name__ == "__main__":
    unittest.main()
