#!/usr/bin/env python3
"""Pin the Claude Stop check for the compaction disclosure block (issue 101).

Claude records each compaction as a `compact_boundary` system entry in the
session transcript. After the last boundary, some assistant text must hold a
fenced block with the first line `COMPACTION TEXT DISCLOSURE`. A missing
block blocks one turn end. An unreadable transcript lets the turn end with a
notice. The hook reads a bounded tail of the transcript.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = REPO_ROOT / "hooks" / "reinject_agents_policy.py"
HOOK_TIMEOUT_SECONDS = 30
DISCLOSURE_MARKER = "COMPACTION TEXT DISCLOSURE"
FENCE = "```"
BOUNDARY = {"type": "system", "subtype": "compact_boundary",
            "content": "Conversation compacted"}


def load_hook():
    """Load the reinjection hook by path under a private module name."""
    spec = importlib.util.spec_from_file_location("reinject_stop_check", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assistant(text: str) -> dict:
    """Return one assistant transcript entry holding `text`."""
    return {"type": "assistant",
            "message": {"role": "assistant",
                        "content": [{"type": "text", "text": text}]}}


def disclosure() -> dict:
    """Return an assistant entry that carries the disclosure block."""
    return assistant("\n".join((FENCE, DISCLOSURE_MARKER, "summary text", FENCE)))


def run_stop(transcript_path: str, stop_hook_active: bool = False) -> dict:
    """Send one Claude Stop event and return the parsed stdout object."""
    environment = dict(os.environ)
    environment["CLAUDE_PROJECT_DIR"] = str(REPO_ROOT)
    payload = {"hook_event_name": "Stop", "cwd": str(REPO_ROOT),
               "transcript_path": transcript_path,
               "stop_hook_active": stop_hook_active}
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH), "--client", "claude"],
        input=json.dumps(payload), capture_output=True, text=True,
        env=environment, check=False, timeout=HOOK_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise AssertionError(f"hook failed: {result.stderr}")
    return json.loads(result.stdout) if result.stdout.strip() else {}


class CompactionDisclosureStopTest(unittest.TestCase):
    """The Stop check reads the transcript after the last compaction."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def transcript(self, entries: list, prefix: str = "") -> str:
        """Write `entries` as JSONL after `prefix` and return the file path."""
        path = self.directory / "session.jsonl"
        lines = [json.dumps(entry) for entry in entries]
        path.write_text(prefix + "\n".join(lines) + "\n", encoding="utf-8")
        return str(path)

    def test_session_without_compaction_passes(self):
        output = run_stop(self.transcript([assistant("plain reply")]))
        self.assertNotEqual(output.get("decision"), "block")

    def test_disclosure_after_boundary_passes(self):
        path = self.transcript([BOUNDARY, disclosure(), assistant("next step")])
        self.assertNotEqual(run_stop(path).get("decision"), "block")

    def test_missing_disclosure_after_boundary_blocks(self):
        path = self.transcript([BOUNDARY, assistant("resumed without disclosure")])
        output = run_stop(path)
        self.assertEqual(output.get("decision"), "block")
        self.assertIn(DISCLOSURE_MARKER, output.get("reason", ""))

    def test_marker_outside_a_fence_still_blocks(self):
        path = self.transcript([BOUNDARY, assistant(DISCLOSURE_MARKER + " was shown above")])
        self.assertEqual(run_stop(path).get("decision"), "block")

    def test_active_stop_hook_passes(self):
        path = self.transcript([BOUNDARY, assistant("resumed")])
        output = run_stop(path, stop_hook_active=True)
        self.assertNotEqual(output.get("decision"), "block")

    def test_newer_boundary_needs_its_own_disclosure(self):
        path = self.transcript([BOUNDARY, disclosure(), BOUNDARY, assistant("resumed")])
        self.assertEqual(run_stop(path).get("decision"), "block")

    def test_missing_transcript_passes_with_notice(self):
        output = run_stop(str(self.directory / "absent.jsonl"))
        self.assertNotEqual(output.get("decision"), "block")
        self.assertIn("systemMessage", output)

    def test_unreadable_transcript_passes_with_notice(self):
        output = run_stop(str(self.directory))
        self.assertNotEqual(output.get("decision"), "block")
        self.assertIn("systemMessage", output)

    def test_boundary_inside_the_read_window_still_blocks(self):
        hook = load_hook()
        filler = "x" * (hook.MAX_TRANSCRIPT_TAIL_BYTES + 1) + "\n"
        path = self.transcript([BOUNDARY, assistant("resumed")], prefix=filler)
        self.assertEqual(run_stop(path).get("decision"), "block")

    def test_boundary_before_the_read_window_passes(self):
        hook = load_hook()
        padding = [assistant("y" * 1024)] * (hook.MAX_TRANSCRIPT_TAIL_BYTES // 1024 + 1)
        path = self.transcript([BOUNDARY] + padding)
        self.assertNotEqual(run_stop(path).get("decision"), "block")


class StopRegistrationTest(unittest.TestCase):
    """Both Claude settings files run the reinjection hook on Stop."""

    def test_claude_settings_register_the_stop_check(self):
        for relative_path in (".claude/settings.json",
                              "hooks/claude-code-settings.example.json"):
            with self.subTest(path=relative_path):
                settings = json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
                commands = [
                    " ".join(hook.get("args", []))
                    for group in settings["hooks"]["Stop"]
                    for hook in group["hooks"]]
                self.assertTrue(any("reinject_agents_policy.py --client claude" in command
                                    for command in commands))


if __name__ == "__main__":
    unittest.main()
