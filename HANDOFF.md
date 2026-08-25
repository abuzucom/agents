# Handoff

Current working state for agent continuity. This file is ephemeral;
clear it only when the user tells you to.
Use CHANGELOG.md for the permanent record.

Each agent appends its own section under "Active work." Do not
overwrite, edit, or remove another agent's section.

## Repo orientation

| Path | Purpose |
|---|---|
| `AGENTS.md` | Source of truth for agent rules |
| `scripts/sync.py` | Copies `AGENTS.md` to tool-specific files |
| `scripts/check_*.py` | CI enforcement scripts (one per rule) |
| `scripts/lint_style.py` | Dash and ASCII lint on `AGENTS.md` |
| `.github/workflows/agents-md-compliance.yml` | Main CI workflow |
| `.github/workflows/sync-check.yml` | Verifies copies stay in sync |

## Active work

**Branch:** `chore/review-path`
**Base:** `main` at `1960515`

| File | Change | Commit | PR |
|---|---|---|---|
| `scripts/check_dockerfile_root.py` L90 | `if` to `elif`; skip redundant `indent != indent` on initialization iteration | `69dd9e7` | pending |
| `scripts/check_commit_message.py` L33 | Remove dead `if sha else ""` guard; sha from `git log %H` is always 40 chars | `69dd9e7` | pending |

## Decisions made

- Em/en dash and non-ASCII duplicate violations in `check_ascii.py` / `lint_style.py`: intentional, keep both.
- `nullglob` + array-length guards in `agents-md-compliance.yml`: keep for defensive shell hygiene.

## Next steps

- [x] Commit changes on `chore/review-path`
- [ ] Open draft PR against `main`
- [ ] Verify CI passes

---

**Agent:** Antigravity (Google DeepMind, Claude Opus 4.6)
**Updated:** 2026-08-25T15:52Z
