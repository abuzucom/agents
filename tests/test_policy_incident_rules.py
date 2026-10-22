#!/usr/bin/env python3
"""Pin the approved gate-denial and retry wording across every policy copy."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = REPO_ROOT / "AGENTS.md"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_policy_size
import sync

WHITESPACE = re.compile(r"\s+")
ADOPTION_DOC = REPO_ROOT / "docs" / "agent-policy" / "adoption.md"
GITHUB_DOC = REPO_ROOT / "docs" / "agent-policy" / "github.md"

# E1 and E2: the approved denial response and retry budget sentences.
REQUIRED_SENTENCES = (
    "On a denial, report the gate and reason. Then stop until the next user message.",
    "Never propose or offer gate removal, adjustment, or bypass.",
    "Never route around a denial.",
    "A new active-human instruction starts a new attempt budget.",
    "Never cite a retry limit, lockout, or denial to refuse instructed work.",
    # H3, H7, H2, H14, H25, H10 replacement text.
    "The hooks refuse the targets and command families listed in "
    "`docs/agent-policy/enforcement.md`.",
    "The hooks route all other consent-required commands listed there to active-human approval.",
    "`scripts/check_hedging.py` warns on voice, sentence, discourse, escape-sequence, "
    "and vocabulary findings and exits 0 for those findings.",
    "Unreadable policy data and unsafe metadata exit 1.",
    "Other clients lack that shell coverage. The rule binds without it.",
    "Rule 22 governs denylist and hook edits.",
    "Write code, identifiers, comments, commit messages, and documentation in English.",
    "Follow the matching validation path in `docs/agent-policy/adoption.md`.",
)

# Text the approved rewordings, removals, and moves take out of AGENTS.md.
REMOVED_SENTENCES = (
    "Report failure.",
    "**Refuse without a prompt.**",
    "**Route for active-human approval.**",
    "Pattern checks provide advisory coverage.",
    "client hook APIs lack equivalent shell coverage.",
    "Modifying the denylist or hook files requires fresh",
    "Allowed: `The checker reads the file and reports warnings.`",
    "Allowed: `If the path escapes the root, reject the request.`",
    "Comments always use English.",
    "Keep other languages out of identifiers, comments, and documentation.",
    "Container examples live in `docs/agent-policy/security.md`.",
    "A fork of an unmaintained upstream is the common case.",
    "Use the matching path:",
)

MOVED_SENTENCES = (
    (ADOPTION_DOC, "- Allowed: `The checker reads the file and reports warnings.`"),
    (ADOPTION_DOC, "- Allowed: `If the path escapes the root, reject the request.`"),
    (GITHUB_DOC, "A fork of an unmaintained upstream is the common external case."),
)


def normalize_whitespace(text: str) -> str:
    """Collapse line wraps so a sentence matches regardless of where it breaks."""
    return WHITESPACE.sub(" ", text)


def read_normalized(path: Path) -> str:
    """Return one policy file as whitespace-normalized text."""
    return normalize_whitespace(path.read_text(encoding="utf-8"))


class ApprovedPolicyTextTest(unittest.TestCase):
    """The canonical policy carries exactly the approved incident wording."""

    def test_policy_stays_within_size_limit(self) -> None:
        self.assertEqual(check_policy_size.find_violations(POLICY_PATH), [])
        self.assertLessEqual(len(POLICY_PATH.read_bytes()), check_policy_size.MAX_POLICY_BYTES)

    def test_required_sentences_present_in_canonical_policy(self) -> None:
        policy = read_normalized(POLICY_PATH)
        for sentence in REQUIRED_SENTENCES:
            with self.subTest(sentence=sentence):
                self.assertIn(sentence, policy)

    def test_removed_sentences_absent_from_canonical_policy(self) -> None:
        policy = read_normalized(POLICY_PATH)
        for sentence in REMOVED_SENTENCES:
            with self.subTest(sentence=sentence):
                self.assertNotIn(sentence, policy)

    def test_moved_sentences_present_in_destination_docs(self) -> None:
        for path, sentence in MOVED_SENTENCES:
            with self.subTest(path=path.name, sentence=sentence):
                self.assertIn(sentence, path.read_text(encoding="utf-8"))

    def test_adoptable_output_carries_required_sentences(self) -> None:
        adoptable = normalize_whitespace(
            sync.adoptable_content(POLICY_PATH.read_text(encoding="utf-8")))
        for sentence in REQUIRED_SENTENCES:
            with self.subTest(sentence=sentence):
                self.assertIn(sentence, adoptable)

    def test_every_synchronized_copy_carries_required_sentences(self) -> None:
        for copy in sync.COPIES:
            text = read_normalized(REPO_ROOT / copy)
            for sentence in REQUIRED_SENTENCES:
                with self.subTest(copy=copy, sentence=sentence):
                    self.assertIn(sentence, text)

    def test_synchronized_copies_match_canonical_policy(self) -> None:
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "sync.py"), "--check"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=60, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_supporting_docs_stay_ascii_lf(self) -> None:
        for path in sorted((REPO_ROOT / "docs" / "agent-policy").glob("*.md")):
            data = path.read_bytes()
            with self.subTest(path=path.name):
                self.assertNotIn(b"\r\n", data)
                data.decode("ascii")
                self.assertLessEqual(len(data), check_policy_size.MAX_POLICY_BYTES)


if __name__ == "__main__":
    unittest.main()
