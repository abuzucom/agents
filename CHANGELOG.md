# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.7.1] - 2026-08-15

### Added
- Added a Style rule banning hedging qualifiers, self-justification, self-narration, prompt/task/plan references, tutorial-mode narration, and justification theater in prose, documentation, CHANGELOG entries, and code comments.
- Extended the "Comment the why" rule to ban historical narration in comments (referencing removed code or prior implementations); git history covers that.
- Added `scripts/check_hedging.py`, a portable, warning-only heuristic checker backing both rules above, matching phrase lists plus generic filler comment openers (`# Note:`, `# This function`, `# Handle errors`, etc.).
- Added a `check_hedging.py` step to `sync-check.yml`'s existing `check-sync` job, with no new job or checkout/setup-python cost.
- Added a `check_hedging.py` row to the README Checker reference table.

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
