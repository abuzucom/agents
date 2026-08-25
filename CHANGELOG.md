# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added handoff planning trigger to `AGENTS.md` (and synced copies) requiring agents to enter planning mode (Claude Code: plan mode; Antigravity: implementation plan artifact; ChatGPT/Codex: plan proposal) upon detecting handoff changes.
- Added security guardrails and sensitive data protections to `plan/HANDOFF.md.example`, defining untrusted status data, prohibiting secrets, PII, and private vulnerability details, and guiding untracked/gitignored live handoffs for sensitive repos.

### Fixed
- Fixed redundant condition in `scripts/check_dockerfile_root.py`: `if` to `elif` on the service-indent comparison so the first iteration skips the guaranteed-false `indent != indent` check.
- Removed dead `if sha else ""` guard in `scripts/check_commit_message.py`: sha from `git log --format=%H` is always 40 characters; the fallback was unreachable.

## [1.12.0] - 2026-08-20

### Added
- Added AGENTS.md Rule 14, "Verify the git identity before the first commit", and a matching item 14 in the Non-negotiable summary. The rule requires checking `git config user.name` and `user.email` before the first commit of a session, states that git does not inherit the `gh` identity, restricts commit emails to GitHub noreply addresses, and refers a wrong identity already in history to the existing pushed-history consent rule instead of a rewrite.
- Added `scripts/check_git_identity.py`, a portable blocking checker with three modes: no arguments checks the identity the next commit would use, reading the environment variables git treats as explicit before `user.name` and `user.email`; `--unpushed` checks commits absent from every remote-tracking ref; `--base`/`--head` checks a pull request range. `--allow` takes a regex for repos on another convention, and `--advise` adds `gh` and `user.useConfigOnly` notes that never change the exit code.
- Added `hooks/enforce_git_identity.py`, a Claude Code hook backing Rule 14 from the harness. On `SessionStart` it runs the checker with `--advise` and injects a stop-and-ask instruction into the session context; on `PreToolUse` (`Bash` matcher) it exits 2 on a `git commit` under an unset or disallowed identity, and on a `git push` when either the current config or any commit that push would publish fails. `git config` is never blocked.
- Added `tests/test_enforce_git_identity.py`, 42 stdlib `unittest` tests running the hook and the checker against a throwaway git repo, so results do not depend on the identity configured on the machine running them. Covers both events, unset and disallowed identities, environment-supplied identities, the `git config` escape hatch, the `--unpushed` path, GitHub's squash-merge committer, `[bot]` addresses, and whether both settings files still register the hook for each event.
- Added both `enforce_git_identity.py` entries to `.claude/settings.json` and `hooks/claude-code-settings.example.json`, inside the existing `Bash` matcher.
- Added a `check-git-identity` pre-commit hook and a `check-unpushed-identity` pre-push hook to `.pre-commit-config.yaml`, a "Check commit identities" step to the `pr-checks` job in `agents-compliance.yml`, and an `identity` target to the Makefile.
- Added a README "Git identity enforcement (live)" subsection under Claude Code hooks, a "Git identity outside this repository" section covering the machine, account, and organization settings a repository file cannot reach, and Adopting step 11.

### Changed
- Widened the `hook-tests` pre-commit `files` pattern to cover `scripts/check_git_identity.py`.
- Updated the README critical-rule count to fourteen, the `hooks/` and `tests/` bullets, the Local checks table, and the Checker reference table.
- Synced the AGENTS.md Rule 14 addition into all eight tool copies.

## [1.11.0] - 2026-08-17

### Added
- Added `hooks/enforce_branch_name.py`, a Claude Code hook backing the Branch naming conventions section from the harness instead of the model's memory. On `SessionStart` it runs `scripts/check_branch_name.py` before the session does any git work and injects a stop-and-rename instruction into the session context; on `PreToolUse` (`Bash` matcher) it exits 2 on a `git commit` or `git push` while the branch name is non-conforming.
- Added `.claude/settings.json`, wiring `enforce_branch_name.py` into both events for this repo. `block_destructive_bash.py` stays opt-in and is not wired up.
- Added both `enforce_branch_name.py` hook entries to `hooks/claude-code-settings.example.json`, alongside the existing `block_destructive_bash.py` entry.
- Added a README "Branch-name enforcement (live)" subsection under a renamed "Claude Code hooks" section, splitting the live branch hook from the opt-in destructive-Bash example.
- Added two paragraphs to AGENTS.md's Branch naming conventions section: a harness-assigned or dispatcher-assigned branch name is not an exception and gets renamed before the first commit, and adopting repos wire the branch check in (pre-push hook, plus the two Claude Code hook events) in the same change that adds AGENTS.md.
- Added README Adopting step 10 covering that wiring.
- Added `tests/test_enforce_branch_name.py`, 22 stdlib `unittest` tests covering both hook events, the `git branch -m` escape hatch, read-only git commands, non-Bash tools, empty and malformed stdin, an absent checker, and whether `.claude/settings.json` and `hooks/claude-code-settings.example.json` still register the hook for each event. No new dependency.
- Added a `test` target to the Makefile, a "Run tests" step to `sync-check.yml`, and a `hook-tests` pre-commit hook scoped to `hooks/`, `tests/`, `.claude/settings.json`, and `scripts/check_branch_name.py`.
- Added a README "Local checks" section listing the four make targets, a `tests/` bullet under "What's in it", and test coverage detail under Branch-name enforcement.
- Added an AGENTS.md paragraph requiring adopting repos to copy the hook's test suite and run it in CI and pre-commit.

### Changed
- Updated the README `hooks/` bullet and `check_branch_name.py` Checker reference row for the new hook, and corrected the claim that this repo has no `.claude/` directory.
- Synced the AGENTS.md branch-naming additions into all eight tool copies.

## [1.10.0] - 2026-08-15

### Added
- Added `CONTRIBUTING.md.example`, an opt-in, self-contained contribution guide for human contributors, covering setup, naming/comment conventions, security and review practices, code quality, and workflow, each item drawn from an explicit item-by-item review of AGENTS.md's rules.
- Added `.github/PULL_REQUEST_TEMPLATE.md` (live), formalizing the Summary/Test plan PR shape used throughout this project's history.
- Added `.github/ISSUE_TEMPLATE.md` (live), a single legacy-format template covering both bug reports and rule/template proposals.
- Added a README "Contributing guide example" section and Adopting step 9 documenting the new template.
- Extended `check_us_spelling.py`, `check_english_only.py`, `check_hedging.py`, and `check_ascii.py` in `sync-check.yml` to also scan all three new files.

## [1.9.0] - 2026-08-15

### Added
- Added `SECURITY.md.example`, an opt-in vulnerability-reporting policy template routing reports through GitHub's private vulnerability reporting, conforming to AGENTS.md's Style section throughout.
- Added a `## Security` line to AGENTS.md's commented-out orientation template, pointing at `SECURITY.md.example`.
- Added a README "Security policy example" section and Adopting step 8 documenting the new template.
- Extended `check_us_spelling.py`, `check_english_only.py`, `check_hedging.py`, and `check_ascii.py` in `sync-check.yml` to also scan `SECURITY.md.example`.

## [1.8.0] - 2026-08-15

### Added
- Added `plan/HANDOFF.md.example`, an opt-in per-repo handoff/progress template pairing every status claim with a command that verifies it, conforming to AGENTS.md's Style section throughout.
- Added a `## Handoff` line to AGENTS.md's commented-out orientation template, pointing at `plan/HANDOFF.md.example`.
- Added a README "Handoff file example" section and Adopting step 7 documenting the new template.
- Extended `check_us_spelling.py`, `check_english_only.py`, and `check_hedging.py` in `sync-check.yml` to also scan `plan/HANDOFF.md.example`.
- Added a `check_ascii.py` step to `sync-check.yml`'s `check-sync` job, covering `plan/HANDOFF.md.example`'s dash/ASCII conformance.

## [1.7.3] - 2026-08-15

### Added
- Added AgentLint (`0xmariowu/AgentLint@v1.1.13`) to `sync-check.yml`'s `check-sync` job, an advisory, third-party AI-agent-harness audit, pinned to an exact tag with `fail-below: '0'` so it never fails the job.
- Added a `pull-requests: write` permission and an `actions/github-script@v9.0.0` step posting AgentLint's score as an upserted PR comment (find-and-update via a marker HTML comment, not a new comment per push).
- Added a README bullet documenting AgentLint's integration, separate from the Checker reference table since it is a third-party action, not a portable `scripts/check_*.py` checker.
- Added `format: md`/`output-dir` to the AgentLint step and a report-reading step, embedding the full generated report in a collapsible section of the PR comment below the score table.

## [1.7.2] - 2026-08-15

### Added
- Added a Style rule banning hedging qualifiers, self-justification, self-narration, prompt/task/plan references, tutorial-mode narration, and justification theater in prose, documentation, CHANGELOG entries, and code comments.
- Extended the "Comment the why" rule to ban historical narration in comments (referencing removed code or prior implementations); git history covers that.
- Added `scripts/check_hedging.py`, a portable, warning-only heuristic checker backing both rules above, matching phrase lists plus generic filler comment openers (`# Note:`, `# This function`, `# Handle errors`, etc.).
- Added a `check_hedging.py` step to `sync-check.yml`'s existing `check-sync` job, with no new job or checkout/setup-python cost.
- Added a `check_hedging.py` row to the README Checker reference table.

### Fixed
- Synced all tool rule copies with `AGENTS.md`.

## [1.7.1] - 2026-08-15

### Added
- Added a Branch naming rule banning `claude/`-prefixed branches by name, so a model cannot rationalize past an implicit "match one of these five prefixes" statement.
- Added a Branch naming exemption for automated dependency-update tools (Dependabot): their branch and commit format is not configurable.
- Added `.github/workflows/agents-compliance.yml`, a reusable `workflow_call` workflow holding the `pr-checks` and `static-checks` jobs, as an opt-in path for downstream repos that want the compliance checks unmodified, alongside the existing copy-and-tailor adoption path.
- Added a Rule 9 note: pin any `uses:` reference to this repo's reusable workflow to a released tag, never `@main`.
- Added `concurrency: cancel-in-progress` groups to `sync-check.yml` and `agents-md-compliance.yml`, cancelling superseded runs on the same branch or PR.
- Added `ready_for_review` to `agents-md-compliance.yml`'s `pull_request` trigger types, so a PR leaving draft status re-runs its draft-skipped jobs instead of staying stuck at "skipped".

### Changed
- Consolidated `agents-md-compliance.yml` from 4 jobs to a thin caller of `agents-compliance.yml`'s 2 jobs, halving redundant checkout/setup-python overhead per PR run.
- Made `scripts/check_commit_message.py` warning-only (always exits 0), matching `check_us_spelling.py`/`check_english_only.py`, instead of blocking on subject-format violations.
- Exempted Dependabot PRs from the `branch-name` and `commit-message` checks, keyed on PR author (`github.event.pull_request.user.login`) rather than `github.actor`, since a human pushing to or rebasing a Dependabot branch changes the triggering actor but not the PR's author.
- Updated README's "Adopting"/"Banned agents" sections with the reusable-workflow option, a CI efficiency pattern for repos writing custom checker CI, and a new Versioning section.

### Fixed
- Synced all tool rule copies with `AGENTS.md`.

## [1.7.0] - 2026-08-08

### Added
- Added `scripts/` references to the dash/ASCII rule (`lint_style.py`/`check_ascii.py`) and the American spelling/English-only rules (`check_us_spelling.py`/`check_english_only.py`, marked warning only), completing the enforcement markers across every rule with a shipped checker.
- Added a Checker reference table to README, replacing the prose paragraphs Adopting step 5 had accumulated across three prior releases.
- Added `hooks/block_destructive_bash.py`, an opt-in Claude Code `PreToolUse` hook example blocking `rm -rf /`/`~`/`$HOME`, bare `git push --force`/`-f`, and `git reset --hard`.
- Added `hooks/claude-code-settings.example.json`, the wiring example for the hook above.
- Added a README "Claude Code hook example" section documenting both files; not referenced from AGENTS.md, which stays tool-agnostic.

### Changed
- Consolidated the per-PR checker bullets in README's "What's in it" into a single entry pointing at the Checker reference table.

### Fixed
- Synced all tool rule copies with `AGENTS.md`.
>>>>>>> origin/main

## [1.6.0] - 2026-08-08

### Added
- Added `scripts/check_branch_name.py`, backing Branch naming by validating `<type>/<kebab-description>` against the documented prefixes, exempting `main`, `master`, and detached HEAD.
- Added `scripts/check_commit_message.py`, backing the commit-message style bullet by validating `type: description` shape, 50-character length, and no trailing period, stripping a trailing GitHub squash-merge suffix first.
- Added `branch-name` and `commit-message` jobs to `agents-md-compliance.yml`, running on every pull request.
- Added a `check-branch-name` pre-commit hook at the `pre-push` stage.
- Added inline `scripts/` references to Branch naming and the commit-message style bullet.

### Fixed
- Synced all tool rule copies with `AGENTS.md`.

## [1.5.0] - 2026-08-08

### Added
- Added `scripts/check_persist_credentials.py`, backing rule 11 by scanning workflow files for `actions/checkout` steps missing `persist-credentials: false`.
- Added `scripts/check_weak_hashing.py`, backing rule 7 by flagging MD5/SHA-1 calls with no same-line justification comment.
- Added `scripts/check_dockerfile_root.py`, backing rule 12 by flagging Dockerfiles, compose files, and Kubernetes manifests with no non-root user configured.
- Added `scripts/check_secrets_heuristic.py`, backing rule 8 with a heuristic match on structured secret-token prefixes and a `.env`/`.env.local` filename block.
- Added a Rule 12 exception comment, `# runtime-root: this container <reason> (Rule 12 exception).`, mirroring rule 11's escape hatch.
- Added a `static-checks` job to `agents-md-compliance.yml`, running all four new checkers on every push and pull request to `main`.
- Added local pre-commit hooks for all four checkers, scoped to their relevant file globs.
- Added inline `scripts/` references to rules 7, 8, 11, and 12, and Adopting-step guidance for propagating them.

### Fixed
- Synced all tool rule copies with `AGENTS.md`.

## [1.4.0] - 2026-08-08

### Added
- Added rule 13, **Back enforcement claims with real checks**: no rule may claim CI or tooling enforcement it lacks; propose the check in the same change that adds an enforceable rule.
- Added `scripts/check_banned_agents.py`, matching commit author, committer, and `Co-authored-by` trailer fields, plus the PR author, against a banned-agent denylist.
- Added `.github/workflows/agents-md-compliance.yml`, running the check on every pull request.
- Added `README.md` Adopting step 6: adopting repos may prune rules and their checks that do not apply, with user approval, without violating rule 13.

### Changed
- Rewrote the Banned agents section's enforcement claim to name the real script and its limitation (cannot catch a banned agent committing under a human's own identity with no trailer).

### Fixed
- Synced all tool rule copies with `AGENTS.md`.

## [1.3.0] - 2026-08-08

### Added
- Added `**American English spelling**` rule banning British spelling variants (`-our`, `-ise`/`-isation`, `-re`, etc.) even though they are valid ASCII.
- Added `**English only**` rule requiring English in code, comments, commit messages, and documentation, with comments always English and no exception for Chinese, Japanese, or Korean, even in a codebase targeting those markets.
- Added `scripts/check_us_spelling.py`, a portable, warning-only checker for the American spelling rule, usable in any repo.
- Added `scripts/check_english_only.py`, a portable, warning-only stopword heuristic for the English-only rule, usable in any repo.
- Added `scripts/check_ascii.py`, a portable, blocking checker mirroring `lint_style.py`'s existing dash and ASCII checks for use outside this repo.
- Added the two new warning-only checks to `make lint` and to the CI style-lint step.
- Added `README.md` guidance for propagating all three new checkers into adopting repos, including each script's exit-code contract.

### Fixed
- Synced all tool rule copies with `AGENTS.md`.

## [1.2.0] - 2026-07-19

### Added
- Added rule requiring `persist-credentials: false` on `actions/checkout` steps that do not need the credential afterward.
- Added rule requiring non-root Docker containers by default, with explicit user consent required before configuring runtime root.

### Fixed
- Set `persist-credentials: false` on the `sync-check.yml` checkout step per the new rule.
- Synced all tool rule copies with `AGENTS.md`.

## [1.1.0] - 2026-07-16

### Added
- Added `**No suppressing checks**` rule banning `# noqa`, `type: ignore`, and disabling CI steps to force a pass.
- Added history-safety rule forbidding force-push, rebase, amend, or reset of pushed commits on shared branches without consent.
- Added `**No run-on sentences**` rule prohibiting clause-splicing.
- Added `scripts/lint_style.py`, a `make lint` target, and a CI style-lint step enforcing the dash and ASCII rules on `AGENTS.md`.

### Changed
- Strengthened the em/en dash rule to ban hyphen substitutes (`--`, `---`, spaced ` - `) and reframed it around run-on sentences.
- Closed self-attested loopholes: weak-hashing exception, always-draft PRs (removed the integration-tool exception), test-first mocking, retry discipline, and magic-number naming.
- Renamed `**No extended ASCII**` to `**No non-ASCII characters**` and restricted Unicode to string literals or data.
- Replaced incomplete-work rule to cover markers beyond `TODO`/`FIXME` (`XXX`, `HACK`, stubs, bare `pass`).
- Required commit detail in the body rather than truncating the subject.
- Tightened AGENTS.md prose throughout to cut needless words.

### Fixed
- Fixed `AGENTS.md` self-violations of its own dash and ASCII rules, and replaced emoji `Bad`/`Good` markers with ASCII.
- Synced all tool rule copies with `AGENTS.md`.

## [1.0.0] - 2026-07-11

### Added
- Added `**Documentation and versioning**` rule specifying target README/CHANGELOG updates and Semantic Versioning (SemVer 2.0.0) requirements.
- Added `**Imperative tone**` style rule.
- Added `**Path traversal**` correctness and safety rule.
- Added `.copilot-instructions` (root-level) and `.github/copilot-instructions.md` to rules sync script.
- Added local pre-commit hook (`.pre-commit-config.yaml`) and task runner (`Makefile`) for sync checks.
- Added GitHub Actions workflow (`.github/workflows/sync-check.yml`) running in CI with read-only permissions.
- Added **Roo Code** and **OpenHands** compatibility instructions to `README.md`.

### Changed
- Overhauled `AGENTS.md` prose to use imperative, professional, and terse tone.
- Excluded redundant rule copy files in `.claudeignore` to reduce context token waste.
- Formatted example lines with double-space markdown line breaks instead of bullet lists.
- Updated `Adopting` guidelines in `README.md` to prevent agent integration pitfalls (respecting custom rules, verifying commands, and preventing unauthorized changes).

### Fixed
- Synced all tool rule copies (`CLAUDE.md`, `GEMINI.md`, etc.) with `AGENTS.md`.
