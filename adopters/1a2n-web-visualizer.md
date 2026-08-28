# Adopter: 1a2n-web-visualizer

See [`../DRIFT.md`](../DRIFT.md) for policy and the adopter's
`docs/template-drift.md` for local differences.

## Adopted at

Template commit `104b611`, mirrored in adopter commit `278f249`.

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

- `hooks/claude-code-settings.example.json` lists only the hooks the adopter
  runs.
- `tests/test_require_consent.py` carries wiring assertions from the declined
  branch-name hook suite.

## Declined

- `scripts/check_git_identity.py`, `hooks/enforce_git_identity.py`, and
  `tests/test_enforce_git_identity.py`
- `hooks/enforce_branch_name.py` and `tests/test_enforce_branch_name.py`. The
  adopter enforces branch names in CI.
- `scripts/check_hedging.py`

## Held only by the adopter

- `scripts/check_action_pins.py`
- `scripts/check_protected_files.py`, whose template adoption was declined
- `scripts/jira_sync.py`
