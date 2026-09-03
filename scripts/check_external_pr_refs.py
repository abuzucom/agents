#!/usr/bin/env python3
"""Block autolinked pull request references to an external repository."""
import json
import os
import re
import sys
from pathlib import Path

try:
    from scripts.prose_policy import mask_markdown_code
except ImportError:
    from prose_policy import mask_markdown_code

MAX_EVENT_BYTES = 1024 * 1024
MAX_TITLE_LENGTH = 4096
MAX_BODY_LENGTH = 1024 * 1024
DEPENDABOT_LOGIN = "dependabot[bot]"

# GitHub posts a cross-reference event on the target of an autolinked
# reference. A code span suppresses the autolink, so masked text never
# reaches these patterns. Both patterns stay linear and avoid nested
# quantifiers.
SHORT_REFERENCE = re.compile(
    r"(?<![\w./-])([A-Za-z0-9][\w.-]*)/([\w.-]+?)"
    r"(?:#\d+(?![\w-])|@[0-9a-fA-F]{7,40}(?![0-9A-Za-z-]))"
)
RESOURCE_URL = re.compile(
    r"https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)"
    r"/(?:pull|issues|commit)/\w+",
    re.IGNORECASE,
)


def _load_event(path: Path) -> tuple[str, str, str, str]:
    """Load bounded pull request prose, author, and repository owner."""
    if path.stat().st_size > MAX_EVENT_BYTES:
        raise ValueError("event payload exceeds the size limit")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("event payload must contain an object")
    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, dict):
        raise ValueError("event payload lacks pull request data")
    repository = payload.get("repository")
    if not isinstance(repository, dict):
        raise ValueError("event payload lacks repository data")
    owner = repository.get("owner")
    if not isinstance(owner, dict) or not isinstance(owner.get("login"), str):
        raise ValueError("event payload lacks a repository owner login")
    title = pull_request.get("title")
    body = pull_request.get("body")
    author = pull_request.get("user")
    if not isinstance(title, str):
        raise ValueError("pull request title must contain text")
    if body is None:
        body = ""
    if not isinstance(body, str):
        raise ValueError("pull request body must contain text or null")
    if not isinstance(author, dict) or not isinstance(author.get("login"), str):
        raise ValueError("pull request author must contain a login")
    if len(title) > MAX_TITLE_LENGTH or len(body) > MAX_BODY_LENGTH:
        raise ValueError("pull request prose exceeds the size limit")
    return title, body, author["login"], owner["login"]


def _sanitize(value: str) -> str:
    """Return untrusted text as one bounded single-line fragment."""
    collapsed = " ".join(value.split())
    return collapsed[:120]


def find_external_references(text: str, owner: str, field: str) -> list[str]:
    """Return findings for autolinked references outside the given owner."""
    masked = mask_markdown_code(text)
    findings = []
    for pattern in (SHORT_REFERENCE, RESOURCE_URL):
        for match in pattern.finditer(masked):
            if match.group(1).lower() == owner.lower():
                continue
            reference = _sanitize(match.group(0))
            findings.append(
                f"{field}: autolinked external reference '{reference}' "
                f"notifies another owner; wrap it in a code span"
            )
    return findings


def check_event(path: str | Path) -> int:
    """Return 1 when a pull request cross-references an external owner."""
    try:
        title, body, author, owner = _load_event(Path(path))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: external reference check failed: {error}",
              file=sys.stderr)
        return 1
    if author == DEPENDABOT_LOGIN:
        print("no external-reference findings found")
        return 0
    findings = find_external_references(title, owner, "pull_request.title")
    findings.extend(
        find_external_references(body, owner, "pull_request.body")
    )
    for message in findings:
        print(message)
    if findings:
        return 1
    print("no external-reference findings found")
    return 0


def main() -> int:
    """Check the GitHub event path supplied by the runner environment."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("error: GITHUB_EVENT_PATH is unset", file=sys.stderr)
        return 1
    return check_event(event_path)


if __name__ == "__main__":
    sys.exit(main())
