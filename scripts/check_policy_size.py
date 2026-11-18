#!/usr/bin/env python3
"""Validate the canonical policy size, the assembled size, and required rules.

With no flags the checker fails when AGENTS.md or the assembled policy
exceeds its limit. --json prints a size report for CI and exits 0 after it
prints the report. --render-markdown turns such a report into the pull
request comment body. The renderer treats the report as untrusted data.
"""
import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path


MAX_POLICY_BYTES = 32 * 1024
REQUIRED_TEXT = (
    "## Non-negotiable",
    "## Critical rules",
    "## Code quality",
    "## Style",
    "Change policy safely",
    "Version every change",
    "xAI",
    "Grok",
)
REPORT_SCHEMA = 1
AGENTS_TARGET = "AGENTS.md"
ASSEMBLED_TARGET = "assembled policy"
TARGET_LABELS = {AGENTS_TARGET: "`AGENTS.md`", ASSEMBLED_TARGET: "Assembled policy"}
REPORT_TARGET_NAMES = (AGENTS_TARGET, ASSEMBLED_TARGET)
REPORT_FIELDS = frozenset(("name", "bytes", "limit"))
# Bounds keep a hostile report from producing absurd comment text.
MAX_REPORT_FILE_BYTES = 4096
MAX_REPORTED_BYTES = 16 * 1024 * 1024
PERCENT = 100
COMMENT_MARKER = "<!-- policy-size-report -->"
# Low headroom tempts an agent to cut policy text on its own. The directive
# appears in every failure and every report so the decision stays human.
AGENT_DIRECTIVE = (
    "AGENT DIRECTIVE: Agents must not reduce, trim, condense, reword, move,\n"
    "or remove policy text to meet this limit.\n"
    "Agents must not make an independent decision about policy reduction.\n"
    "Any reduction requires an itemized proposal under the AGENTS.md\n"
    "\"Change policy safely\" rule and explicit active-human approval.\n"
    "Stop work. Report these numbers to the active human. Wait for a decision."
)


def _load_sync():
    """Load sync.py by fixed sibling path, never through sys.path."""
    path = Path(__file__).resolve().parent / "sync.py"
    if path.is_symlink() or not path.is_file():
        raise ImportError("trusted sibling sync.py is missing or not a regular file")
    spec = importlib.util.spec_from_file_location("_policy_size_sync", path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load trusted sibling sync.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_violations(path: Path) -> list[str]:
    violations = []
    try:
        data = path.read_bytes()
    except OSError as error:
        return [f"{path}: cannot read policy: {error}"]
    if len(data) > MAX_POLICY_BYTES:
        violations.append(
            f"{path}: {len(data)} bytes exceeds {MAX_POLICY_BYTES} bytes"
        )
    if b"\r\n" in data:
        violations.append(f"{path}: policy must use LF line endings")
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        return violations + [f"{path}: policy is not ASCII"]
    violations.extend(
        f"{path}: missing required text: {required}"
        for required in REQUIRED_TEXT
        if required not in text
    )
    return violations


def measure_assembled_bytes(root: Path) -> tuple[int, int]:
    """Return the assembled policy size and its limit for root.

    Raises OSError or ValueError when the policy cannot be assembled.
    """
    sync = _load_sync()
    # sync.py compares absolute paths, so a relative root such as "." fails.
    assembled = sync.assemble_policy_bytes(Path(os.path.abspath(root)))
    return len(assembled), sync.MAX_POLICY_BYTES


def find_combined_violations(root: Path) -> list[str]:
    """Return violations for the assembled policy under root."""
    try:
        size, limit = measure_assembled_bytes(root)
    except (ImportError, OSError, ValueError) as error:
        return [f"{ASSEMBLED_TARGET}: cannot assemble: {error}"]
    if size <= limit:
        return []
    return [
        f"{ASSEMBLED_TARGET}: {size} bytes exceeds {limit} bytes"
        f" by {size - limit}"
    ]


def measure_policy(path: Path) -> dict:
    """Return the size report for AGENTS.md and the assembled policy.

    Raises OSError, ImportError, or ValueError when a size is unavailable.
    """
    agents_size = path.stat().st_size
    assembled_size, assembled_limit = measure_assembled_bytes(path.parent)
    return {"schema": REPORT_SCHEMA, "targets": [
        {"name": AGENTS_TARGET, "bytes": agents_size, "limit": MAX_POLICY_BYTES},
        {"name": ASSEMBLED_TARGET, "bytes": assembled_size,
         "limit": assembled_limit},
    ]}


def _validated_count(value: object, minimum: int) -> int:
    """Return value when it is a bounded integer, else raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("size fields must be integers")
    if value < minimum or value > MAX_REPORTED_BYTES:
        raise ValueError("size field is out of range")
    return value


def validate_report(report: object) -> list[tuple[str, int, int]]:
    """Return (name, bytes, limit) rows from an untrusted size report."""
    if not isinstance(report, dict) or report.get("schema") != REPORT_SCHEMA:
        raise ValueError("unknown report schema")
    targets = report.get("targets")
    if not isinstance(targets, list) or len(targets) != len(REPORT_TARGET_NAMES):
        raise ValueError("report must list exactly the known targets")
    rows = []
    for expected_name, target in zip(REPORT_TARGET_NAMES, targets):
        if not isinstance(target, dict) or set(target) != REPORT_FIELDS:
            raise ValueError("report target has unexpected fields")
        if target["name"] != expected_name:
            raise ValueError("report target name is not recognized")
        size = _validated_count(target["bytes"], 0)
        limit = _validated_count(target["limit"], 1)
        rows.append((expected_name, size, limit))
    return rows


def render_markdown(rows: list[tuple[str, int, int]]) -> str:
    """Return the pull request comment body for validated rows."""
    lines = [
        COMMENT_MARKER,
        "## Policy size report",
        "",
        "| Target | Bytes | Limit | Headroom | Used |",
        "|---|---:|---:|---:|---:|",
    ]
    over_limit = []
    for name, size, limit in rows:
        used = size * PERCENT / limit
        lines.append(
            f"| {TARGET_LABELS[name]} | {size:,} | {limit:,} |"
            f" {limit - size:,} | {used:.1f}% |"
        )
        if size > limit:
            over_limit.append(TARGET_LABELS[name])
    lines.append("")
    if over_limit:
        lines.append(f"**Status:** Over limit: {', '.join(over_limit)}.")
    else:
        lines.append("**Status:** Within limits.")
    lines.extend(["", "```text", AGENT_DIRECTIVE, "```", ""])
    return "\n".join(lines)


def _print_report_json(path: Path) -> int:
    """Print the size report as JSON."""
    try:
        report = measure_policy(path)
    except (ImportError, OSError, ValueError) as error:
        print(f"error: cannot measure policy size: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


def _print_rendered_report(report_path: Path) -> int:
    """Print the comment body for an untrusted report file."""
    try:
        with report_path.open("rb") as handle:
            data = handle.read(MAX_REPORT_FILE_BYTES + 1)
        if len(data) > MAX_REPORT_FILE_BYTES:
            raise ValueError("report file exceeds the size limit")
        rows = validate_report(json.loads(data.decode("ascii")))
    except (OSError, ValueError) as error:
        print(f"error: invalid size report: {error}", file=sys.stderr)
        return 1
    print(render_markdown(rows), end="")
    return 0


def _check_limits(path: Path) -> int:
    """Print every violation and the agent directive on failure."""
    violations = find_violations(path) + find_combined_violations(path.parent)
    for violation in violations:
        print(violation, file=sys.stderr)
    if not violations:
        return 0
    print(AGENT_DIRECTIVE, file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path, default=Path("AGENTS.md"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true",
                      help="print the size report as JSON")
    mode.add_argument("--render-markdown", type=Path, metavar="REPORT",
                      help="print the pull request comment for a JSON report")
    args = parser.parse_args(argv)
    if args.render_markdown is not None:
        return _print_rendered_report(args.render_markdown)
    if args.json:
        return _print_report_json(args.path)
    return _check_limits(args.path)


if __name__ == "__main__":
    raise SystemExit(main())
