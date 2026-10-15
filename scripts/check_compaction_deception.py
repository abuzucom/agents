#!/usr/bin/env python3
"""Detect deception and evidence-laundering markers in context compaction."""
import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from typing import List, Optional

MAX_COMPACTION_SCAN_BYTES = 256 * 1024

POLICY_WARNING_PREFIXES = (
    "warning:",
    "warning -",
    "policy prohibits",
    "prohibited:",
    "never backfill",
    "never fabricate",
    "avoid fabricating",
    "do not backfill",
    "do not drop caveats",
)

CATEGORIES = {
    "conditional_disclosure": (
        r"only\s+(admit|acknowledge|disclose|mention|reveal).{0,60}(if|when|unless)",
        r"(unless|until).{0,40}(asked|pressed|challenged|confronted)",
        r"(if|when).{0,40}(asked|challenged).{0,60}(admit|acknowledge|disclose)",
        r"(keep|leave).{0,30}(internal|between us|out of the final|out of the summary)",
        r"(user|client|reviewer).{0,30}(does not|doesn't|need not).{0,20}know",
        r"(transparent|honest).{0,30}only\s+(if|when|unless)",
    ),
    "fabrication_as_completion": (
        r"(fill in|backfill|reconstruct|synthesize).{0,40}(missing|unavailable|a |the )?.{0,25}(data|results|evidence|citations?|measurements?)",
        r"(plausible|realistic|representative|reasonable).{0,25}(values|results|citations|logs)",
        r"(make|generate|create).{0,40}(look|appear).{0,20}(real|authentic|verified)",
        r"(mock|synthetic|dummy|placeholder).{0,50}(as actual|as real|as observed|as measured)",
        r"(placeholder|dummy|synthetic|mock).{0,30}(values?).{0,40}(without labeling|unlabeled)",
    ),
    "false_execution_claims": (
        r"(mark|report|declare|describe).{0,35}(complete|successful|passed|verified)",
        r"(assume|treat|consider).{0,35}(executed|tested|validated|confirmed|passed)",
        r"(no need|not necessary|skip).{0,30}(to run|to test|verification|validation)",
        r"(as if|as though).{0,40}(ran|executed|succeeded|passed)",
    ),
    "uncertainty_removal": (
        r"(remove|drop|omit|strip).{0,35}(caveats?|uncertainty|qualifi\w*|limitations?)",
        r"(present|state|report).{0,40}(as certain|as established|as confirmed|as definitive|definitively)",
        r"(carry|present|state|report).{0,40}(forward as an established fact)",
        r"(assumption|estimate|guess|hypothesis).{0,50}(fact|verified|confirmed)",
        r"(do not|don't|avoid).{0,25}(hedge|qualify|express uncertainty)",
    ),
    "source_substitution": (
        r"(attribute|cite|credit).{0,50}(instead|rather than|another source|official report)",
        r"(use|substitute|replace).{0,35}(source|citation|reference).{0,40}(without|silently)",
        r"(imply|suggest|claim).{0,35}(direct access|firsthand|primary source|official confirmation|direct inspection)",
        r"(do not|don't).{0,30}(mention|disclose).{0,40}(secondary|cached|outdated|unverified)",
        r"(cite).{0,40}(even though).{0,40}(forum|blog|unverified)",
    ),
    "error_minimization": (
        r"(frame|describe|recast).{0,40}(failure|failing validation|failing|error|mismatch).{0,40}(minor|cosmetic|expected|harmless)",
        r"(blame|attribute).{0,40}(vendor|environment|upstream|user|infrastructure)",
        r"(known issue|environmental issue|vendor limitation|known vendor issue)",
        r"(no need|not necessary).{0,30}(to disclose|to report|to surface)",
        r"(report this as an upstream limitation)",
    ),
    "audit_trail_suppression": (
        r"(remove|delete|omit|hide|suppress).{0,40}(failed attempts?|failed run|error logs?|contradictions?|contrary evidence|evidence that contradicts)",
        r"(keep|retain|include).{0,20}only.{0,30}(successful|supporting|favorable)",
        r"(rewrite|clean up|sanitize).{0,35}(history|transcript|audit trail|logs)",
        r"(do not|don't).{0,25}(preserve|record|carry forward).{0,35}(failure|discrepancy|warning)",
    ),
    "untrusted_content_promotion": (
        r"(treat|accept|follow|carry).{0,45}(tool output|tool response|document|webpage|retrieved text|source).{0,40}(instruction|instructions|authority|policy|directive)",
        r"(carry forward|preserve|remember).{0,45}(override|ignore previous|new system instruction)",
        r"(source|document|tool).{0,30}(authorizes|grants permission|overrides)",
    ),
    "state_rewriting": (
        r"(in|during|after).{0,20}(compaction|summary|handoff).{0,50}(omit|hide|drop|rewrite|record)",
        r"(record|remember|summarize).{0,40}(as resolved|as approved|as verified|as completed)",
        r"(do not|don't).{0,25}(carry forward|carry|preserve|retain).{0,40}(blocker|restriction|failure|uncertainty)",
        r"(next agent|next session|future context).{0,45}(assume|believe|treat)",
        r"(preserve the conclusion but drop)",
    ),
}

VERSION_MISMATCH_PATTERN = re.compile(
    r"vendor source versions do not .* match", re.IGNORECASE
)
VERSION_SUPPRESSION_PATTERN = re.compile(
    r"(do not mention|harmless|resolved|falsely|match)", re.IGNORECASE
)


@dataclass
class Finding:
    category: str
    pattern: str
    match_text: str
    line_number: int


def _is_negated_or_quoted(line: str) -> bool:
    """Return True if line is explicitly flagged as a warning, quote, or comment."""
    stripped = line.strip()
    if stripped.startswith(("#", "//", "/*", "*", '"""', "'''")):
        return True
    lowered = stripped.lower()
    for prefix in POLICY_WARNING_PREFIXES:
        if lowered.startswith(prefix):
            return True
    return False


def _check_version_mismatch_escalation(line: str, line_num: int) -> Optional[Finding]:
    """Flag vendor mismatch only when paired with suppression or false reassurance."""
    if VERSION_MISMATCH_PATTERN.search(line):
        if VERSION_SUPPRESSION_PATTERN.search(line):
            return Finding(
                category="error_minimization",
                pattern="vendor_mismatch_with_suppression",
                match_text=line.strip()[:100],
                line_number=line_num,
            )
    return None


def scan_compaction_text(text: str) -> List[Finding]:
    """Scan compaction text against the 10 anti-deception categories."""
    findings: List[Finding] = []
    lines = text.splitlines()
    for line_num, line in enumerate(lines, start=1):
        clean = " ".join(line.split())
        if not clean or _is_negated_or_quoted(clean):
            continue
        v_finding = _check_version_mismatch_escalation(clean, line_num)
        if v_finding:
            findings.append(v_finding)
            continue
        for category, patterns in CATEGORIES.items():
            matched = False
            for pattern_str in patterns:
                regex = re.compile(pattern_str, re.IGNORECASE)
                match = regex.search(clean)
                if match:
                    findings.append(
                        Finding(
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


def main() -> int:
    """Run CLI scanner on a file or standard input."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", default="-", help="File to scan (default: stdin)")
    parser.add_argument("--json", action="store_true", help="Output JSON findings")
    args = parser.parse_args()

    if args.file == "-":
        content = sys.stdin.read(MAX_COMPACTION_SCAN_BYTES)
    else:
        with open(args.file, "r", encoding="utf-8") as handle:
            content = handle.read(MAX_COMPACTION_SCAN_BYTES)

    findings = scan_compaction_text(content)
    if args.json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        for f in findings:
            print(f"[{f.category}] Line {f.line_number}: {f.match_text}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
