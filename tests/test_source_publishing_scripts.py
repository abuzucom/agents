"""Source publishing scripts live in the source repository's local script list.

An adopter takes hooks/workflow-scripts.txt byte for byte. That shared list
must name no script that only the source repository ships.
"""
import unittest
from pathlib import Path

from tests.test_command_execution_gate import _load_gate_module

REPO_ROOT = Path(__file__).resolve().parent.parent
# Only the source repository ships this file. Adopters omit it.
SOURCE_MARKER = REPO_ROOT / "docs" / "agent-policy" / "source-orientation.md"
SOURCE_PUBLISHING_SCRIPT = "scripts/release.py"
CHECK_TAG_COMMAND = "python scripts/release.py check-tag v1.0.0"


class SourcePublishingScriptListTest(unittest.TestCase):
    """The shared list omits release.py and the local list supplies it."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.gate = _load_gate_module()

    def test_shared_list_omits_release(self) -> None:
        scripts = {script for script, _pattern, _verdict in self.gate._load_shared_scripts()}
        self.assertNotIn(SOURCE_PUBLISHING_SCRIPT, scripts)

    @unittest.skipUnless(SOURCE_MARKER.is_file(), "release tooling ships only in the source repository")
    def test_local_list_supplies_release(self) -> None:
        self.gate._load_workflow_scripts.cache_clear()
        decision, _reason = self.gate.workflow_decision(CHECK_TAG_COMMAND, str(REPO_ROOT))
        self.assertEqual(decision, "allow")


if __name__ == "__main__":
    unittest.main()
