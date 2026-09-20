#!/usr/bin/env python3
"""Test staged complete-gate transaction path controls."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "complete_gate_adoption.py"


def load_script():
    """Load the transaction installer from its checked-in path."""
    spec = importlib.util.spec_from_file_location("complete_gate_adoption", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CompleteGateAdoptionTest(unittest.TestCase):
    """The installer accepts only a complete candidate below fixed staging."""

    def setUp(self) -> None:
        self.script = load_script()

    def test_candidate_requires_fixed_staging_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staged = root / ".gate-staging" / "release"
            staged.mkdir(parents=True)
            outside = root / "outside"
            outside.mkdir()
            self.assertEqual(self.script._candidate(root, str(staged)), staged.resolve())
            with self.assertRaises(ValueError):
                self.script._candidate(root, str(outside))

    def test_candidate_paths_include_all_transaction_configs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary)
            (candidate / "shared-files.json").write_text(
                json.dumps({"shared": {"hooks/example.py": "digest"}}),
                encoding="utf-8",
            )
            paths = self.script._candidate_paths(candidate)
        self.assertIn("hooks/example.py", paths)
        self.assertIn(".claude/settings.json", paths)
        self.assertIn(".codex/config.toml", paths)

    def test_transaction_configs_copy_last(self) -> None:
        paths = self.script._ordered_paths([
            ".claude/settings.json",
            "hooks/example.py",
            ".codex/hooks.json",
        ])
        self.assertEqual(paths[0], "hooks/example.py")
        self.assertEqual(paths[-2:], [".claude/settings.json", ".codex/hooks.json"])


if __name__ == "__main__":
    unittest.main()
