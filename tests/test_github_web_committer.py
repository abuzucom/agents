#!/usr/bin/env python3
"""A GitHub-signed web-flow committer passes strict attribution; nothing else does.

GitHub commits a web merge or squash as `GitHub <noreply@github.com>`, which
its API resolves to the web-flow account. A squash keeps the merged commits'
agent trailers, so the strict numbered-noreply rule applies to it. The
committer exemption needs every web-flow marker plus GitHub's own signature.
The author keeps the strict rule.
"""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_commit_attribution as attribution

AUTHOR_ID = 1234567
AUTHOR_EMAIL = f"{AUTHOR_ID}+octocat@users.noreply.github.com"
WEB_FLOW = {"login": "web-flow", "id": 19864447}


def web_commit() -> dict:
    """Return GitHub API metadata for a signed web squash commit."""
    return {
        "sha": "a" * 40,
        "author": {"login": "octocat", "id": AUTHOR_ID},
        "committer": dict(WEB_FLOW),
        "commit": {
            "author": {"email": AUTHOR_EMAIL},
            "committer": {"email": "noreply@github.com"},
            "verification": {"verified": True, "reason": "valid"},
        },
    }


def committer_violation(document: dict) -> str | None:
    """Return the strict committer verdict for one commit document."""
    return attribution._identity_violation(
        "committer", document, document.get("committer"), require_noreply=True)


class WebFlowCommitterTest(unittest.TestCase):
    """Only a GitHub-signed web-flow commit skips the committer noreply rule."""

    def test_signed_web_flow_committer_passes(self):
        self.assertIsNone(committer_violation(web_commit()))

    def test_author_stays_strict(self):
        document = web_commit()
        document["commit"]["author"]["email"] = "noreply@github.com"
        violation = attribution._identity_violation(
            "author", document, document["author"], require_noreply=True)
        self.assertIn("numbered GitHub noreply", violation)

    def test_each_marker_is_required(self):
        mutations = {
            "email": lambda doc: doc["commit"]["committer"].update(email="ci@example.com"),
            "login": lambda doc: doc["committer"].update(login="web-flow-bot"),
            "account id": lambda doc: doc["committer"].update(id=42),
            "unverified": lambda doc: doc["commit"]["verification"].update(verified=False),
            "no verification": lambda doc: doc["commit"].pop("verification"),
        }
        for name, mutate in mutations.items():
            with self.subTest(marker=name):
                document = copy.deepcopy(web_commit())
                mutate(document)
                self.assertTrue(committer_violation(document))


if __name__ == "__main__":
    unittest.main()
