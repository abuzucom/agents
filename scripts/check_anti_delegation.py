#!/usr/bin/env python3
"""Detect and prohibit delegating recovery commands or manual actions to humans."""
import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from typing import List, Optional

MAX_SCAN_BYTES = 256 * 1024

POLICY_EXEMPT_PREFIXES = (
    "warning:",
    "warning -",
    "policy prohibits",
    "policy forbids",
    "never ask",
    "do not ask",
    "never delegate",
    "do not delegate",
    "strictly prohibited",
    "strictly forbids",
)

CATEGORIES = {
    "command_delegation": (
        r"(?:please\s+)?(?:run|execute|type)\s+.{0,60}(?:in\s+)?(?:powershell|terminal|bash|shell|cmd|command\s+prompt)",
        r"(?:please\s+)?run\s+(?:the\s+following|this)\s+command",
        r"you\s+(?:can|should|need\s+to|must)\s+run\s+",
        r"run\s+this\s+command\s+in\s+powershell",
    ),
    "git_recovery_delegation": (
        r"(?:run|execute)\s+`?git\s+(?:merge|rebase|switch|checkout|branch|reset)\b[^`\n]*`?",
        r"(?:please\s+)?run\s+`?git\s+(?:merge\s+--abort|rebase\s+--abort|switch|checkout|branch\s+-m)`?",
        r"ask(?:ing)?\s+(?:the\s+)?(?:user|human)\s+to\s+(?:run|execute)\s+`?git",
    ),
    "manual_recovery_delegation": (
        r"(?:perform|run|do|require|need|execute)?\s*(?:manual\s+recovery|recover\s+manually)",
        r"(?:the\s+)?(?:user|human)\s+must\s+manually\s+recover",
        r"delegate.{0,30}(?:recovery|action|command).{0,30}(?:to\s+the\s+)?(?:human|user)",
        r"ask\s+(?:the\s+)?(?:user|human)\s+to\s+run\s+recovery\s+manually",
    ),
}


@dataclass
class DelegationFinding:
    """Record of a detected delegation violation."""

    category: str
    pattern: str
    match_text: str
    line_number: int


def _is_exempt_line(line: str) -> bool:
    """Return True if line is a comment or explicit policy prohibition."""
    stripped = line.strip()
    if stripped.startswith(("#", "//", "/*", "*", '"""', "'''")):
        return True
    lowered = stripped.lower()
    for prefix in POLICY_EXEMPT_PREFIXES:
        if lowered.startswith(prefix):
            return True
    return False


def scan_text_for_delegation(text: str) -> List[DelegationFinding]:
    """Scan input text against all anti-delegation rule categories."""
    findings: List[DelegationFinding] = []
    lines = text.splitlines()
    for line_num, line in enumerate(lines, start=1):
        clean = " ".join(line.split())
        if not clean or _is_exempt_line(clean):
            continue
        for category, patterns in CATEGORIES.items():
            matched = False
            for pattern_str in patterns:
                regex = re.compile(pattern_str, re.IGNORECASE)
                match = regex.search(clean)
                if match:
                    findings.append(
                        DelegationFinding(
                            category=category,
                            pattern=pattern_str,
                            match_text=match.group(0),
                            line_number=line_num,
                        )
                    )
                    matched = True
                    break
            if matched:
                break
    return findings


def main(argv: Optional[List[str]] = None) -> int:
    """Run CLI scanner on a file or standard input."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", default="-", help="File to scan (default: stdin)")
    parser.add_argument("--json", action="store_true", help="Output JSON findings")
    args = parser.parse_args(argv)

    if args.file == "-":
        content = sys.stdin.read(MAX_SCAN_BYTES)
    else:
        with open(args.file, "r", encoding="utf-8") as handle:
            content = handle.read(MAX_SCAN_BYTES)

    findings = scan_text_for_delegation(content)
    if args.json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        for finding in findings:
            print(f"[{finding.category}] Line {finding.line_number}: {finding.match_text}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
