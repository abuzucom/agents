#!/usr/bin/env python3
"""Every AGENTS.md pointer into docs/agent-policy/ names text the target holds.

AGENTS.md delegates detail with sentences such as "listed in
`docs/agent-policy/enforcement.md`". A move of that detail out of the
assembled policy leaves the rule pointing at nothing. Each case pairs one
pointer sentence with an anchor that the named file must contain.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY = "docs/agent-policy/"

# (pointer sentence in AGENTS.md, target file, anchor the target must hold)
POINTERS = (
    ("Protected files live in `docs/agent-policy/enforcement.md`.",
     "enforcement.md", "The protected inventory covers"),
    ("Follow the authorization procedure in `docs/agent-policy/enforcement.md`.",
     "enforcement.md", "The gates route acts that need consent"),
    ("The hooks refuse the targets and command families listed in "
     "`docs/agent-policy/enforcement.md`.",
     "enforcement.md", "The gates refuse destructive commands"),
    ("The hooks route all other commands that require consent in "
     "`docs/agent-policy/enforcement.md` to active human approval.",
     "enforcement.md", "The gates route acts that need consent"),
    ("State examples live in `docs/agent-policy/adoption.md`.",
     "adoption.md", "Verify the current branch, remote URLs"),
    ("Container examples live in `docs/agent-policy/security.md`.",
     "security.md", "securityContext.runAsNonRoot"),
    ("Check examples live in `docs/agent-policy/enforcement.md`.",
     "enforcement.md", "python scripts/check_gate_adoption.py"),
    ("Use the trusted recovery procedure in `docs/agent-policy/adoption.md`.",
     "adoption.md", "## Git identity recovery"),
    ("The required files and registrations live in `docs/agent-policy/adoption.md`.",
     "adoption.md", "Copy `scripts/check_git_identity.py`"),
    ("The complete command inventory lives in `docs/agent-policy/security.md`.",
     "security.md", "## Denied command families"),
    ("`docs/agent-policy/security.md` lists protected credential directories",
     "security.md", "Protected content includes"),
    ("The inventory of covered acts lives in `docs/agent-policy/github.md`.",
     "github.md", "PR creation, issue creation, comments"),
    ("Surfaces and coverage live in `docs/agent-policy/github.md`.",
     "github.md", "Rule 23 covers these surfaces"),
    ("Surfaces and coverage live in `docs/agent-policy/github.md`.",
     "github.md", "denies MCP label fields"),
    ("Match the validation path in `docs/agent-policy/adoption.md`.",
     "adoption.md", "## Validation paths"),
)


def normalized(text: str) -> str:
    """Return `text` with each whitespace run collapsed to one space."""
    return " ".join(text.split())


class PolicyPointerTest(unittest.TestCase):
    """AGENTS.md pointers and their targets stay in step."""

    def setUp(self) -> None:
        self.agents = normalized((ROOT / "AGENTS.md").read_text(encoding="utf-8"))

    def test_pointer_sentences_exist(self) -> None:
        for sentence, _target, _anchor in POINTERS:
            with self.subTest(sentence=sentence):
                self.assertIn(normalized(sentence), self.agents)

    def test_pointer_targets_hold_anchors(self) -> None:
        for sentence, target, anchor in POINTERS:
            with self.subTest(target=target, anchor=anchor):
                text = normalized((ROOT / POLICY / target).read_text(encoding="utf-8"))
                self.assertIn(normalized(anchor), text, sentence)


if __name__ == "__main__":
    unittest.main()
