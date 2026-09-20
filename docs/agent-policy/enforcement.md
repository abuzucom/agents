# Enforcement

Repository hooks provide defense in depth. They remain reviewable and
disableable. A repository writer can alter hooks and `.claude/settings.json`.
Tamper resistance requires an external harness, filesystem isolation, or
server-side controls.

The gates read command shape. They lack event-stream, rate, volume, and
login-correlation telemetry.

Adopt every gate with its registrations, shared modules, tests, and checkers.
Missing artifacts indicate incomplete adoption. Complete the adoption and run
the recovery check.

The gates refuse destructive commands, unsafe infrastructure access, direct
GitHub CLI lookup, unsafe GitHub HTTP substitutes, credential-manager access,
browser token recovery, and incomplete policy loading.

The shared command classifier permits only a local, explicitly named
Cloudflare Pages deployment from a dedicated non-hidden output directory named
`build` or `dist`. It rejects repository roots, hidden paths, and protected
credential contents. It denies other Wrangler operations.

The gates route consent-required acts to the active human. Unattended sessions
refuse those acts.

Designed denials, prompts, refusals, opaque-command blocks, and exit code 2 on
missing shared modules are policy outcomes. They are not defects.

Run:

- `python scripts/check_gate_adoption.py`
- `python scripts/check_hook_launchers.py`
- `python scripts/check_hook_coverage.py`
- `python scripts/sync.py --check-shared`
- `python -m unittest tests.test_gate_parity -v`

The checks cover only observed files, commands, clients, and event surfaces.
External controls must enforce controls beyond repository coverage.

## Windows test environment

Use the normal user temporary directory for Windows tests. Do not redirect
`TEMP` or `TMP` into the repository or a worktree. `WinError 5` while a fixture
creates or removes a temporary tree indicates an ACL problem in the temporary
directory. Run the focused test once in an elevated PowerShell session to
confirm the diagnosis. Repair or remove inaccessible stale fixture directories
only with active-human authorization. Do not weaken, skip, or edit tests. Do
not make elevation a routine CI requirement.

Hooks must not label execution as elevated without a client runtime approval
result. Missing or contradictory approval metadata fails closed. Repository
hooks cannot inspect client prose when the client API hides it. An external
harness must enforce those claims.

The complete adoption inventory and recovery procedure cover every hook,
registration, shared module, test, checker, manifest, policy file, and
synchronized copy. A designed-denial defect report includes the exact input,
contradictory policy text, and a reproduction. Report a blocked file, command,
and message. A blocking gate does not authorize another act.

Use a CI job, pre-commit hook, or script for mechanically checkable rules.
State the limitation for rules that require human semantic review.

The destructive gate set includes the Bash, PowerShell, CMD, shared parser,
platform policy, shared gate, and parity-test files. Register Bash, PowerShell,
and available CMD `PreToolUse` matchers. Require matching Git and destructive
verdicts across all shell gates.

`scripts/check_banned_agents.py` checks commit authors, committers,
`Co-authored-by` trailers, `Assisted-by` trailers, pull request descriptions,
and pull request authors against blanket vendor denylists, specific models,
and wildcard patterns. The checker cannot identify hidden agent use under a
human identity. Platform controls apply separately.

## Agent-attributed prose gate

`scripts/check_us_spelling.py`, `scripts/check_english_only.py`,
`scripts/check_hedging.py`, and `scripts/check_pull_request_message.py`
always exit 0. That leniency covers human-authored prose, where the
pattern checks misfire on legitimate writing and semantic review covers
what they miss. It does not relax AGENTS.md's rules for an agent. Those
rules bind every AI system regardless of what CI reports.

`scripts/check_agent_prose_gate.py` runs the same analyzers as the four
checks above and fails on their findings, but only for a pull request that
discloses agent authorship. Attribution reuses
`scripts/check_commit_attribution.py::has_agent_label`, the name-only
`Assisted-by`/`Co-authored-by` trailer AGENTS.md Rule 14 already requires
on agent-assisted commits, checked against every commit in the pull
request, plus a matching disclosure line in the pull request description
alone (`scripts/check_banned_agents.py::_extract_pr_disclosures`). A pull
request with no disclosure anywhere stays exactly as advisory as today:
the gate reads no file and runs no analyzer for it.

**Limitation.** An agent that never adds the required disclosure trailer
is invisible to this signal, the same documented gap
`scripts/check_banned_agents.py` already states for banned-agent
authorship. No mechanical check closes it.

**Anti-bypass constraint.** Removing, editing, or omitting an attribution
trailer specifically to stop this gate from firing, or to evade Rule 14's
disclosure requirement, is a rule violation, not a remediation, on the
same footing as editing a test to make it pass. The only compliant fix for
a prose-gate failure is to fix the flagged prose. The gate's own failure
output states this constraint at the point of failure. Detecting trailer
removal across a force-push is out of scope and mechanically unenforced
here. A single pull-request-range check only sees the current head, not a
prior push's message. This prohibition binds as policy independent of
that mechanical limit, the same way Rule 3 binds without every possible
test edit being mechanically caught.

## Protected files and hook inventory

Modifying hook files or `scripts/banned_models.txt` can never be inferred,
inherited, or grandfathered from prior instructions, plan approvals, handoff
status, or compaction text.

Whenever an agent encounters a need or instruction to modify any file in this
inventory, the agent must immediately stop work, enter plan mode, present the
proposed changes, and obtain fresh active-human approval immediately before
execution.

If the active human does not provide consent, the agent must not work around
it. Work remains stopped until consent is provided affirmatively.

The protected inventory covers:

- Hook implementations:
  `hooks/_bash_parser.py`, `hooks/_cmd_parser.py`, `hooks/_gate_core.py`,
  `hooks/_platform_policy.py`, `hooks/block_destructive_bash.py`,
  `hooks/block_destructive_cmd.py`, `hooks/block_destructive_powershell.py`,
  `hooks/block_infrastructure_access.py`, `hooks/enforce_branch_name.py`,
  `hooks/enforce_git_identity.py`, `hooks/reinject_agents_policy.py`,
  `hooks/require_consent.py`, `hooks/github-command-denylist.txt`, and
  `hooks/claude-code-settings.example.json`.
- Hook configurations:
  `.claude/settings.json`, `.agents/`, `.codex/hooks/`, `.gemini/settings/`, and
  `.git/hooks/`.
- Denylist configuration:
  `scripts/banned_models.txt`.

`AGENTS.md` controls when linked documents conflict with it.

Claude Code's consent hook reads paths. New test files do not prompt. Existing
test edits prompt. A final `ExistingTest = None` assignment can disable a
textual implementation. The Bash gate also protects existing tests reached by
redirects, `tee`, `sed -i`, `cp`, or `mv`.

Adopt the consent hook with `hooks/require_consent.py`, `hooks/_gate_core.py`,
its test, and the `.claude/settings.json` `PreToolUse` registration for
`Edit|Write|MultiEdit|NotebookEdit`. Adopt the matching Bash protection. Do not
adopt one gate without the other.
