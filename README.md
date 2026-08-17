# AGENTS.md template

Bootstrap instruction conventions for AI coding agents and their human
collaborators across ABUZUCOM projects. See Tool compatibility and
Banned agents below. Copy into a repository and adapt.

## What's in it

- **Non-negotiable summary** - every critical rule in one line, at the
  top, where model attention is strongest.
- **Thirteen critical rules** - injection, destructive commands, test
  integrity, scope, draft-PR workflow, API contracts, hashing, secrets,
  dependencies, workflow-state verification, CI credential hygiene,
  container privilege, honest enforcement claims.
- **Branch naming** - clean conventions for branch names.
- **Workflow** - test-first, lint-clean, safe editing, retry discipline.
- **Correctness & safety** - divisors, regex backtracking, collection
  mutation, unbounded recursion, log sanitization, idempotency.
- **Concurrency & shared state** - locks, task joining, lock ordering.
- **Code quality and style** - limits and conventions (magic numbers, change size, duplication, TODO/FIXME ban, comments, commit messages, extended ASCII ban) applicable without judgment calls.
- **Orientation template** (commented out, end of file) - Commands, Do not
  touch, Architecture, Gotchas, doc pointers. Per-repo; fill on adoption.
- **`.claudeignore`** - excludes noisy/generated paths (`node_modules/`,
  build output, lockfiles, `.env*`, etc.) from Claude Code's context. Part
  of the template, not optional tooling - see Adopting step 1.
- **`scripts/check_*.py`** and **`.github/workflows/agents-md-compliance.yml`**
  (which calls the reusable `.github/workflows/agents-compliance.yml`) -
  this template's own mechanical enforcement of its rules, dogfooded in its
  own CI and `.pre-commit-config.yaml`; see the Checker reference table under
  Adopting for what each script backs, and Banned agents below for
  `check_banned_agents.py` specifically.
- **`hooks/`** - Claude-Code-specific hooks: an opt-in `PreToolUse` example
  blocking obviously destructive Bash commands, and `enforce_branch_name.py`,
  which is live in this repo through `.claude/settings.json` and refuses
  commits and pushes from a branch that breaks the naming convention; see
  Claude Code hooks below.
- **`tests/`** - the stdlib `unittest` suite covering
  `hooks/enforce_branch_name.py` and its settings wiring. Run it with
  `make test` (or `python -m unittest discover -s tests`); `sync-check.yml`
  runs it on every pull request, and `.pre-commit-config.yaml` runs it when
  a hook, test, settings, or `check_branch_name.py` file changes. No test
  dependencies: `unittest` ships with Python.
- **`plan/HANDOFF.md.example`** - an opt-in per-repo handoff/progress
  template; see Handoff file example below.
- **`SECURITY.md.example`** - an opt-in vulnerability-reporting policy
  template; see Security policy example below.
- **`CONTRIBUTING.md.example`** - an opt-in contribution-guide template;
  see Contributing guide example below.
- **`.github/PULL_REQUEST_TEMPLATE.md`** and
  **`.github/ISSUE_TEMPLATE.md`** - live for this repo, formalizing the
  Summary/Test plan PR shape and a single issue template covering bugs
  and proposals; adopting repos can copy them too, like any other new
  tooling (Rule 9).
- **AgentLint** - `sync-check.yml` also runs
  [AgentLint](https://github.com/0xmariowu/AgentLint), a third-party
  GitHub Action that audits AI-agent-harness setup and scores it across
  6 dimensions. Advisory only (`fail-below: '0'`, never fails the job);
  posts its score as an upserted PR comment. Not one of this repo's own
  `scripts/check_*.py` checkers and not listed in the Checker reference
  table below, since it is not a portable script meant for copying into
  adopting repos.

## Local checks

Run before pushing. Python 3 standard library only, no install step.

| Command | Runs |
|---|---|
| `make test` | `unittest` suite in `tests/` |
| `make check` | `scripts/sync.py --check`, the tool-copy drift check |
| `make lint` | style, American spelling, and English-only checks on AGENTS.md |
| `make sync` | regenerates the tool copies after editing AGENTS.md |

`.pre-commit-config.yaml` runs the same checks on the files each one owns.
CI runs `make test`, `make check`, and the checker scripts on every pull
request through `.github/workflows/sync-check.yml`.

## Adopting

1. Copy `AGENTS.md`, `.claudeignore`, `.gitattributes`, and `.editorconfig` to your repo root - all are
   part of this template. If the target repository already contains custom rules files
   (e.g., CLAUDE.md, .cursorrules), respect those custom rules: do not blindly overwrite them.
   Analyze their content, extract repository-specific guidelines, and merge them into AGENTS.md,
   or flag differences to the user for approval before syncing. Adjust `.claudeignore` patterns
   to the target repo's stack (build output dirs, dependency dirs, secrets globs).
2. Uncomment the orientation block (located directly below "Non-negotiable");
   fill Commands and Do not touch first; delete unused sections. Do not guess or hallucinate
   commands or paths; run static analysis of the repository (e.g., inspecting lockfiles or configuration
   files) to verify correct commands and directories first.
3. Swap code examples to your dominant language if it is not Python.
4. Tool files (`CLAUDE.md`, `GEMINI.md`, etc.) are real copies of
   AGENTS.md (Windows compatibility). After editing AGENTS.md, run
   `make sync` (or manually run `python scripts/sync.py`); `--check` in CI or
   `make check` catches drift. `.claudeignore`, `.gitattributes`, and `.editorconfig`
   are not part of this sync - they are single shared files, copied as-is.
5. Back lintable rules with no shipped checker (nesting, function size, line
   length, empty catches, cond-assign, injection) with linter/semgrep config. If
   you (agent) are doing the integration, do not wire up lint CI, add files, or
   dependencies unprompted (Rule 4); propose linter configuration and CI setup
   for approval first. Every other lintable rule ships a ready-made, portable
   checker instead (see the Checker reference table below): copy the relevant
   one(s) into the target repo and point them at that repo's own globs and CI
   rather than reimplementing from scratch. Propagating each checker, like
   wiring any new CI job, is its own proposal under Rule 9. When writing custom
   CI for these checkers, default to an efficient shape: one job with
   sequential steps per checker group rather than one job per checker, a
   `concurrency: cancel-in-progress` group, and dependency caching once the
   job installs anything beyond stdlib. A repo that wants the checks
   unmodified, with no per-repo CI file to maintain, can instead call this
   repo's reusable workflow directly (see Banned agents and Versioning
   below) rather than copying scripts.
6. Prune rules, and their scripts or CI jobs, that do not apply to the target
   repo, with the user's approval. Example: a static site with no authentication
   or database has no use for the weak-hashing rule or `check_weak_hashing.py`.
   A pruned rule carries no enforcement obligation; rule 13 binds only rules and
   claims that remain in the file. This template's own CI (`sync-check.yml`,
   `agents-md-compliance.yml`) checks copy drift and banned-agent authorship
   only, never rule content, so pruning a rule and rerunning `make sync` passes
   both cleanly. Neither workflow copies into a target repo by default;
   propagating one, like any other checker in this section, is its own
   proposal under Rule 9.
7. Copy `plan/HANDOFF.md.example` if you want a handoff/progress
   convention; fill Status/Next/Blocked per session, delete the
   instructional comment. Propose adopting it to the user first, like
   any other new tooling (Rule 9).
8. Copy `SECURITY.md.example` if you want a vulnerability-reporting
   policy; fill in supported versions, enable GitHub private
   vulnerability reporting (Settings, Security), then rename to
   `SECURITY.md`. Propose adopting it to the user first, like any other
   new tooling (Rule 9).
9. Copy `CONTRIBUTING.md.example` if you want a contribution guide; fill
   in the install/test/lint commands, then rename to `CONTRIBUTING.md`.
   Propose adopting it to the user first, like any other new tooling
   (Rule 9).
10. Wire the branch-name check into the target repo in this same change,
    not as a follow-up. Copy `scripts/check_branch_name.py` and register
    it as a `pre-push` hook (see `.pre-commit-config.yaml` here for the
    `stages: [pre-push]` shape). For Claude Code, also copy
    `hooks/enforce_branch_name.py` and merge the `SessionStart` and
    `PreToolUse` keys from `hooks/claude-code-settings.example.json` into
    the target repo's `.claude/settings.json`. CI alone catches a bad
    branch name only after a pull request exists, and a session handed a
    branch name it did not choose cannot fix that from instructions
    alone; see Branch-name enforcement below. Copy
    `tests/test_enforce_branch_name.py` with the hook and run it in the
    target repo's CI, so a later edit that unregisters the hook fails
    rather than silently disabling enforcement. Propose the hook, the
    test step, and any CI job to the user first, like any other new
    tooling (Rule 9).

### Checker reference

`scripts/check_banned_agents.py` backs Banned agents below, not this table.

| Script | Backs | Exit code | Notes |
|---|---|---|---|
| `check_us_spelling.py` | American spelling | 0, warning only | |
| `check_english_only.py` | English only | 0, warning only | stopword-ratio heuristic, not language detection; real detection needs a dependency (e.g. `langdetect`), a separate Rule 9 proposal |
| `check_hedging.py` | No hedging/fluff/self-justification/self-narration; historical narration in comments | 0, warning only | heuristic keyword match, not NLP; false positives/negatives expected |
| `check_ascii.py` | No run-on sentences/dashes; No non-ASCII characters | 1, blocking | |
| `check_persist_credentials.py` | Rule 11 | 1, blocking | |
| `check_weak_hashing.py` | Rule 7 | 1, blocking | |
| `check_dockerfile_root.py` | Rule 12 | 1, blocking | |
| `check_secrets_heuristic.py` | Rule 8 | 1, blocking | heuristic, not entropy-based; propose gitleaks or detect-secrets (Rule 9) for that |
| `check_branch_name.py` | Branch naming | 1, blocking | usable as a `pre-push` hook, a `pull_request` CI step, or a Claude Code hook through `hooks/enforce_branch_name.py`; no arguments needed |
| `check_commit_message.py` | Commit-message style | 0, warning only | CI-only, takes `--base`/`--head`; not a drop-in `commit-msg` hook, which receives a message-file path instead |

## Banned agents

AGENTS.md contains a banned-agents section (currently xAI/Grok). Instructions
bind only compliant agents; this template's own CI runs
`scripts/check_banned_agents.py` (`.github/workflows/agents-md-compliance.yml`,
via the reusable `.github/workflows/agents-compliance.yml`)
on every pull request, matching commit author, committer, and
`Co-authored-by` trailer fields, plus the PR author, against a denylist. It
cannot catch an agent committing under a human's own identity with no
trailer; pair it with platform-level bot blocks. Adopting repos must copy
the script and wire it into their own CI; it is not part of the sync step.
A repo that wants this check (and the other compliance checks) unmodified
can instead call `uses: abuzucom/agents/.github/workflows/agents-compliance.yml@<tag>`
as a `workflow_call` job - see Versioning below for the `@<tag>` pin.

Do not create pointer or copy files for banned tools; do not add them to
`scripts/sync.py`.

## Versioning

Anything referencing this repo's reusable workflow via `uses:` must pin a
released tag, never `@main` or another moving ref, per Rule 9. No tag has
been cut yet; do not reference `agents-compliance.yml` from another repo
until one exists.

## Tool compatibility

`AGENTS.md` is canonical; tool files are synced copies
(`make sync` or manually `python scripts/sync.py` after editing; `--check` in CI).

| Tool | Reads | How |
|---|---|---|
| ChatGPT / Codex | `AGENTS.md` | Native |
| Cursor | `AGENTS.md`, `.cursorrules` | Native + copy fallback |
| Claude (Claude Code) | `CLAUDE.md` | Synced copy |
| Gemini (CLI) | `GEMINI.md` | Synced copy (or set `contextFileName` to AGENTS.md) |
| Cline / Roo Code | `.clinerules` | Synced copy |
| Windsurf | `.windsurfrules` | Synced copy |
| Aider / OpenHands (local) | `CONVENTIONS.md` | Synced copy; load via `--read CONVENTIONS.md` |
| Other local agents (Zed, Continue, etc.) | `AGENTS.md` or config | Native or point config at it |
| GitHub/Microsoft Copilot | `.github/copilot-instructions.md`, `.copilot-instructions` | Synced copies |
| Mistral, Perplexity, DeepSeek, Lovable | N/A | No repo-file convention: paste AGENTS.md into system prompt / custom instructions / project knowledge |
| xAI/Grok | N/A | Banned - see Banned agents; no pointer files |

Verify against each tool's current docs; conventions shift.

## Claude Code hooks

`hooks/` holds Claude-Code-specific scripts, not part of the AGENTS.md rules
themselves (AGENTS.md stays tool-agnostic; it is synced byte-identical to
non-Claude tools). Each one is a mechanical backstop for a single tool,
independent of whether the model remembers the rule.

### Destructive Bash example (opt-in)

`hooks/block_destructive_bash.py` is an opt-in defense-in-depth example.
This repo's `.claude/settings.json` does not wire it up. A `PreToolUse` hook
on the `Bash` matcher blocks `rm -rf /`, `~`, or `$HOME`, a bare
`git push --force`/`-f`, and `git reset --hard`, mirroring rule 2 and the
history-safety rule in Workflow. It is a heuristic, not a sandbox: it does
not parse the shell, so a command hidden behind a variable, alias, or
wrapper script is invisible to it. To use it, copy the script and
`hooks/claude-code-settings.example.json` into a target repo and merge the
example's `hooks` key into that repo's own `.claude/settings.json`; propose
this to the user first, like any other new tooling (Rule 9).

### Branch-name enforcement (live)

`hooks/enforce_branch_name.py` is live in this repo, wired through
`.claude/settings.json`. It backs the Branch naming conventions section, and
targets a failure mode that no instruction can fix: an agent session handed a
branch name it did not choose (a harness-assigned `claude/<slug>-<id>`, for
example) reads the rule, works on the branch anyway, and finds the conflict
only when `check_branch_name.py` fails CI on an already-open PR. A stateless
session cannot remember that the last one did the same thing, so the check
has to run in the harness rather than in the model's memory.

One script serves two hook events, dispatched on `hook_event_name`:

| Event | Behavior |
|---|---|
| `SessionStart` | Runs `scripts/check_branch_name.py` before the session does any git work; on a violation, injects a stop-and-rename instruction into the session context via `additionalContext` and `systemMessage`. |
| `PreToolUse` (`Bash`) | Exits 2 on a `git commit` or `git push` while the branch name is non-conforming, so a session that ignores the warning still cannot land the branch. |

The split exists because Claude Code ignores a non-zero exit from a
`SessionStart` hook: that event can inform, only `PreToolUse` can refuse.
Renaming the branch (`git branch -m <type>/<kebab-description>`) clears
both, and the rename command itself is never blocked. A repo without
`scripts/check_branch_name.py` has no convention to enforce, so the hook
exits 0 there. Adopting repos copy `hooks/enforce_branch_name.py`,
`scripts/check_branch_name.py`, `tests/test_enforce_branch_name.py`, and
the matching `hooks` keys from `hooks/claude-code-settings.example.json`;
propose it to the user first, like any other new tooling (Rule 9).

`tests/test_enforce_branch_name.py` runs the hook as a subprocess against
synthetic Claude Code payloads, the same path the harness uses. Branch names
come from `GITHUB_HEAD_REF`, which `check_branch_name.py` reads before
falling back to `git rev-parse`, so the results do not depend on which
branch the test run happens to be on. 22 tests cover both events, the
`git branch -m` escape hatch, read-only git commands, non-Bash tools,
empty and malformed stdin, a missing checker, and whether both settings
files still register the hook for each event. That last group is the one
that matters most over time: an unregistered hook enforces nothing while
every behavioral test still passes. Run it with `make test`.

## Handoff file example

`plan/HANDOFF.md.example` is a per-repo handoff/progress template, not
part of the AGENTS.md rules themselves. Nothing in this repo loads it
automatically. It states current status and next steps, each paired
with a command that verifies the claim, instead of narrated prose. Every
line in it follows AGENTS.md's Style section: no hedging, fluff,
self-justification, self-narration, or historical narration (that is
CHANGELOG.md and git log's job, not a handoff file's). To use it, copy
it into a target repo, fill in Status/Next/Blocked, and delete the
instructional comment; propose adopting it to the user first, like any
other new tooling (Rule 9).

Bad: `I think I've mostly finished the config parser, though there
might be some edge cases left to check.`
Good: `Config parser: done. Edge cases: 3/5 covered. Verify: pytest
tests/test_config.py -k edge`

## Security policy example

`SECURITY.md.example` is a per-repo vulnerability-reporting policy
template, not part of the AGENTS.md rules themselves. Nothing in this
repo loads it automatically. It routes reports through GitHub's private
vulnerability reporting (Security tab), which the target repo must
enable first (Settings, Security, Private vulnerability reporting). To
use it, copy it into a target repo, fill in supported versions, rename
it to `SECURITY.md` so GitHub's UI picks it up, and delete the
instructional comment; propose adopting it to the user first, like any
other new tooling (Rule 9).

## Contributing guide example

`CONTRIBUTING.md.example` is a per-repo contribution-guide template for
human contributors, not part of the AGENTS.md rules themselves. AGENTS.md
governs AI agent behavior in this repo; it is not the right document to
hand a human contributor. `CONTRIBUTING.md.example` is self-contained:
it states the shared conventions (branch naming, commit format, code
quality, security review) directly, rather than pointing back into
AGENTS.md. Nothing in this repo loads it automatically. To use it, copy
it into a target repo, fill in the install/test/lint commands, rename it
to `CONTRIBUTING.md`, and delete the instructional comment; propose
adopting it to the user first, like any other new tooling (Rule 9).

## Maintaining

When an agent errs for lack of context, add the line that would have
prevented it. Prune as ruthlessly as you add.

This template repo is exempt from rule 5's branch requirement: maintainers
direct commits to `main` interactively. The exemption does not copy to
adopting repos.
