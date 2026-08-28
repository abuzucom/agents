# Drift

The default `scripts/sync.py` operation keeps the AGENTS.md family content
identical across its eight tool copies after line-ending normalization. Shared
manifest modes cover the gate files described below. Other files under
`scripts/`, `hooks/`, and `tests/` are maintained separately after adoption.

`scripts/sync.py --check-shared` verifies each repository's local shared files
against that repository's local `shared-files.json`. It does not inspect or
compare another repository. A change fails only the local check while the local
file and manifest disagree. It does not automatically fail another repository.

Cross-repository equality requires coordinated file and manifest updates in
every repository that adopted the files. Deliberate differences also require
the drift records described below. The local manifest check does not enforce
either coordination or those records.

## Three categories

| Category | Example | What it requires |
|---|---|---|
| Expected to differ | settings files, CODEOWNERS, CI workflows, a repo's own checkers | Record it locally. No issue. |
| Not adopted | a repository that took the branch gate and not the identity gate | Record it locally. No issue. |
| True drift | the same adopted file differs between repositories | Record it and open an `abuzucom/agents` issue. |

Only true drift carries information this template cannot get another way. A
file the adopter never took, or a settings file that names that repository's
own hooks, tells the template nothing it should act on.

A not-adopted file can produce a difference in an adopted file. Record the
cause next to the effect.

## Who owns which field

| File | Repository | Owns |
|---|---|---|
| `DRIFT.md` | `abuzucom/agents` | This policy. |
| `adopters/<repo>.md` | `abuzucom/agents` | The adopted-at commit and what that repository took versus declined. |
| `docs/template-drift.md` | the adopting repository | What differs locally and why. |

Do not restate a field outside the file that owns it. Cross-reference another
record when it has a stable location.

## The shared-file manifest

`SHARED_FILES` in `scripts/sync.py` lists files that must retain the same
line-ending-normalized content. It includes `hooks/_gate_core.py`, both shell gates,
`hooks/require_consent.py`, `tests/gate_corpus.py`, and both shell gate suites.

After changing one, coordinate the file update across every repository holding
it. Run `scripts/sync.py --write-shared` in each repository and commit each
local manifest. Update the required drift records for deliberate differences.
Line endings are normalized before hashing, so a Windows checkout does not
report every file as drift.

Generic exclusions include repository-specific settings, CI, CODEOWNERS,
repository-owned checks, declined files, and coverage baselines for suites that
differ. Record any adopted file excluded because of local changes as true drift
in the adopter record and the adopting repository's drift record.

## Opening a drift issue

For true drift, open an issue in `abuzucom/agents`. Name the file, describe the
change and its reason, link the local drift record, and state whether you
recommend upstreaming it. The template maintainer adopts or declines it, then
closes the issue.

## Adopters

- [`1a2n-web-visualizer`](adopters/1a2n-web-visualizer.md)
