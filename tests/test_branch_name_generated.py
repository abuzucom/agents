#!/usr/bin/env python3
"""Generated adjective-surname branch names fail the branch checker."""
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_branch_name

ADOPTION_DOC = REPO_ROOT / "docs" / "agent-policy" / "adoption.md"
MAX_WORD_LIST_BYTES = 64 * 1024
LONG_NAME_LENGTH = 10_000
LONG_NAME_SECONDS = 1.0

GENERATED_NAMES = (
    "chore/blissful-johnson-kqcymp",
    "chore/kind-thompson",
    "chore/kind-thompson-6vv1rj",
    "fix/eager-hopper",
    "feat/vibrant-curie-abcdef",
    "docs/serene-lovelace-x7k2mq",
)

# Head branches of every abuzucom/agents pull request that used an allowed
# prefix, read through the GitHub connector on 2026-10-22. The generated
# `chore/kind-thompson-6vv1rj` (#44) sits in GENERATED_NAMES instead.
HISTORICAL_NAMES = (
    "fix/compaction-transcript-bug", "chore/hooks-remove-dead-code",
    "fix/hooks-logic-and-dead-code", "fix/allow-trusted-git-in-gate",
    "fix/disable-status-filter-drivers", "fix/correct-prose-gate-enforcement-claim",
    "feat/block-local-path-disclosure", "feat/route-npm-workflows-to-consent",
    "feat/allow-npm-workflow-consent", "docs/record-xdj-rx3-emu-adopter",
    "feat/separate-command-execution-gate", "chore/merge-same-day-changelog-entries",
    "fix/harden-trusted-git-transport", "fix/deny-agent-label-and-api-bypass",
    "fix/bind-gate-approval-to-head", "fix/allow-primary-branch-reads",
    "chore/remove-dependabot-changelog-companion", "fix/diagnose-github-access-failures",
    "fix/protect-identity-and-prose-checkers", "fix/remove-contradictory-logic-checks",
    "fix/pipe-gate-list-operators", "fix/prohibit-agent-pr-label-changes",
    "fix/exempt-coverage-bot-branch-name", "fix/classify-gh-proxy-failures",
    "docs/record-visualizer-readoption", "docs/record-viim-adoption",
    "chore/pull-latest-main", "fix/changelog-range-first-release",
    "chore/enforce-prose-checks-for-agents", "chore/investigate-foucault-pr-checker",
    "docs/require-complete-gate-adoption", "feat/banned-models-disclosure",
    "docs/exempt-dependabot-changelog", "feat/handoff-compaction-events",
    "docs/inspect-time-chime-deployment", "fix/trusted-gh-utf8-decoding",
    "docs/enforce-lf-policy-line-endings", "fix/secure-git-github-delivery",
    "feat/lock-down-github-cli-actions", "docs/github-cli-edit-policy",
    "chore/release-1-14-0", "fix/codeql-url-sanitization",
    "fix/task-specific-branch-names", "fix/logic-inconsistencies",
    "chore/security-review-pr", "fix/rebase-hook-recovery", "fix/immutable-check-auth",
    "fix/branch-validation-bypasses", "chore/examine-kriggins-history",
    "fix/remove-invalid-codex-attribution", "fix/resolve-antigravity-workspace-ambiguity",
    "feat/downstream-adoption-hardening", "feat/external-repo-consent",
    "docs/add-prolink-go-adopter", "fix/adoption-licensing",
    "feat/cross-platform-command-policy", "feat/powershell-command-policy",
    "fix/redact-remote-userinfo", "feat/concise-agent-policy",
    "feat/agent-policy-lifecycle", "feat/advisory-prose-policy",
    "docs/split-semicolon-prose", "fix/security-checker-hardening", "chore/review-path",
    "feat/consent-gate-hooks", "feat/git-identity-enforcement",
    "feat/session-start-branch-check", "feat/contributing-and-pr-templates",
    "feat/security-policy-template", "feat/handoff-template",
    "feat/agentlint-advisory-check", "feat/no-hedging-rule", "chore/reduce-ci-minutes",
    "docs/agents-md-checker-polish", "docs/ruleset-allowed-retest",
)

PLANNED_NAMES = (
    "fix/gate-denial-response-and-plan-mode", "feat/npm-node-test-gate",
    "feat/denial-retry-limit", "chore/adopt-canonical-agent-policy",
)


def documented_example_names() -> list:
    """Return the compliant branch examples quoted in the adoption guide."""
    text = ADOPTION_DOC.read_text(encoding="utf-8")
    examples = ("fix/branch-name-validation", "chore/synchronize-policy-copies",
                "docs/clarify-agent-branch-rules")
    for example in examples:
        if f"`{example}`" not in text:
            raise AssertionError(f"adoption guide no longer quotes {example}")
    return list(examples)


class GeneratedNameDetectionTest(unittest.TestCase):
    """Adjective-surname names from session generators fail."""

    def test_generated_names_fail(self) -> None:
        for branch in GENERATED_NAMES:
            with self.subTest(branch=branch):
                self.assertTrue(check_branch_name.find_violations(branch, strict=True))

    def test_generated_name_violation_names_the_cause(self) -> None:
        violations = check_branch_name.find_violations("chore/blissful-johnson-kqcymp")
        self.assertTrue(any("generated" in violation for violation in violations), violations)


class TaskSpecificNamesPassTest(unittest.TestCase):
    """Real task-specific names keep passing."""

    def test_documented_examples_pass(self) -> None:
        for branch in documented_example_names():
            with self.subTest(branch=branch):
                self.assertEqual(check_branch_name.find_violations(branch, strict=True), [])

    def test_historical_pull_request_branches_pass(self) -> None:
        for branch in HISTORICAL_NAMES:
            with self.subTest(branch=branch):
                self.assertEqual(check_branch_name.find_violations(branch, strict=True), [])

    def test_planned_branches_pass(self) -> None:
        for branch in PLANNED_NAMES:
            with self.subTest(branch=branch):
                self.assertEqual(check_branch_name.find_violations(branch, strict=True), [])


class WordListIntegrityTest(unittest.TestCase):
    """The bundled word list is bounded, sorted ASCII data."""

    def test_word_list_is_bounded_sorted_ascii_regular_file(self) -> None:
        path = check_branch_name.GENERATED_NAME_WORDS_PATH
        self.assertTrue(path.is_file())
        self.assertFalse(path.is_symlink())
        data = path.read_bytes()
        self.assertLessEqual(len(data), MAX_WORD_LIST_BYTES)
        self.assertNotIn(b"\r", data)
        entries = [line for line in data.decode("ascii").splitlines()
                   if line and not line.startswith("#")]
        self.assertTrue(entries)
        self.assertEqual(entries, sorted(entries))
        for entry in entries:
            kind, _separator, word = entry.partition(" ")
            with self.subTest(entry=entry):
                self.assertIn(kind, ("adjective", "surname"))
                self.assertRegex(word, r"^[a-z]+$")

    def test_missing_word_list_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "absent.txt"
            with mock.patch.object(check_branch_name, "GENERATED_NAME_WORDS_PATH", missing):
                self.assertTrue(check_branch_name.find_violations("fix/branch-name-validation"))

    def test_malformed_word_list_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            malformed = Path(directory) / "words.txt"
            malformed.write_bytes(b"adjective Kind\nnoun thompson\n")
            with mock.patch.object(check_branch_name, "GENERATED_NAME_WORDS_PATH", malformed):
                self.assertTrue(check_branch_name.find_violations("fix/branch-name-validation"))


class LinearTimeTest(unittest.TestCase):
    """A very long name finishes inside a fixed bound."""

    def test_long_name_finishes_quickly(self) -> None:
        branch = "fix/" + "-".join(["word"] * (LONG_NAME_LENGTH // len("word-")))
        started = time.monotonic()
        check_branch_name.find_violations(branch, strict=True)
        self.assertLess(time.monotonic() - started, LONG_NAME_SECONDS)


if __name__ == "__main__":
    unittest.main()
