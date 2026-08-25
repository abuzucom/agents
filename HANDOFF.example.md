# Handoff

Current working state for agent continuity. This file is ephemeral;
clear it only when the user tells you to.
Use CHANGELOG.md for the permanent record.

Each agent appends its own section under "Active work." Do not
overwrite, edit, or remove another agent's section.

## Repo orientation

<!-- Tailor this table to the target repo's layout. -->

| Path | Purpose |
|---|---|
| `src/` | Application source |
| `tests/` | Test suite |
| `docs/` | Documentation |

## Active work

<!-- Agents append sections here. Example format below. -->

### Session: <agent-name>

- **Branch:** `feat/example-feature`
- **Base:** `main` at `abc1234`
- **Status:** uncommitted; ready to commit and open draft PR

#### Changes

| File | Change | Commit | PR |
|---|---|---|---|
| `src/example.py` L42 | Fix off-by-one in range check | pending | pending |

#### Decisions made

- Kept existing retry logic as-is; user confirmed intentional.

#### Next steps

- [ ] Commit changes
- [ ] Open draft PR against `main`
- [ ] Verify CI passes

---

**Agent:** <agent name and model>
**Updated:** <UTC-0 timestamp>
