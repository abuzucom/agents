# Gate internals

This file describes how the repository gates, checkers, and installers
work. The assembled agent policy does not include it. The imperative notes
below address hook authors, client configuration, and repository owners.
No agent rule lives here. Agent rules live in `AGENTS.md` and
`docs/agent-policy/`. A conflict resolves in favor of the policy.

## Threat model
Repository hooks provide defense in depth. They remain reviewable and
disableable. A repository writer can alter hooks and `.claude/settings.json`.
Tamper resistance requires an external harness, filesystem isolation, or
server-side controls.

The gates read command shape. They lack telemetry on event streams, rates,
volume, and login correlation.

Shell gates allow repeated `scripts/trusted_gh.py` calls and route
`-c agents.githubFallback=confirmed` commands to consent without cross-process
state. Repository hooks cannot force a tool call when a model refuses in prose.

The Claude file tool gate also denies protected file operations and broad
searches.

## Client lifecycle
Keep client output within the client limit.

Claude loads `CLAUDE.md` natively. Built-in Explore and Plan agents skip that
file. Preserve both agents. Inject numbered chunks through `SubagentStart`.

Codex loads `AGENTS.md` natively. Set `project_doc_max_bytes` above the
canonical limit. Set `additionalContextLimit` to zero when supported.

Gemini uses `SessionStart` and `BeforeModel`. Gemini project hooks require
fingerprint trust and permit disablement.

Antigravity uses an ephemeral `PreInvocation` message. Its `PreToolUse`
payload must match its schema. Do not emit unsupported `injectSteps` fields
from `PreToolUse`.

The reinjection hook states external hook precedence on every lifecycle
event.

Claude Code, Codex, and Gemini pass `session_id` to hooks. Their
`SessionStart` creates `.scratch/<id>/` and `.worktrees/<id>/`. Codex has
no native consent prompt. Its zone deletes still deny. Antigravity
passes no session id. The zone helper stays denied there.

Claude Code hooks check the `AskUserQuestion` shape. A Stop hook flags prose
choices as advice. Other clients expose neither to hooks.

## Cloud sessions
A setup script running `pre-commit install --hook-type pre-push` restores the
pre-push check. Start each cloud session inside one repository. Its hooks
then load natively.

## Compaction events
Claude and Codex report compaction through the session payload `source`
field. The reinjection hook prepends a compaction directive to policy
context for those events.

Claude and Codex deliver policy through hook context. Gemini prepends a
system message. Antigravity uses an ephemeral message.

Gemini and Antigravity expose no compaction event to repository hooks. No
repository hook can verify disclosure, the stop, plan mode, or continuation
claims. An external harness must enforce them.

## Adoption transaction
`hooks/enforce_gate_adoption.py` calls `scripts/check_gate_adoption.py` before
ordinary work on Claude Code, Codex, Gemini, and Antigravity. The hook permits
only questions, fixed verification, read-only discovery, writes below
`.gate-staging/`, and a staged transaction when the check fails. Staging writes
must resolve below that directory. The installer verifies the staged candidate
before writing. It replaces every other artifact first. It replaces client
registrations last. An interrupted installation remains recoverable through
the same bounded command. A copy failure restores every prior target before
the installer returns failure.

Antigravity recovery accepts `view_file`, `list_dir`, `find_by_name`, and
`grep_search`. It accepts `write_to_file` and `replace_file_content` only when
`TargetFile` resolves below `.gate-staging/`.
`scripts/check_hook_launchers.py` launches the transaction hook through every
configured launcher. `scripts/check_hook_coverage.py` requires test reachability.

## Adoption layout
Create `docs/project-orientation.md` for the adopter's own commands, protected
paths, architecture, entry points, and operational notes. Keep source repository
facts out of that file. The synchronization and reinjection tools append it to
the policy copies and adoptable output.

The source repository may provide
`docs/agent-policy/source-orientation.md`. Its content must use the
`source orientation:start` and `source orientation:end` markers. Content between those
markers reaches local policy copies but never adoptable output. An adopter may
lack that marked content. Missing adopter orientation content fails closed.

Supporting files must remain regular files within the repository. Keep them
ASCII and below the policy size limit. Synchronization rejects missing,
oversized, non-ASCII, or escaping supporting files.

The source repository uses `scripts/sync.py` for copies and digests of shared
files. `scripts/check_*.py` supplies portable checks. `hooks/` supplies
client enforcement. `tests/` covers checks, hooks, distribution, and wiring.
Client settings live under `.agents/`, `.claude/`, `.codex/`, and `.gemini/`.
Preserve checker flags, hook payloads, reusable workflows, and copied policy
files.

The `gate-adoption` skill holds the template upgrade merge order and the
source publishing tooling rule.

## Gate integrity CI
`gate-integrity.yml` uses read-only `pull_request` execution and checks out the
exact base and head revisions. The job executes no pull request code. Without a
base checker, the job requires the label. It runs the base branch copy of
`scripts/check_gate_pr_integrity.py` against the pull request diff. The same
job runs the base copy of `scripts/check_pr_base.py`. It fails a base outside
the stable branches. Configure GitHub branch protection to require this job.
Repository files cannot enforce the branch rule.

## Windows test environment
Hooks must not label execution as elevated without a client runtime approval
result. Missing or contradictory approval metadata fails closed. Repository
hooks cannot inspect client prose when the client API hides it. An external
harness must enforce those claims.

## Checker scope
`scripts/check_banned_agents.py` checks commit authors, committers,
`Co-authored-by` trailers, `Assisted-by` trailers, pull request descriptions,
and pull request authors against blanket vendor denylists, specific models,
and wildcard patterns. The checker cannot identify hidden agent use under a
human identity. Platform controls apply separately.

The local identifier check has limits. Only the trusted CI scan blocks. CI
sees only profile paths. Accounts with placeholder names, double encoding, and
homoglyphs pass.

## Prose checkers
`scripts/check_us_spelling.py`, `scripts/check_english_only.py`,
`scripts/check_hedging.py`, and `scripts/check_pull_request_message.py`
stay advisory for human prose. `scripts/check_agent_prose_gate.py`
fails on the same findings for commits or pull requests that disclose
agent authorship through the Rule 14 `Assisted-by`/`Co-authored-by`
trailer (`check_commit_attribution.py::has_agent_label`) or a matching
pull request description line. Undisclosed agent authorship stays
invisible to this signal. `check_banned_agents.py` shares that gap. The
`pr-checks` job in `agents-compliance.yml` runs this gate. No repository
hook runs it.

In `scripts/prose_bans.txt`, each nonempty policy line defines one exact word
or phrase. Section headers define scope. Add entries without changing checker
logic. The denylist source receives the sole exemption from scanning itself. The
handoff exemption section skips matches only for `plan/HANDOFF.md.example`.

`check_us_spelling.py` flags British variants such as `-our`,
`-ise`/`-isation`, `-re`, and doubled consonants before a suffix.

`scripts/check_hedging.py` reports voice, sentence, discourse, escape sequence,
and vocabulary findings as warnings.
`scripts/check_hedging.py` prose findings always return exit code 0. Unreadable
policy data and unsafe metadata return exit code 1. Pattern checks provide
advisory coverage. Human review covers semantic paraphrases and complex
grammar.

## Trusted wrapper
The wrapper resolves `gh` outside the repository and verifies the authenticated
account through a fixed account request. Direct `gh` lookup remains denied
because shell lookup can select an executable inside the repository.

Commands bound to a repository receive a validated `--repo OWNER/REPOSITORY`
target. The wrapper resolves `origin` from the local checkout or worktree
metadata. The wrapper fails closed when that context is missing or unsafe. The
wrapper keeps `gh` execution in an external safe directory.

PR creation also receives a validated `--head OWNER:BRANCH` target
when no head option exists. Global options may precede the GitHub command.

The transport CLI rejects arbitrary Git options, shell expansion, and paths
outside the current workspace. Git receives only an allowlisted environment.

For comment posts the wrapper opens the draft once through a descriptor that
follows no link and reads only that descriptor. It sends the validated bytes
to `gh` on standard input. A later change or link swap cannot alter the posted
body.

## Pull request base
CI workflows run on every pull request base. Gate integrity runs the base
branch copy of `scripts/check_pr_base.py`. It fails a base outside the
stable branches. `forge_verdict` in
`hooks/_gate_core.py` denies `gh pr create` and `gh pr edit` with any other
`--base` or `-B` value. It reads `hooks/primary-branch.txt` and fails
closed on an unusable file. Coverage:
- `scripts/trusted_gh.py` runs the check on every call in every client.
  It exits 2. A `pr create` without a base gets `--base <primary>`, since
  gh otherwise targets the GitHub default branch.
- The Bash, PowerShell, and CMD gates run it for each client that
  registers them.
- `hooks/enforce_pr_base.py` checks the `base` of GitHub MCP
  `create_pull_request` and `update_pull_request` calls in Claude Code.
  Other clients expose no MCP tool calls to repository hooks.

## Checkout credentials
The default `true` writes `GITHUB_TOKEN` to the runner Git configuration. Any
later step or third-party action can read it.

## Policy loader
The loader rejects missing, malformed, non-ASCII, oversized, symlinked, and
special files. It rejects absolute paths and paths that escape the policy root.
It assembles deterministic output and fails closed.
