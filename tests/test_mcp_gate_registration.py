#!/usr/bin/env python3
"""Every client that exposes MCP calls to hooks registers the MCP write gate."""
import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_gate_adoption

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
MCP_GATE = "deny_mcp_github_writes.py"


def run_check(root: Path) -> tuple[int, str]:
    """Return the gate-adoption exit code and diagnostics for one root."""
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        code = check_gate_adoption.main(["--root", str(root)])
    return code, stderr.getvalue()


class McpGateRegistrationTest(unittest.TestCase):
    """Codex, Gemini, and Antigravity each register the gate with its client flag."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repository"
        self.root.mkdir()
        self.addCleanup(self.temporary.cleanup)
        for relative in ("docs", "hooks", "scripts", "skills", "tests", ".claude", ".codex",
                         ".agents", ".gemini"):
            shutil.copytree(REPOSITORY_ROOT / relative, self.root / relative)
        for relative in check_gate_adoption.REQUIRED_POLICY:
            shutil.copy(REPOSITORY_ROOT / relative, self.root / relative)

    def _rewrite(self, relative: str, old: str, new: str) -> None:
        """Replace one literal in a copied client configuration."""
        path = self.root / relative
        content = path.read_text(encoding="utf-8")
        self.assertIn(old, content)
        path.write_text(content.replace(old, new), encoding="utf-8")

    def test_full_copy_passes(self) -> None:
        code, output = run_check(self.root)
        self.assertEqual(code, 0, output)

    def test_missing_client_registration_reported(self) -> None:
        for client, (relative, event, matcher) in check_gate_adoption.MCP_GATE_CONFIGS.items():
            with self.subTest(client=client):
                self.setUp()
                self._rewrite(relative, f"{MCP_GATE} --client {client}", "omitted_gate.py")
                code, output = run_check(self.root)
                self.assertEqual(code, 1)
                self.assertIn(f"{client} does not register {MCP_GATE}", output)
                self.assertIn(event, output)
                self.assertIn(repr(matcher), output)

    def test_wrong_matcher_reported(self) -> None:
        relative, _event, matcher = check_gate_adoption.MCP_GATE_CONFIGS["gemini"]
        self._rewrite(relative, f'"matcher": "{matcher}"', '"matcher": "^mcp_github_.*"')
        code, output = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn(f"gemini does not register {MCP_GATE}", output)


if __name__ == "__main__":
    unittest.main()
