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

FIXTURES = ROOT / "tests" / "fixtures" / "web_flow"
# A real web-flow signature from this repository's history, and one made by
# a throwaway key. Both are public signature data, never keys.
GITHUB_SIGNATURE = (FIXTURES / "github_signature.asc").read_text(encoding="ascii")
OTHER_SIGNATURE = (FIXTURES / "other_signature.asc").read_text(encoding="ascii")
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
            "verification": {"verified": True, "reason": "valid",
                             "signature": GITHUB_SIGNATURE},
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
            "other signer": lambda doc: doc["commit"]["verification"].update(
                signature=OTHER_SIGNATURE),
            "no signature": lambda doc: doc["commit"]["verification"].pop("signature"),
            "malformed signature": lambda doc: doc["commit"]["verification"].update(
                signature="-----BEGIN PGP SIGNATURE-----\n\nnot base64!\n"),
        }
        for name, mutate in mutations.items():
            with self.subTest(marker=name):
                document = copy.deepcopy(web_commit())
                mutate(document)
                self.assertTrue(committer_violation(document))


class SignatureIssuerTest(unittest.TestCase):
    """The issuer key ID comes from the signature's hashed subpackets."""

    def test_github_signature_issuer(self):
        self.assertEqual(attribution.signature_issuer(GITHUB_SIGNATURE), "B5690EEEBB952194")

    def test_other_signature_issuer(self):
        self.assertEqual(attribution.signature_issuer(OTHER_SIGNATURE), "405A1684C1B51779")

    def test_unreadable_signature_has_no_issuer(self):
        for value in ("", "plain text", None, "-----BEGIN PGP SIGNATURE-----\n\nAAAA\n"):
            with self.subTest(value=value):
                self.assertEqual(attribution.signature_issuer(value), "")


if __name__ == "__main__":
    unittest.main()
