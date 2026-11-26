"""The template upgrade plan reports base branch verdicts before the first push."""
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import plan_template_upgrade

GIT_IDENTITY = ("-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid")
CODEQL_TEXT = "paths:\n  - legacy\npaths-ignore:\n  - vendor/\n"
CLEAN_MESSAGE = "fix: keep the parser strict\n\nThe parser rejects a malformed record.\n"
BRITISH_MESSAGE = "fix: keep the colour strict\n\nThe parser keeps the colour.\n"


def _git(root: Path, *arguments: str) -> str:
    """Run one fixture Git command and return its output."""
    result = subprocess.run(["git", "-C", str(root), *GIT_IDENTITY, *arguments],
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


class PlanTemplateUpgradeTest(unittest.TestCase):
    """The plan names consumers, CodeQL gaps, and prose findings."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        _git(self.root, "init", "--quiet")
        (self.root / ".github" / "codeql").mkdir(parents=True)
        (self.root / ".github" / "codeql" / "config.yml").write_text(CODEQL_TEXT, encoding="utf-8")
        (self.root / "legacy").mkdir()
        (self.root / "legacy" / "old.py").write_text("x = 1\n", encoding="utf-8")
        (self.root / "keep.py").write_text("y = 2\n", encoding="utf-8")
        _git(self.root, "add", "--all")
        _git(self.root, "commit", "--quiet", "-m", "base")
        self.base = _git(self.root, "rev-parse", "HEAD")

    def run_plan(self, arguments: list) -> tuple:
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            code = plan_template_upgrade.main(arguments, root=self.root)
        return code, output.getvalue()

    def message(self, text: str) -> str:
        path = self.root / "message.txt"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_unchanged_candidate_passes(self) -> None:
        code, output = self.run_plan(["--base", self.base, "--message", self.message(CLEAN_MESSAGE)])
        self.assertEqual(code, 0, output)
        self.assertIn("Expected failures:\n- none", output)
        self.assertIn("immutable-conflict-check.yml", output)
        self.assertIn("1. Prose fixes", output)

    def test_deleted_codeql_path_fails(self) -> None:
        _git(self.root, "rm", "--quiet", "-r", "legacy")
        code, output = self.run_plan(["--base", self.base])
        self.assertEqual(code, plan_template_upgrade.EXPECTED_FAILURE)
        self.assertIn("CodeQL path legacy", output)

    def test_british_message_fails(self) -> None:
        code, output = self.run_plan(["--base", self.base, "--message", self.message(BRITISH_MESSAGE)])
        self.assertEqual(code, plan_template_upgrade.EXPECTED_FAILURE)
        self.assertIn("check_us_spelling.py reports findings", output)

    def test_option_shaped_base_rejected(self) -> None:
        code, _output = self.run_plan(["--base=--output=x"])
        self.assertEqual(code, plan_template_upgrade.USAGE_FAILURE)


if __name__ == "__main__":
    unittest.main()
