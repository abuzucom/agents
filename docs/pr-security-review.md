# Pull request security review

This repository calls the `abuzucom/agents-personas` foucault security
review. The `docs/` and `reviewers/foucault/` directories of agents-personas
own the architecture and the trust boundary. This document records only the
local wiring.

## What runs

`.github/workflows/security-review-pr.yml` triggers on completion of the
`Immutable Compliance` workflow, resolves the pull request from the workflow
run head, and calls the agents-personas `foucault-security-review.yml`
wrapper. The wrapper loads the engine, the foucault prompt, and the model
adapter from the pinned revision. It builds the review case without the
provider key, sends each envelope to the configured provider, posts a fenced
report, and publishes a `foucault / security` check run.

`.github/workflows/quality-review-pr.yml` calls the
`euler-quality-review.yml` wrapper at the same revision after
`Convention Sync Check` and `Immutable Compliance` both pass. It publishes a
`euler / quality` check run.

Both callers pin the reusable workflow and `personas_ref` to agents-personas
commit `c43f4592191b42b9f66072622b082fc2f4dc3217`, version 0.22.0. Keeping one
revision for both means the policy and its runner never diverge. Change the
pin only on purpose. Record the change in `CHANGELOG.md`.

This repository vendors no adapter or response validator. The engine
supplies both from the pinned revision.

Both callers set `fail_on_block: true`. A `BLOCK` verdict therefore fails the
check. A `NEEDS-HUMAN` verdict warns and concludes neutral.

A pull request from a fork receives a skipped check from the engine and no
provider secret.

Each caller skips a head with a GitHub Actions check run that already
carries a `VERDICT:` title. A run that ends before a verdict carries another
title. The next event for that head then retries the review.

The `workflow_run` trigger keeps the caller on default branch code. The
review does not appear on a pull request's own checks list until GitHub
finishes the upstream run for that head and the caller starts. Find the
`security-review-pr` run under the default branch in the Actions tab.
`workflow_run` runs do not appear on the pull request branch.

A `v*` tag push starts no foucault or euler review. Every tagged commit
passed both reviews on its way to `main`.

## Required repository secret

The review stays idle until an active human adds the provider API key as a
repository secret. No agent sets it, and no agent commits it.

The active profile in the pinned `engine/model_providers.json` selects the
provider. The callers
map `secrets.OLLAMA_API_KEY` to the reusable workflow's `MODEL_API_KEY`.

Add it under Settings, Secrets and variables, Actions, as `OLLAMA_API_KEY`.

Until the secret exists, the `foucault / security` and `euler / quality`
checks fail. That failure reflects the absent secret. It reports no
finding against the diff.

To use another provider, change the secret name in each caller's `secrets`
block and pass a `model_call_command` adapter that the agents-personas
documentation describes.

## Required checks

Branch protection that required the `security-review` or `quality-review`
check needs the `foucault / security` and `euler / quality` names. Repository
files cannot change branch protection.
