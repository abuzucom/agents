"""Test the shared Cloudflare Pages deployment allowance."""
import unittest
from pathlib import Path

from hooks import _gate_core


class CloudflarePagesPolicyTest(unittest.TestCase):
    """Verify the allowlist and its denial boundaries."""

    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]

    def verdict(self, *arguments: str) -> tuple:
        return _gate_core.cloudflare_pages_verdict(
            "wrangler", list(arguments), str(self.root))

    def test_allows_named_pages_deployment(self) -> None:
        self.assertEqual(
            self.verdict("pages", "deploy", "hooks", "--project-name", "time-chime"),
            ("", ""),
        )

    def test_allows_preview_branch(self) -> None:
        self.assertEqual(
            self.verdict("pages", "deploy", "hooks", "--project-name=site",
                         "--branch", "preview"),
            ("", ""),
        )

    def test_rejects_other_wrangler_commands(self) -> None:
        self.assertEqual(self.verdict("deploy", "dist" )[0], "deny")
        self.assertEqual(self.verdict("pages", "project", "list")[0], "deny")
        self.assertEqual(self.verdict("pages", "secret", "put", "KEY")[0], "deny")

    def test_rejects_missing_or_extra_options(self) -> None:
        self.assertEqual(self.verdict("pages", "deploy", "hooks")[0], "deny")
        self.assertEqual(
            self.verdict("pages", "deploy", "hooks", "--project-name", "site",
                         "--commit-dirty")[0], "deny")

    def test_rejects_paths_outside_workspace(self) -> None:
        self.assertEqual(
            self.verdict("pages", "deploy", "..", "--project-name", "site")[0],
            "deny",
        )

    def test_rejects_ambiguous_values(self) -> None:
        self.assertEqual(
            self.verdict("pages", "deploy", "hooks", "--project-name", "$NAME")[0],
            "deny",
        )


if __name__ == "__main__":
    unittest.main()
