# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
