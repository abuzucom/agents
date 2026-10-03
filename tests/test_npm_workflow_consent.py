"""Route a fixed set of npm workflows to consent only when the repository uses npm."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_enforce_branch_name import HOOK_PATH

GATE_NAME = "hooks/_command_execution_gate.py"
TIMEOUT_SECONDS = 15
OVERSIZED_MANIFEST_BYTES = 1024 * 1024 + 1
PACKAGE_SCRIPTS = {
    "test": "vitest run",
    "lint": "eslint .",
    "typecheck": "tsc --noEmit",
    "build": "tsc",
    "dev": "vite",
}
ALLOWED_COMMANDS = (
    "npm ci", "npm test", "npm test -- src/a.test.ts",
    "npm test -- src/a.test.ts src/b.test.ts",
    "npm run lint", "npm run typecheck", "npm run build",
)
DENIED_COMMANDS = (
    "npx vitest", "npm install", "npm i", "npm audit", "npm exec vitest",
    "npm run dev", "npm run test", "npm run", "npm test --watch",
    "npm test -- --watch", "npm test --", "npm test src/a.test.ts",
    "npm ci --force", "npm run lint --fix", "npm test; git push origin HEAD",
    "npm test && npm run build", "npm test > out.txt", "npm test -- $file",
    "npm test -- missing.test.ts", "npm test -- ../outside.test.ts",
    "npm test -- src", "./npm test", "node script.js",
)


class NpmWorkflowTest(unittest.TestCase):
    """Send npm commands to the real hook inside an isolated repository."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / "repository"
        self.admin = self.root / ".git"
        (self.admin / "objects").mkdir(parents=True)
        (self.admin / "refs" / "heads").mkdir(parents=True)
        self.set_branch("fix/example")
        (self.admin / "config").write_text("[core]\nbare = false\n", encoding="utf-8")
        global_config = self.root.parent / "global.config"
        global_config.write_text("", encoding="utf-8")
        self.environment = {key: value for key, value in os.environ.items()
                            if not key.startswith("GIT_")}
        self.environment.update({"CLAUDE_PROJECT_DIR": str(self.root), "GIT_CONFIG_NOSYSTEM": "1",
                                 "GIT_CONFIG_GLOBAL": str(global_config)})
        self.write_manifest({"name": "fixture", "scripts": PACKAGE_SCRIPTS})
        (self.root / "package-lock.json").write_text("{}", encoding="utf-8")
        (self.root / "src").mkdir()
        for name in ("a.test.ts", "b.test.ts"):
            (self.root / "src" / name).write_text("", encoding="utf-8")
        (self.root.parent / "outside.test.ts").write_text("", encoding="utf-8")

    def set_branch(self, branch: str) -> None:
        """Point the fixture HEAD at one branch name."""
        (self.admin / "HEAD").write_text(f"ref: refs/heads/{branch}\n", encoding="utf-8")

    def write_manifest(self, manifest: dict) -> None:
        """Replace the fixture package.json."""
        (self.root / "package.json").write_text(json.dumps(manifest), encoding="utf-8")

    def run_candidate(self, command: str, client: str = "claude") -> subprocess.CompletedProcess:
        """Send one command payload to the hook without executing the command."""
        payload = {"hook_event_name": "PreToolUse", "permission_mode": "default",
                   "tool_name": "Bash", "tool_input": {"command": command},
                   "workspacePaths": [str(self.root)],
                   "toolCall": {"name": "run_command", "args": {"CommandLine": command}}}
        return subprocess.run(
            [sys.executable, str(HOOK_PATH), "--client", client], input=json.dumps(payload),
            env=self.environment, capture_output=True, text=True,
            timeout=TIMEOUT_SECONDS, check=False,
        )

    def assert_consent(self, command: str) -> None:
        """Require a native ask decision that names the command gate."""
        result = self.run_candidate(command)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "ask")
        self.assertIn(f"blocked by {GATE_NAME}:", output["permissionDecisionReason"])

    def assert_denied(self, command: str) -> None:
        """Require a blocking exit for one command."""
        result = self.run_candidate(command)
        self.assertEqual(result.returncode, 2, result.stdout)

    def test_fixed_npm_workflows_request_consent(self) -> None:
        for command in ALLOWED_COMMANDS:
            with self.subTest(command=command):
                self.assert_consent(command)

    def test_other_npm_shapes_deny(self) -> None:
        for command in DENIED_COMMANDS:
            with self.subTest(command=command):
                self.assert_denied(command)

    def test_absent_manifest_denies_every_npm_workflow(self) -> None:
        (self.root / "package.json").unlink()
        for command in ALLOWED_COMMANDS:
            with self.subTest(command=command):
                self.assert_denied(command)

    def test_undefined_script_denies_its_workflow(self) -> None:
        for name in ("test", "lint", "typecheck", "build"):
            with self.subTest(script=name):
                scripts = {key: value for key, value in PACKAGE_SCRIPTS.items() if key != name}
                self.write_manifest({"scripts": scripts})
                command = "npm test" if name == "test" else f"npm run {name}"
                self.assert_denied(command)

    def test_malformed_manifest_denies(self) -> None:
        for content in ("not json", "[]", '{"scripts": []}', '{"scripts": {"test": 1}}'):
            with self.subTest(content=content):
                (self.root / "package.json").write_text(content, encoding="utf-8")
                self.assert_denied("npm test")

    def test_manifest_without_scripts_allows_only_clean_install(self) -> None:
        self.write_manifest({"name": "fixture"})
        self.assert_consent("npm ci")
        for command in ("npm test", "npm run lint", "npm run build"):
            with self.subTest(command=command):
                self.assert_denied(command)

    def test_oversized_manifest_denies(self) -> None:
        padding = " " * OVERSIZED_MANIFEST_BYTES
        (self.root / "package.json").write_text(
            json.dumps({"scripts": PACKAGE_SCRIPTS}) + padding, encoding="utf-8")
        self.assert_denied("npm test")

    def test_symlinked_manifest_denies(self) -> None:
        target = self.root.parent / "package.json"
        target.write_text(json.dumps({"scripts": PACKAGE_SCRIPTS}), encoding="utf-8")
        (self.root / "package.json").unlink()
        (self.root / "package.json").symlink_to(target)
        self.assert_denied("npm test")

    def test_clean_install_requires_a_lockfile(self) -> None:
        (self.root / "package-lock.json").unlink()
        self.assert_denied("npm ci")
        (self.root / "npm-shrinkwrap.json").write_text("{}", encoding="utf-8")
        self.assert_consent("npm ci")

    def test_absolute_test_path_outside_the_repository_denies(self) -> None:
        self.assert_denied(f"npm test -- {(self.root.parent / 'outside.test.ts').as_posix()}")

    def test_primary_branch_denies_npm_workflows(self) -> None:
        self.set_branch("main")
        for command in ALLOWED_COMMANDS:
            with self.subTest(command=command):
                self.assert_denied(command)

    def test_each_client_uses_its_consent_response(self) -> None:
        for client in ("gemini", "antigravity", "codex"):
            with self.subTest(client=client):
                result = self.run_candidate("npm test", client=client)
                if client == "codex":
                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertIn("execution consent", result.stderr)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout)["decision"], "ask")


if __name__ == "__main__":
    unittest.main()
