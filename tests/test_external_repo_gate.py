#!/usr/bin/env python3
"""Cover the cross-owner GitHub gate in hooks/_gate_core.py (Rule 17)."""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "hooks"))

try:
    from tests.retrying_temp_directory import RetryingTemporaryDirectory
except ImportError:
    from retrying_temp_directory import RetryingTemporaryDirectory

import _gate_core

OWNER = "abuzucom"
EXTERNAL = "evanpurkhiser/prolink-go"


def repo_with_remote(directory: str, url: str) -> str:
    """Write a minimal git config naming one origin URL."""
    git_dir = Path(directory, ".git")
    git_dir.mkdir(exist_ok=True)
    if url:
        Path(git_dir, "config").write_text(
            f'[remote "origin"]\n\turl = {url}\n', encoding="utf-8")
    return directory


class OriginOwnerTest(unittest.TestCase):
    """The origin owner comes from the bounded config reader."""

    def owner_for(self, url: str) -> str:
        """Return the parsed origin owner for one remote URL."""
        with RetryingTemporaryDirectory() as tmp_dir:
            return _gate_core._origin_owner(repo_with_remote(tmp_dir, url))

    def test_https_remote(self):
        self.assertEqual(
            self.owner_for("https://github.com/abuzucom/agents"), OWNER)

    def test_https_remote_with_git_suffix(self):
        self.assertEqual(
            self.owner_for("https://github.com/abuzucom/agents.git"), OWNER)

    def test_scp_style_ssh_remote(self):
        self.assertEqual(
            self.owner_for("git@github.com:abuzucom/agents.git"), OWNER)

    def test_ssh_url_remote(self):
        self.assertEqual(
            self.owner_for("ssh://git@github.com/abuzucom/agents.git"), OWNER)

    def test_non_github_remote_yields_nothing(self):
        self.assertEqual(
            self.owner_for("https://gitlab.com/abuzucom/agents"), "")

    def test_remote_without_repository_yields_nothing(self):
        self.assertEqual(self.owner_for("https://github.com/abuzucom"), "")

    def test_missing_config_yields_nothing(self):
        self.assertEqual(self.owner_for(""), "")

    def test_remote_with_port_resolves_past_it(self):
        self.assertEqual(
            self.owner_for("https://github.com:443/abuzucom/agents"), OWNER)

    def test_empty_remote_url_yields_nothing(self):
        with RetryingTemporaryDirectory() as tmp_dir:
            git_dir = Path(tmp_dir, ".git")
            git_dir.mkdir()
            Path(git_dir, "config").write_text(
                '[remote "origin"]\n\turl =\n', encoding="utf-8")
            self.assertEqual(_gate_core._origin_owner(tmp_dir), "")

    def test_remote_without_separator_yields_nothing(self):
        self.assertEqual(self.owner_for("github.com"), "")


class RepositoryTargetTest(unittest.TestCase):
    """Only a plain owner/name argument names a target owner."""

    def test_plain_target(self):
        self.assertEqual(
            _gate_core._repository_target_owner("owner/name"), "owner")

    def test_extra_path_segment_rejected(self):
        self.assertEqual(
            _gate_core._repository_target_owner("owner/name/extra"), "")

    def test_flag_rejected(self):
        self.assertEqual(
            _gate_core._repository_target_owner("--repo/name"), "")

    def test_ambiguous_token_rejected(self):
        self.assertEqual(
            _gate_core._repository_target_owner("$OWNER/name"), "")

    def test_bare_word_rejected(self):
        self.assertEqual(_gate_core._repository_target_owner("name"), "")


class CrossOwnerVerdictTest(unittest.TestCase):
    """Outward-facing commands at another owner reach an active human."""

    def verdict(self, args: list, owner: str = OWNER) -> str:
        """Return the decision for one GitHub CLI argument list."""
        return _gate_core.github_cli_verdict(args, repo_owner=owner)[0]

    def test_pull_request_comment_asks(self):
        self.assertEqual(
            self.verdict(["pr", "comment", "16", "--repo", EXTERNAL]), "ask")

    def test_pull_request_create_asks(self):
        self.assertEqual(
            self.verdict(["pr", "create", "--repo", EXTERNAL]), "ask")

    def test_issue_create_asks_through_short_flag(self):
        self.assertEqual(
            self.verdict(["issue", "create", "-R", EXTERNAL]), "ask")

    def test_repository_fork_asks_from_positional_target(self):
        self.assertEqual(self.verdict(["repo", "fork", EXTERNAL]), "ask")

    def test_positional_scan_skips_leading_flags(self):
        self.assertEqual(
            self.verdict(["repo", "fork", "--clone", EXTERNAL]), "ask")

    def test_owner_comparison_ignores_case(self):
        self.assertEqual(
            self.verdict(["pr", "comment", "6", "--repo", "ABUZUCOM/agents"]),
            "")

    def test_same_owner_passes(self):
        self.assertEqual(
            self.verdict(["pr", "comment", "6", "--repo", "abuzucom/agents"]),
            "")

    def test_missing_target_passes(self):
        self.assertEqual(self.verdict(["pr", "create"]), "")

    def test_unknown_origin_owner_asks(self):
        # Rule 17 prefers a prompt over waving an outward-facing command
        # through when the origin owner cannot be read.
        self.assertEqual(
            self.verdict(["pr", "comment", "16", "--repo", EXTERNAL], ""),
            "ask")

    def test_read_only_commands_stay_available(self):
        for args in (
                ["pr", "view", "16", "--repo", EXTERNAL],
                ["pr", "diff", "16", "--repo", EXTERNAL],
                ["pr", "checks", "16", "--repo", EXTERNAL],
                ["issue", "list", "--repo", EXTERNAL],
                ["repo", "view", EXTERNAL],
                ["repo", "clone", EXTERNAL],
        ):
            with self.subTest(args=args):
                self.assertEqual(self.verdict(args), "")

    def test_existing_deny_paths_keep_priority(self):
        self.assertEqual(
            self.verdict(["pr", "merge", "12", "--admin", "--repo", EXTERNAL]),
            "deny")


class ForgeVerdictTest(unittest.TestCase):
    """forge_verdict resolves the owner from the working directory."""

    def verdict(self, args: list, url: str) -> str:
        """Return the decision for one gh invocation in a crafted repository."""
        with RetryingTemporaryDirectory() as tmp_dir:
            repo = repo_with_remote(tmp_dir, url)
            return _gate_core.forge_verdict("gh", args, repo)[0]

    def test_external_target_asks(self):
        self.assertEqual(
            self.verdict(["pr", "comment", "16", "--repo", EXTERNAL],
                         "https://github.com/abuzucom/agents"),
            "ask")

    def test_same_owner_target_passes(self):
        self.assertEqual(
            self.verdict(["pr", "comment", "6", "--repo", "abuzucom/agents"],
                         "https://github.com/abuzucom/agents"),
            "")

    def test_repository_delete_still_denies(self):
        self.assertEqual(
            self.verdict(["repo", "delete", EXTERNAL],
                         "https://github.com/abuzucom/agents"),
            "deny")


if __name__ == "__main__":
    unittest.main()
