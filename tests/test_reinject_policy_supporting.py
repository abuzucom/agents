import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = ROOT / "hooks" / "reinject_agents_policy.py"


def load_hook():
    spec = importlib.util.spec_from_file_location("reinject_supporting", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SupportingPolicyTests(unittest.TestCase):
    def test_load_policy_assembles_supporting_file(self):
        hook = load_hook()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("canonical\n", encoding="utf-8")
            supporting = root / "docs" / "agent-policy"
            supporting.mkdir(parents=True)
            (supporting / "adoption.md").write_text(
                "supporting\n", encoding="utf-8")
            for relative_name in hook.SUPPORTING_POLICY_FILES[1:]:
                (root / relative_name).write_text("detail\n", encoding="utf-8")
            policy, _digest = hook.load_policy(root)
        self.assertTrue(policy.startswith("canonical\n"))
        self.assertIn("supporting\n", policy)

    def test_load_policy_rejects_non_regular_supporting_file(self):
        hook = load_hook()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("canonical\n", encoding="utf-8")
            supporting = root / "docs" / "agent-policy"
            supporting.mkdir(parents=True)
            (supporting / "adoption.md").mkdir()
            with self.assertRaisesRegex(ValueError, "regular file"):
                hook.load_policy(root)

    def test_load_policy_rejects_missing_supporting_file(self):
        hook = load_hook()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("canonical\n", encoding="utf-8")
            (root / "docs" / "agent-policy").mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "missing"):
                hook.load_policy(root)

    def test_load_policy_rejects_missing_supporting_directory(self):
        hook = load_hook()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("canonical\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing"):
                hook.load_policy(root)

    def test_load_policy_rejects_non_ascii_supporting_file(self):
        hook = load_hook()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("canonical\n", encoding="utf-8")
            supporting = root / "docs" / "agent-policy"
            supporting.mkdir(parents=True)
            for relative_name in hook.SUPPORTING_POLICY_FILES:
                path = root / relative_name
                path.write_bytes(b"detail\n")
            (supporting / "security.md").write_bytes(b"bad\xc3\xa9\n")
            with self.assertRaisesRegex(ValueError, "non-ASCII"):
                hook.load_policy(root)

    def test_load_policy_rejects_oversized_supporting_file(self):
        hook = load_hook()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("canonical\n", encoding="utf-8")
            for relative_name in hook.SUPPORTING_POLICY_FILES:
                path = root / relative_name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("detail\n", encoding="utf-8")
            oversized = root / hook.SUPPORTING_POLICY_FILES[0]
            oversized.write_bytes(b"x" * (hook.MAX_POLICY_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "exceeds the policy size limit"):
                hook.load_policy(root)


if __name__ == "__main__":
    unittest.main()
