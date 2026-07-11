# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
