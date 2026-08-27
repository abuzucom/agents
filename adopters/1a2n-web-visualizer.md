# Adopter: 1a2n-web-visualizer

Owns the adopted-at commit and what that repository took versus declined. The
policy behind this file is [`../DRIFT.md`](../DRIFT.md). What differs locally,
and why, is owned by `docs/template-drift.md` in the adopting repository. This
file does not restate either.

Nothing verifies any of it.

## Adopted at

Template `104b611`, on `feat/consent-gate-hooks`. Mirrored into the adopter at
`278f249`, on a branch of the same name. Both are open pull requests, so the
pairing moves until they merge.

## Taken

| File | Note |
|---|---|
| `scripts/check_ascii.py` | The adopter had `MAX_ASCII_CODEPOINT` first; backported in 1.13.0. |
| `scripts/lint_style.py` | Same. |
| `scripts/check_english_only.py` | The adopter dropped the duplicate `para` first; backported in 1.13.0. |
| `scripts/check_banned_agents.py` | |
| `scripts/check_branch_name.py` | |
| `scripts/check_commit_message.py` | |
| `scripts/check_dockerfile_root.py` | |
| `scripts/check_persist_credentials.py` | |
| `scripts/check_secrets_heuristic.py` | |
| `scripts/check_us_spelling.py` | |
| `scripts/check_weak_hashing.py` | |
| `scripts/sync.py` | |
| `hooks/_gate_core.py` | |
| `hooks/block_destructive_bash.py` | |
| `hooks/block_destructive_powershell.py` | |
| `hooks/require_consent.py` | |
| `hooks/claude-code-settings.example.json` | Differs: it lists only the hooks this adopter runs. |
| `tests/test_block_destructive_bash.py` | |
| `tests/test_block_destructive_powershell.py` | |
| `tests/test_gate_parity.py` | |
| `tests/test_require_consent.py` | Differs: it carries the wiring assertions from a suite this adopter declined. |

## Declined

| File | Reason |
|---|---|
| `scripts/check_git_identity.py` | Not adopted. |
| `hooks/enforce_git_identity.py` | Not adopted. |
| `tests/test_enforce_git_identity.py` | Follows the hook. |
| `hooks/enforce_branch_name.py` | Not adopted; the adopter enforces branch names in CI instead. |
| `tests/test_enforce_branch_name.py` | Follows the hook. It also held `HOOK_MATCHERS` and the launcher-resolution test, which the adopter moved into `tests/test_require_consent.py` rather than lose. That move is why the two copies of that file are not byte-identical. |
| `scripts/check_hedging.py` | Not adopted. |

## Held only by the adopter

`scripts/check_action_pins.py`, `scripts/check_protected_files.py`, and
`scripts/jira_sync.py` exist in `1a2n-web-visualizer` and not here. Porting
`check_protected_files.py` into this template was raised and declined; this
template ships no protected-file check, which Rule 2's enforcement account
already states.
