# Adopter: 1a2n-web-visualizer

See [`../DRIFT.md`](../DRIFT.md) for policy. The adopter's
`docs/template-drift.md` records local differences.

## Adopted at

Adopter commit `278f249` mirrors template commit `104b611`.

## Taken

- `scripts/check_ascii.py`, `scripts/lint_style.py`,
  `scripts/check_english_only.py`, `scripts/check_banned_agents.py`
- `scripts/check_branch_name.py`, `scripts/check_commit_message.py`,
  `scripts/check_dockerfile_root.py`, `scripts/check_persist_credentials.py`
- `scripts/check_secrets_heuristic.py`, `scripts/check_us_spelling.py`,
  `scripts/check_weak_hashing.py`, `scripts/sync.py`
- `hooks/_gate_core.py`, `hooks/_bash_parser.py`,
  `hooks/block_destructive_bash.py`, `hooks/block_destructive_powershell.py`
- `hooks/require_consent.py`, `hooks/claude-code-settings.example.json`
- `shared-files.json`, `tests/gate_corpus.py`
- `tests/test_block_destructive_bash.py`,
  `tests/test_block_destructive_powershell.py`, `tests/test_gate_parity.py`,
  `tests/test_require_consent.py`
- `scripts/check_hook_coverage.py`, `tools/hook-trace/sitecustomize.py`,
  `hook-coverage-baseline.json`, `tests/test_check_hook_coverage.py`

## Current drift

- `hooks/claude-code-settings.example.json` lists only the hooks in use at the
  adopter.
- `tests/test_require_consent.py` carries wiring assertions from the declined
  branch-name hook suite.

## Declined

- `scripts/check_git_identity.py`, `hooks/enforce_git_identity.py`, and
  `tests/test_enforce_git_identity.py`
- `hooks/enforce_branch_name.py` and `tests/test_enforce_branch_name.py`. The
  adopter enforces branch names in CI.
- `scripts/check_hedging.py`

## Later prose support files

The `scripts/check_hedging.py` decline remains the explicit prose-check
decision for the adopted snapshot. The current bundle in
[`../DRIFT.md`](../DRIFT.md) includes later support files. The following files
remain outside the adopted snapshot. An explicit decision must record status
for each file:

- `scripts/prose_policy.py`
- `scripts/prose_bans.txt`
- `scripts/check_pull_request_message.py`

## Adopter-only files

- `scripts/check_action_pins.py`
- `scripts/check_protected_files.py`. The adopter declined template adoption.
- `scripts/jira_sync.py`
