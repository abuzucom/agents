#!/usr/bin/env python3
"""CI scans cover hooks/, and checker dependencies install by hash (S-16, S-17)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
SHA256_HASH = re.compile(r"--hash=sha256:[0-9a-f]{64}")
PINNED_REQUIREMENT = re.compile(r"^([A-Za-z0-9_.-]+)==([0-9][0-9A-Za-z.]*)")
LOCAL_INSTALL = "python -m pip install --requirement requirements-checkers.txt"


def read_text(path: Path) -> str:
    """Return one repository file as text."""
    return path.read_text(encoding="utf-8")


def step_block(workflow: str, step_name: str) -> str:
    """Return the text of one named workflow step up to the next step."""
    text = read_text(WORKFLOWS / workflow)
    start = text.index(f"- name: {step_name}")
    end = text.find("\n      - ", start + 1)
    return text[start:] if end == -1 else text[start:end]


def requirement_blocks() -> list:
    """Return each requirement in requirements-checkers.txt with its hash lines."""
    blocks = []
    for line in read_text(ROOT / "requirements-checkers.txt").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("--hash="):
            blocks[-1].append(stripped)
        else:
            blocks.append([stripped])
    return blocks


class ScanCoverageTest(unittest.TestCase):
    """The weak-hash and secrets scans include the hook sources."""

    def test_ci_scans_include_hooks(self):
        for step in ("Check for unjustified MD5/SHA-1", "Check for likely secrets"):
            with self.subTest(step=step):
                self.assertIn("hooks/*.py", step_block("agents-compliance.yml", step))

    def test_pre_commit_scans_include_hooks(self):
        text = read_text(ROOT / ".pre-commit-config.yaml")
        for hook_id in ("check-weak-hashing", "check-secrets-heuristic"):
            with self.subTest(hook_id=hook_id):
                block = text[text.index(f"id: {hook_id}"):]
                files_line = next(line for line in block.splitlines() if "files:" in line)
                pattern = re.compile(files_line.split("files:", 1)[1].strip())
                self.assertTrue(pattern.search("hooks/_gate_core.py"))
                self.assertTrue(pattern.search("scripts/sync.py"))


class HashPinTest(unittest.TestCase):
    """Every checker requirement carries an exact version and sha256 hashes."""

    def test_each_requirement_is_hash_pinned(self):
        blocks = requirement_blocks()
        self.assertTrue(blocks)
        for block in blocks:
            with self.subTest(requirement=block[0]):
                self.assertRegex(block[0].rstrip(" \\"), PINNED_REQUIREMENT)
                self.assertTrue(block[1:], "no --hash lines")
                for hash_line in block[1:]:
                    self.assertRegex(hash_line.rstrip(" \\"), SHA256_HASH)

    def test_local_installs_require_hashes(self):
        text = read_text(WORKFLOWS / "sync-check.yml")
        self.assertNotIn(LOCAL_INSTALL + "\n", text)
        self.assertGreater(text.count(LOCAL_INSTALL + " --require-hashes"), 0)

    def test_pre_commit_pins_match_the_requirements_version(self):
        name, version = PINNED_REQUIREMENT.match(requirement_blocks()[0][0]).groups()
        pins = re.findall(re.escape(name) + r"==([0-9][0-9A-Za-z.]*)",
                          read_text(ROOT / ".pre-commit-config.yaml"))
        self.assertTrue(pins)
        self.assertEqual(set(pins), {version})


if __name__ == "__main__":
    unittest.main()
