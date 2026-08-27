# Drift

`scripts/sync.py` keeps the AGENTS.md family byte-identical across its eight
tool copies. It covers nothing else. Every file under `scripts/`, `hooks/`, and
`tests/` is copied into an adopting repository by hand and then maintained
there, so a local edit is invisible from here until somebody diffs the two
repositories.

That is not hypothetical. `check_commit_message.py` blocked in one repository
and warned in the other for weeks, and the three checker fixes backported in
1.13.0 were found the same way: by hand, by accident.

This file states the policy. One part of it is mechanical and the rest is not.

`scripts/sync.py --check-shared` compares the files carrying gate decisions
against `shared-files.json`, a manifest of SHA-256 digests committed in every
repository holding them. A file that changes in one repository and not another
fails that repository's check on its next run. It runs in CI.

Everything else here is a convention. Nothing verifies it.

## Three categories

| Category | Example | What it requires |
|---|---|---|
| Expected to differ | settings files, CODEOWNERS, CI workflows, a repo's own checkers | Record it locally. No issue. |
| Not adopted | a repository that took the branch gate and not the identity gate | Record it locally. No issue. |
| True drift | the same file, present in both, modified in one | Record it locally **and** open an issue in `abuzucom/agents`. |

Only true drift carries information this template cannot get another way. A
file the adopter never took, or a settings file that names that repository's
own hooks, tells the template nothing it should act on.

A not-adopted file often produces a difference in a file that *was* adopted.
When an adopter moves an assertion out of a suite it declined and into one it
kept, the kept file is no longer byte-identical, and it reads as true drift
until somebody traces it. Record the cause next to the effect.

## Who owns which field

Three files, split so the record does not become its own drift surface.

| File | Repository | Owns |
|---|---|---|
| `DRIFT.md` | `abuzucom/agents` | This policy. |
| `adopters/<repo>.md` | `abuzucom/agents` | The adopted-at commit and what that repository took versus declined. |
| `docs/template-drift.md` | the adopting repository | What differs locally and why. |

Each links the others. None restates a field it does not own: a value copied
into two files is a value that can disagree with itself, which is the failure
this whole document exists to name.

## The shared-file manifest

`SHARED_FILES` in `scripts/sync.py` lists the files that must stay
byte-identical: `hooks/_gate_core.py`, both shell gates,
`hooks/require_consent.py`, `tests/gate_corpus.py`, and the two shell gate
suites. These carry decisions, and a decision reached by one copy and not
another is the failure this whole design exists to prevent.

After changing one, run `scripts/sync.py --write-shared` and commit the new
manifest in every repository holding those files. Line endings are normalized
before hashing, so a Windows checkout does not report every file as drift.

`tests/test_require_consent.py` is deliberately absent from that list. The
adopting repository moved two wiring assertions into it from a suite it
declined, so the two copies cannot be byte-identical. That is recorded in the
adopter file rather than enforced here, which is what a true-drift entry looks
like once somebody has judged it.

## Opening a drift issue

Name the file, the change, and whether you recommend upstreaming it. The
template maintainer adopts it or declines it; either answer closes the issue.
An issue that says only "these differ" moves the work back to the person who
already did it.

## Adopters

- [`1a2n-web-visualizer`](adopters/1a2n-web-visualizer.md)
