#!/usr/bin/env python3
"""Fail on long test names added in a `--base`/`--head` commit range.

The AGENTS.md Test names rule allows at most five words after `test_`.
This check covers test functions under `tests/` that the range adds or
renames. Names present in the base version at the same path pass. A
renamed test file gets no exemption. Exits 1 on any finding or on any
Git, decoding, or parse failure.
"""
import argparse
import ast
import os
import subprocess
import sys

try:
    from scripts.trusted_git import run_git
except ModuleNotFoundError:
    from trusted_git import run_git

MAX_TEST_NAME_WORDS = 5
TEST_PREFIX = "test_"
TESTS_DIRECTORY = "tests/"
PYTHON_SUFFIX = ".py"
MAX_BLOB_BYTES = 4 * 1024 * 1024
CHANGED_STATUSES = ("A", "M", "R")


def count_name_words(name: str) -> int:
    """Return the number of `_`-separated words after `test_`."""
    return len([word for word in name[len(TEST_PREFIX):].split("_") if word])


def resolve_commit(repo: str, revision: str) -> str:
    """Return the full commit ID for one revision."""
    result = run_git(
        repo,
        ["rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}"],
        check=True, runner=subprocess.run,
    )
    return result.stdout.strip()


def is_test_path(path: str) -> bool:
    """Return True for a Python file below `tests/` without `..` segments."""
    if ".." in path.split("/"):
        return False
    return path.startswith(TESTS_DIRECTORY) and path.endswith(PYTHON_SUFFIX)


def parse_name_status(stdout: str) -> list[tuple[str, str]]:
    """Return (base path or empty, head path) pairs for changed test files."""
    fields = stdout.split("\0")
    pairs = []
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index][:1]
        if status == "R":
            old_path, new_path = fields[index + 1], fields[index + 2]
            index += 3
        else:
            old_path = new_path = fields[index + 1]
            index += 2
        if status not in CHANGED_STATUSES or not is_test_path(new_path):
            continue
        pairs.append(("" if status == "A" else old_path, new_path))
    return pairs


def list_changed_tests(repo: str, base: str, head: str) -> list[tuple[str, str]]:
    """Return changed test file pairs between two commits."""
    result = run_git(
        repo,
        ["diff", "--name-status", "-z", "-M", "--no-ext-diff", base, head, "--", "tests"],
        check=True, runner=subprocess.run,
    )
    return parse_name_status(result.stdout)


def read_blob_size(repo: str, commit: str, path: str) -> int:
    """Return one blob's size in bytes without reading its content."""
    result = run_git(repo, ["cat-file", "-s", f"{commit}:{path}"], check=True, runner=subprocess.run)
    return int(result.stdout.strip())


def read_blob(repo: str, commit: str, path: str) -> str:
    """Return one file's text at a commit.

    The size query runs first. An oversize blob never enters memory.
    """
    blob_size = read_blob_size(repo, commit, path)
    if blob_size > MAX_BLOB_BYTES:
        raise ValueError(f"file {path} holds {blob_size} bytes over the {MAX_BLOB_BYTES} byte cap")
    result = run_git(repo, ["cat-file", "blob", f"{commit}:{path}"], check=True, runner=subprocess.run)
    if len(result.stdout.encode("utf-8")) > MAX_BLOB_BYTES:
        raise ValueError(f"file {path} grew past the {MAX_BLOB_BYTES} byte cap during the read")
    return result.stdout


def collect_test_names(source: str, path: str) -> dict[str, tuple[str, int]]:
    """Map each class-qualified test name to its bare name and line.

    Module and class bodies hold test functions. An explicit stack walks
    nested classes without recursion.
    """
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as error:
        raise ValueError(f"syntax error in {path} at line {error.lineno} ({error.msg})") from error
    names = {}
    stack = [(tree.body, "")]
    while stack:
        body, prefix = stack.pop()
        for node in body:
            if isinstance(node, ast.ClassDef):
                stack.append((node.body, f"{prefix}{node.name}."))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(TEST_PREFIX):
                names[f"{prefix}{node.name}"] = (node.name, node.lineno)
    return names


def find_file_violations(repo: str, base: str, head: str, pair: tuple[str, str]) -> list[str]:
    """Return findings for new long test names in one changed file.

    The base comparison uses bare names. A test moved to another class or
    under a renamed class keeps its exemption. A renamed file gets no
    exemption. Every long name in it counts as new.
    """
    base_path, head_path = pair
    head_names = collect_test_names(read_blob(repo, head, head_path), head_path)
    base_bare_names = set()
    if base_path == head_path:
        base_entries = collect_test_names(read_blob(repo, base, base_path), base_path)
        base_bare_names = {name for name, _line in base_entries.values()}
    findings = []
    for name, line in sorted(head_names.values(), key=lambda entry: entry[1]):
        word_count = count_name_words(name)
        if name in base_bare_names or word_count <= MAX_TEST_NAME_WORDS:
            continue
        findings.append(
            f"{head_path}:{line}: {name} has {word_count} words after {TEST_PREFIX}"
            f" (limit {MAX_TEST_NAME_WORDS})"
        )
    return findings


def check(base: str, head: str, repo: str) -> int:
    """Print findings for base..head. Return 1 on any finding, else 0."""
    base_commit = resolve_commit(repo, base)
    head_commit = resolve_commit(repo, head)
    findings = []
    for pair in list_changed_tests(repo, base_commit, head_commit):
        findings.extend(find_file_violations(repo, base_commit, head_commit, pair))
    for finding in findings:
        print(finding)
    if not findings:
        return 0
    print(f"Rename each listed test to at most {MAX_TEST_NAME_WORDS} words after {TEST_PREFIX}.", file=sys.stderr)
    return 1


def main() -> int:
    """Parse arguments and run the range check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="base revision (exclusive)")
    parser.add_argument("--head", required=True, help="head revision (inclusive)")
    parser.add_argument("--repo", default=os.getcwd(), help="repository to inspect (default: cwd)")
    args = parser.parse_args()
    try:
        return check(args.base, args.head, args.repo)
    except (OSError, subprocess.CalledProcessError, UnicodeError, ValueError, IndexError) as error:
        print(f"Test name check failed ({error}). Fix the cause and rerun.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
