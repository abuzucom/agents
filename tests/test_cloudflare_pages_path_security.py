"""Test Cloudflare Pages deployment path safeguards."""
import tempfile
import unittest
from pathlib import Path

from hooks import _gate_core


class CloudflarePagesPathSecurityTest(unittest.TestCase):
    """Reject repository and credential paths from Pages deployment."""

    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]

    def verdict(self, path: str) -> tuple:
        return _gate_core.cloudflare_pages_verdict(
            "wrangler",
            ["pages", "deploy", path, "--project-name", "site"],
            str(self.root),
        )

    def test_rejects_workspace_root_and_hidden_directories(self) -> None:
        for path in (".", ".git", ".agents"):
            with self.subTest(path=path):
                self.assertEqual(self.verdict(path)[0], "deny")

    def test_rejects_protected_target_and_contents(self) -> None:
        self.assertEqual(self.verdict("credentials")[0], "deny")
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            output_path = Path(directory)
            (output_path / ".env.production").write_text("TOKEN=secret\n")
            self.assertEqual(self.verdict(output_path.name)[0], "deny")


if __name__ == "__main__":
    unittest.main()
