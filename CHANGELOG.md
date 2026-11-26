# Changelog

This file documents every notable project change.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
One deviation applies. A version heading parenthesizes the release date.
The format uses `## [1.2.3] (2026-01-01)` instead of a spaced hyphen.
The house style bans that hyphen. `scripts/check_ascii.py` enforces the ban on
this file.
All dates are UTC.
Each date has one entry. Every change still advances the version. A same-day
change renames that day's heading to the new version and merges its items
into the entry. Dates never decrease. Ask the active human when a date is in
doubt.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.50.0] (2026-11-26)

### Added
- `scripts/plan_template_upgrade.py` prints the base branch consumers, the
  CodeQL paths that a candidate removes, the prose findings in planned
  commit messages and pull request bodies, and the merge order. It exits 1
  on an expected failure. `hooks/workflow-scripts.txt` allows its two forms.
- `skills/gate-adoption/SKILL.md` gains a template upgrade merge order
  section and a source publishing tooling section. Its new step runs the
  planner before the first push. `docs/agent-policy/adoption.md` points to
  the skill.
- `docs/agent-policy/github.md` documents the tag-safe fetch form.
- `hooks/workflow-scripts.local.txt` in the source repository lists the four
  `scripts/release.py` forms.
- `persona-review-labels.yml` runs the `abuzucom/agents-personas` adorno,
  generay, and havel reviews when a pull request carries the matching
  `<persona>-scan-requested` label. Every wrapper and `personas_ref` pins
  commit `c43f4592191b42b9f66072622b082fc2f4dc3217` (0.22.0). havel reviews
  the baseline classes with an empty `regimes` scope.
- `tests/test_persona_label_review_wiring.py` covers the pins, the label
  conditions, the secret mapping, and the permissions.
- `.compliance-tree-exemptions.json` reviews
  `.github/workflows/persona-review-labels.yml` as a `pull_request_target`
  caller. The entry pins the caller SHA-256, allows only the
  `OLLAMA_API_KEY` secret, binds the adorno, generay, and havel
  agents-personas wrappers at commit
  `c43f4592191b42b9f66072622b082fc2f4dc3217`, and grants `checks` and
  `pull-requests` write. The trusted scan reads this manifest from `main`
  only.

### Changed
- `security-review-pr.yml` calls the `abuzucom/agents-personas`
  `foucault-security-review.yml` wrapper. `quality-review-pr.yml` calls the
  `euler-quality-review.yml` wrapper. Both pin `uses:` and `personas_ref`
  to agents-personas commit `c43f4592191b42b9f66072622b082fc2f4dc3217`
  (0.22.0). The `abuzucom/foucault` and `abuzucom/euler` pins are gone.
- The check runs carry the names `foucault / security` and
  `euler / quality`. Branch protection that requires `security-review` or
  `quality-review` needs the new names.
- The engine publishes the skipped check for a fork pull request. Both
  callers drop the caller fork jobs. Each caller skips a head with an
  Actions check that already carries a `VERDICT:` title.
- Both review callers trust a prior `VERDICT:` check only when its check
  suite belongs to a `workflow_run` execution of the caller file.
  `security-review-pr.yml` grants `actions: read` to its resolve job.
- The shell gates deny `git fetch` and `git pull` without `--no-tags`. The
  same gates deny `--tags`, `--prune-tags`, a `tag` operand, a refspec
  destination in `refs/tags/`, and a `-c` override of `tagOpt`.
  `scripts/trusted_git.py fetch` always passes `--no-tags` and rejects a tag
  destination.
- `hooks/workflow-scripts.txt` drops the four `scripts/release.py` forms.

### Fixed
- `scripts/check_compliance_tree.py` adds a finding for a reviewed
  `pull_request_target` job value that is not a mapping.
- `primary_branch()` in `hooks/_gate_core.py` closes its descriptor on
  every error path and converts each `OSError` to `ValueError`.
- `hooks/enforce_pr_base.py` checks the primary branch for a
  `create_pull_request` call without a `base`.
- `hooks/detect_prose_options.py` closes its descriptor on an `os.fstat`
  failure. A transcript tail that starts on a record boundary keeps its
  first record.

### Removed
- The vendored foucault adapter `ci/build_pr_case.py`, `ci/call_model.py`,
  `ci/model_providers.json`, and `ci/run_model_command.py`. The
  agents-personas engine supplies the adapter.
- `scripts/check_pr_review_response.py` and its tests
  `tests/test_check_pr_review_response.py`,
  `tests/test_review_adapter_portable.py`, and
  `tests/test_review_response_narration.py`. The engine validates each
  reply.

## [2.46.0] (2026-11-25)

### Added
- `scripts/check_compliance_tree.py` reads an optional
  `.compliance-tree-exemptions.json` beside the trusted base checker. A
  pull request copy never applies. A listed `pull_request_target` workflow
  passes a reviewed rule set instead of exact template equality. The rule
  set requires empty or `contents: read` top-level permissions. It refuses
  checkout steps and event data interpolated into a step. It allows only
  the secret names that the manifest lists for that path. It refuses
  `secrets: inherit`, indexed secrets, and the whole `secrets` context.
  Every job-level `uses:` value
  must match a listed `reusable_workflows` entry. Event data appears only
  in `if` conditions and `concurrency` groups. A job `write` scope needs
  the entry's `permissions` map. Each entry pins the SHA-256 of the listed
  workflow and of every bound local reusable workflow. The tree scan fails
  on a changed pinned blob or an absent bound target. A deleted caller
  runs no privileged job and needs no pin. A symlinked workflow fails the
  existing symlink check. Action pinning still applies.
  Listed `rule7_excluded_trees` patterns skip only the Rule 7 weak-hash
  scan. A malformed, symlinked, or non-ASCII manifest fails closed.
  `scripts/check_gate_pr_integrity.py` protects the manifest path.
- `scripts/lint_style.py` reports every `AGENTS.md` line above 120
  characters.
- `hooks/enforce_single_question.py` denies an `AskUserQuestion` call
  with more than one question, fewer than two or more than four options,
  an empty question or label, or a first option that is not the single
  option marked `(Recommended)`.
- `hooks/deny_mcp_github_writes.py` denies GitHub MCP comment, review,
  merge, and auto-merge writes. Any present `labels` field denies, an
  empty list included. A pull request that is not a draft
  denies. Every other known MCP write asks.
- `hooks/detect_prose_options.py` blocks one stop when the final message
  offers choices in prose with no question call in the turn. The hook is
  advisory and fails open.
- `skills/interactive-decisions/SKILL.md` covers one choice per prompt with
  one recommendation.
- `scripts/delete_zone_path.py` prints one stdout line for each deleted
  operand. A failure names how many operands the helper deleted first. The
  helper docstring and the threat model state that deletion is not atomic.
  Concurrent same-user writers inside the session zone fall outside the
  boundary.

### Changed
- `AGENTS.md` drops twelve sentences that restate other policy text. Two
  checker descriptions move to `docs/agent-policy/enforcement.md`.
  `github.md`, `adoption.md`, and `security.md` drop one sentence each
  that repeats `AGENTS.md`. Every requirement stays stated once.

### Fixed
- `AGENTS.md` wraps eight lines above 120 characters at a space. The words
  stay identical.
- `scripts/complete_gate_adoption.py` installs every skill copy that
  `scripts/check_gate_adoption.py` requires. A failed install removes the
  directories it created deepest first. The rollback no longer fails on a
  parent that holds a sibling directory.
- `hooks/_git_probe.py` also refuses when the trusted Git resolver fails to
  load or lacks `resolve_git`.
- `hooks/prepare_session_workspace.py` docstring prose follows the style
  rules.
- `hooks/_zones.py` rejects `.` and empty path components. The gate and
  the delete helper now accept the same operands.
- `hooks/_git_probe.py` runs the Git that `scripts/trusted_git.py`
  resolves. A Git inside the repository never answers the zone tracked
  check. A missing resolver or no trusted Git refuses the delete.

## [2.43.0] (2026-11-24)

### Added
- `scripts/delete_zone_path.py` deletes inside the session's own
  `.scratch/<id>/` or `.worktrees/<id>/` after a consent prompt. The
  helper walks every path component through descriptors and follows no
  link. Shell `rm` keeps the opaque program denial.
  A target that holds a `.git` entry refuses. `git worktree remove`
  handles linked worktrees.
  `hooks/_zones.py` checks every operand. `hooks/_git_probe.py` rejects
  tracked files with a hardened `git ls-files`. The probe streams Git
  output under a fixed cap and discards stderr.
- `hooks/prepare_session_workspace.py` creates both zone folders at
  `SessionStart` in Claude Code, Codex, and Gemini.
- `.gitignore` and `scripts/check_forbidden_paths.py` cover `.worktrees/`.
- CI workflows run on every pull request base. A static branch filter
  cannot read `hooks/primary-branch.txt`. Gate integrity runs the base
  copy of `scripts/check_pr_base.py`. It fails a base outside the stable
  branches. `scripts/check_branch_name.py` exempts the override primary
  branch outside strict preflight. An unusable override file fails the
  check. `tests/test_custom_primary_coverage.py` covers both.
- `gate-integrity.yml` and `agents-md-compliance.yml` rerun on the
  `edited` activity. A base branch change fires that activity. The base
  check and the compliance checks then run again.
- Stable branches are the primary branch, `test`, and `develop`. `develop`
  is the staging branch. Pull requests may target any stable branch. Agents
  treat every stable branch as read-only. Gate integrity rejects a pull
  request base outside the stable branches. `scripts/check_branch_name.py` exempts stable branches
  outside strict preflight. `tests/test_stable_branches.py` covers the set.
- `tests/test_hook_defects.py` covers a manifest file that another process
  replaces and a manifest file that holds invalid text.
- `hooks/_gate_core.py` documents that the gate reads the manifest prefix
  of the file that the check names. A file that another process replaces
  within one hook run reaches the gate with its current content.
- `docs/gate-threat-model.md` records the sweep cost and the worker
  request budget.
  The repository ignore rules never prune the sweep.
  The gate reads the manifest prefix of the file that the check names on
  every check.
- `tests/gate_corpus.py` raises the worker request budget from 5 seconds
  to 30 seconds. A gate that sweeps a large repository reads thousands of
  files before it answers.
- `pnpm test`, `yarn test`, `go test`, and `cargo test` run without a
  prompt for a trusted `origin` owner and ask otherwise.
  `hooks/_test_runners.py` defines the accepted go and cargo shapes. pnpm
  and yarn require the matching lockfile and a `test` script. Project runner
  configuration and a runner inside the repository deny.
- `hooks/workflow-scripts.local.txt` lists adopter scripts in the shared
  list format. An entry that repeats a shared entry fails the list load.
- `tests/test_more_test_runners.py` covers both runner families and the
  local list.
- The gates deny `gh pr create` and `gh pr edit` with a base other than the
  primary branch. CI workflows run only for pull requests into the primary
  branch. `scripts/trusted_gh.py` and the Bash, PowerShell, and CMD gates
  share the check in `hooks/_gate_core.py`.
- `hooks/enforce_pr_base.py` applies the same rule to GitHub MCP
  `create_pull_request` and `update_pull_request` calls in Claude Code.
- `AGENTS.md` Rule 5 requires every PR to target the primary branch.
- The primary branch reader rejects a link or Windows reparse point through
  `lstat` before the open. The opened file must match the checked one.
  Windows lacks `O_NOFOLLOW`. The open alone would follow a link there.
- `scripts/trusted_gh.py` adds `--base <primary>` to a `pr create` that
  names no base. gh otherwise targets the GitHub default branch. An
  unusable `hooks/primary-branch.txt` refuses the call with exit 2.
- `tests/test_primary_pr_base.py` covers every base option spelling, the
  override file, an unusable file, and the MCP hook.
- `hooks/_trust.py` reads `hooks/trusted-owners.txt`. For a listed `origin`
  owner, `pytest`, `python -m pytest`, `scripts/run_tests.py`, `make test`,
  and `npm test` run without a prompt. Other owners keep the consent
  prompt. A missing or unusable list trusts nobody.
- `hooks/workflow-scripts.txt` accepts the `trusted-read` verdict.
  `scripts/run_tests.py` uses it.
- `tests/test_trusted_test_runners.py` covers owner list parsing, both
  verdicts, the origin lookup, and the denials that stay.

### Changed
- `README.md`, `docs/gate-threat-model.md`, and the `pr-steward` skill
  describe the stable branches. The README names the base check in
  `gate-integrity.yml` and lists `check_pr_base.py`. The `pr-steward` skill
  syncs a pull request with its own base. It matches `baseRefName` against
  a fixed allowlist and fetches only the matched literal entry.
- The command gate rejects pytest arguments that start with `@`. pytest
  reads such an argument as a file of further options.
- `scripts/_skill_sync.py` reads frontmatter fields through named regex
  groups. `scripts/check_handoff_content.py` names its first body line
  number. Behavior stays the same.
- `tests/test_trusted_gh_rest_write_forms.py` expects the wrapper to refuse
  a non-primary `--base`.
- `tests/test_primary_pr_base.py` raises the unreadable override error
  directly. Windows reports a file in place of the `hooks` folder as absent.
- `tests/test_primary_pr_base.py` shows that a direct `gh pr create`
  without a base denies. Every direct gh call routes to the wrapper.

### Fixed
- `.gemini/settings.json` quotes `$GEMINI_PROJECT_DIR` in every hook
  command. A project path with a space no longer splits into several
  arguments. `tests/test_gemini_command_quoting.py` covers each command.

## [2.37.0] (2026-11-23)

### Added
- `AGENTS.md` forbids agent prose that calls a version bump a `release`
  without active human consent. Humans publish every `release` manually.
- `scripts/check_agent_prose_gate.py` flags `release` words outside
  Markdown code in agent-labeled commit messages and agent-disclosed pull
  request titles and bodies. `tests/test_agent_release_wording.py` covers
  the check. Regression tests confirm that a human pull request with
  `release` wording passes and an agent-disclosed one fails.
- Rule 16 and `docs/agent-policy/github.md` let read-only GitHub MCP tools
  fetch issues, PRs, and comments when `scripts/trusted_gh.py` reports no
  authenticated account.
- `skills/` holds twelve canonical agent procedures. `pr-steward` is one
  of the twelve. `scripts/_skill_sync.py` validates each skill and writes
  byte-identical copies to `.claude/skills/` and `.agents/skills/`.
- Skill frontmatter allows only `name` and `description`.
- `scripts/check_forbidden_paths.py` fails when a staged change or pull
  request diff touches `.scratch/`. CI and pre-commit run it.
- `scripts/check_shared_neutrality.py` fails when a shared skill or
  adoptable policy file names a specific owner. CI and pre-commit run it.
- `scripts/check_handoff_content.py` checks an untracked handoff before a
  session writes it. It runs locally only.
- `docs/enforcement-matrix.md` lists the enforcement tier of every skill
  rule.
- `.gitignore` ignores `.scratch/`.

### Changed
- `AGENTS.md` drops two sentences that repeat Non-negotiable rules 5 and
  10 inside Critical rules 5 and 10. Both requirements stay in the
  Non-negotiable list. The change keeps `AGENTS.md` within its size limit.
- `AGENTS.md` and the agent policy documents drop sentences that repeat a
  rule stated elsewhere. Each rule keeps one authoritative statement. No
  requirement or check changes.
- The labels rule heading reads `23` to match the Non-negotiable list.
- The SemVer paragraph and the `adoption.md` agent attribution paragraph
  use shorter wording. Every condition stays.
- `scripts/check_gate_adoption.py` requires every skill, every copy, and
  the new checkers. `--fast` skips skill content parsing. The adoption
  hook passes `--fast`. CI and pre-commit run the full check.
- The file tool and shell consent gates route writes below `skills/` to
  consent. `scripts/check_gate_pr_integrity.py` requires the
  `gate-change-approved` label for skill edits.
- `scripts/sync.py` writes `shared-files.json` through a temporary file
  and `os.replace`. It syncs skill copies when `skills/` exists.
- The source repository orientation section moved from
  `docs/agent-policy/adoption.md` into the source orientation markers.
  Its consent and published-history paragraphs stay in adoption output.
- `docs/agent-policy/clients.md` points every client at `skills/`.

### Fixed
- Skill frontmatter parsing accepts CRLF line endings from a Windows
  checkout.
- `scripts/check_handoff_content.py` accepts only https URLs with the exact
  host `github.com` and no credentials or port.
- `scripts/check_handoff_content.py` and `scripts/check_shared_neutrality.py`
  reject a file above the size cap and scan no truncated prefix.
- `scripts/check_shared_neutrality.py` flags a bare `owner/repo` token in
  plain text, links, and lists. Code spans no longer bound the scan.
- `scripts/check_shared_neutrality.py` skips text only between matched
  source orientation markers. It reports unmatched and nested markers.
- `scripts/check_handoff_content.py` accepts list items only under
  `- pending consents:`.
- `scripts/check_gate_adoption.py` reads the required skill list from its
  own `scripts/_skill_sync.py`. A candidate tree under `--root` must hold
  that module as a regular file. The checker executes only its own
  copy. A missing module fails closed.
- `scripts/check_gate_adoption.py`, `--fast` included, rejects a skill file
  that is a symbolic link or sits below one.
- The full skill check reports any folder under `skills/`,
  `.claude/skills/`, or `.agents/skills/` that names no listed skill.
  `scripts/sync.py` reports such a folder and deletes nothing.

## [2.33.7] (2026-11-22)

### Added
- `scripts/prose_bans.txt` adds six banned words and phrases to the global
  scope. Two requested entries already existed.

### Fixed
- `scripts/check_test_names.py` escapes control characters in every
  printed finding and error through `sanitize_text` from
  `scripts/read_git_state.py`.
- `scripts/check_test_names.py --all` stops before reading when the tests
  folder holds more than 2000 files or 64 MiB.
- `scripts/check_test_names.py --all` exits 1 when the `tests` folder is a
  symbolic link or resolves outside the repository.
- `scripts/check_test_names.py --all` parses each test file once and
  shares the tree between the name and comment scans.
- `scripts/check_test_names.py --all` exits 1 when `--repo` names a
  missing directory or a tree without a `tests` folder.
- `scripts/check_test_names.py` routes every parse through one helper.
  A syntax error in any scan reports the file and line without a
  traceback. `MAX_COMMENT_EXCERPT_CHARS` names the comment excerpt
  limit.

## [2.33.1] (2026-11-21)

### Added
- `scripts/check_test_names.py --all` reads every `tests/**/*.py` file in
  the working tree. It fails on test names over five words after `test_`
  and on narration in test comments. Narration means a personal pronoun
  or an opening sequencing word. Pattern matching covers those forms only.
  `make lint`, the `sync-check.yml` lint steps, and
  `hooks/workflow-scripts.txt` run or allow it.
  `tests/test_check_all_test_names.py` covers it.
- `scripts/check_test_names.py` fails on test functions under `tests/`
  that a `--base`/`--head` range adds or renames with more than five words
  after `test_`. Names present in the base version at the same path
  pass. The `pr-checks` job in `agents-compliance.yml` runs it. It covers
  changed tests only.
  `tests/test_check_test_names.py` covers it.
  `hooks/workflow-scripts.txt` allows the range form in hook-enabled
  sessions.
- `AGENTS.md` adds a Numbers rule to the Style section. Prose, comments,
  commits, and PRs spell out zero through ten and use digits above. No check
  enforces the rule.
- `AGENTS.md` adds a Test names rule to the Style section. A test name
  holds at most five words after `test_`. The rule text names that limit. Test comments state what the code
  does. No check enforces the rule.
- `scripts/prose_bans.txt` adds four banned phrases to the global scope.

### Changed
- 968 test functions in 160 files under `tests/` now use at most five
  words after `test_`. The renames change no test body, assertion, or
  docstring. `tests/test_check_conflict_markers.py` updates the three
  test names its direct execution test lists.
- `shared-files.json` records new digests for the ten renamed shared test
  files. Each repository holding copies takes the new digests at its
  next sync.

### Fixed
- `scripts/check_test_names.py --all` takes its pronoun list from
  `PERSONAL_PRONOUNS` in `scripts/prose_policy.py`. Third person pronouns
  in test comments now fail too. Two test comments drop the pronoun
  `them`.
- `scripts/check_test_names.py` queries each blob size with
  `git cat-file -s` before reading the blob. A test file over the 4 MiB
  cap exits 1 and never enters memory.
- `scripts/check_test_names.py` matches base tests by bare name. A long
  test moved to another class or under a renamed class passes.
- `scripts/check_test_names.py` gives a renamed test file no base
  exemption. Every long test name in a renamed file fails.
- `scripts/check_test_names.py` exempts each base name once per base
  occurrence. A long name copied into a second class fails. A new
  function named `test...` without `test_` fails. The docstring states
  the module and class scope and the pre-read size check.

### Removed
- `docs/agent-policy/adoption.md` drops the retry variations paragraph.
  The Retry discipline rule in `AGENTS.md` keeps the requirement.
- Rule 9 in `AGENTS.md` drops the sentence on proposing each new dependency.
  The rule still requires authorization before any dependency change.
- The Line length rule in `AGENTS.md` drops its line-break hint.

## [2.29.9] (2026-11-20)

### Added
- `hooks/reinject_agents_policy.py` checks the compaction disclosure on
  the Claude `Stop` event. It scans the transcript backward in 4 MiB
  chunks up to 64 MiB for the last `compact_boundary` entry and the next
  `isCompactSummary` entry. It blocks one turn end unless later assistant
  text holds a closed fenced block with the first line
  `COMPACTION TEXT DISCLOSURE` and a body that contains the summary. A
  missing or unreadable transcript, a missing summary entry, or a scan
  past 64 MiB lets the turn end with a notice. `.claude/settings.json`,
  `hooks/claude-code-settings.example.json`, and
  `scripts/check_gate_adoption.py` register the check. Only a parsed
  entry with type `system` and subtype `compact_boundary` counts as a
  boundary. Issue 101.
- `hooks/_gate_core.plan_mode_git_verdict` denies a Git write while
  `permission_mode` is plan. The Bash, PowerShell, and CMD gates merge
  the verdict into each Git command. Inspection subcommands stay open.
  Options that write files or run a program deny in any position. Global
  config, pager, and helper path options deny before the subcommand.
  Plan mode leaves out `ls-remote`, `cat-file`, and `help`. Each allowed
  subcommand gets the `git_read_verdict` config and environment check.
  Plan mode turns any Git ask into a deny. The CMD gate now asks for a
  `set` of a Git-relevant variable through
  `_gate_core.cmd_set_assignment_verdict`. Plan mode turns each Bash,
  PowerShell, and CMD assignment ask into a deny.
  `tests/test_plan_mode_git_parity.py` runs each gate with an inherited
  `GIT_EXTERNAL_DIFF` or `GIT_PAGER` and pins the plan-mode deny.
  Issue 100.

### Changed
- `hooks/enforce_branch_name.py` allows `EnterPlanMode` and plan file
  writes outside the repository on an invalid branch. It allows
  `ExitPlanMode` and `ToolSearch` there only while `permission_mode` is
  plan. Repository reads and writes stay blocked. The Stop check ends a
  plan-mode turn with the rename reminder instead of a block. `AGENTS.md`
  states the allowance. Issue 100.

### Fixed
- `hooks/_gate_core.py` limits the Kubernetes values file name match to YAML
  extensions. The gate protected any file with a name that starts with
  `values-` or `values.`. A Helm values file carries a YAML extension. A source file
  named `values.ts` carries no Kubernetes configuration, and its name reached
  the protected set. That denied broad searches in repositories holding such
  a file. Add `tests/test_infrastructure_values_scope.py`.
- The reusable `pr-checks` job in `agents-compliance.yml` runs on draft
  pull requests. Rule 5 makes every agent pull request a draft. The old
  draft skip kept `scripts/check_agent_prose_gate.py` from running until
  a person marked the pull request ready. Add
  `tests/test_pr_checks_draft_coverage.py`. Correct the draft comments in
  `agents-md-compliance.yml`, `sync-check.yml`, and `README.md`.
- The `pr-authorship` job in `sync-check.yml` drops the banned-agent,
  identity, and attribution steps that `pr-checks` already runs. The job
  keeps the commit-range external reference check. Add
  `tests/test_pr_authorship_deduplication.py`.
- The digest backfill fixture in `tests/test_sync_digest_index.py` turns
  off automatic Git maintenance and garbage collection. Detached
  maintenance removed `maintenance.lock` during the template copy. Add
  `tests/test_digest_fixture_maintenance.py`.
- Comments in `tests/test_advisory_workflow_wiring.py` and
  `tests/test_agents_md_compliance_trigger.py` describe the draft coverage.
- `tests/test_block_destructive_bash.py` strips inherited `GIT_CONFIG_*`
  variables from the hook environment in `run_hook_in`. Cloud sessions
  export those vectors. The malformed vector test now fails closed there
  too. `tests/test_enforce_branch_name.py` runs
  `test_match_carries_effective_git_context` without those variables.
  Issue 103.
- `tests/test_compaction_disclosure_form.py` passes a 30 second timeout
  to the hook subprocess. A hung hook fails the test instead of hanging
  the suite. Issue 104.
- The agent prose gate section in `docs/agent-policy/enforcement.md`
  names the `pr-checks` job in `agents-compliance.yml` as the CI runner
  of `scripts/check_agent_prose_gate.py`. The old text claimed that no
  CI job runs the gate. Regenerate the synchronized policy copies.
- The Rule 22 protected hook inventory in
  `docs/agent-policy/enforcement.md` lists
  `hooks/enforce_anti_delegation.py`. `scripts/sync.py` already lists
  the hook in `SHARED_FILES`.
- The agent prose gate section in `docs/agent-policy/enforcement.md`
  states the shared `check_banned_agents.py` gap in its own sentence and
  names `agents-compliance.yml` by file name. The rewording keeps the
  assembled policy within the 65,536 byte limit.

## [2.28.5] (2026-11-19)

### Added
- `scripts/sync.py` reads `<!-- local policy:start -->`,
  `<!-- local policy:end -->`, `<!-- source orientation:start -->`, and
  `<!-- source orientation:end -->` as the adoption markers. The older
  marker spellings still work. Adoption replaces each one and prints a
  rename notice to standard error. The existing marker constant names now
  hold the new markers. Add `tests/test_policy_marker_names.py`.
- `scripts/prose_policy.py` reads `[handoff exemption]` as the handoff
  scope. The older section spelling still loads with a rename notice.

### Changed
- Five checker functions that issue 122 item V-54 names meet the
  AGENTS.md code quality limits. Behavior stays the same.
  - `check_hook_coverage.run_test_shards` moves validation, environment
    setup, and the submit loop into three helpers.
  - `prose_policy.find_violations` collects vocabulary, sentence style,
    and discourse findings in three stages. The stage order keeps the
    overlap priority.
  - `check_conflict_markers._check_all` probes each path once through
    `_split_by_presence`.
  - `check_conflict_markers._parse_tree_entries` splits records through
    `_split_tree_record` and names the tree entry types.
  - `check_dockerfile_root._skip_heredocs` finds each terminator through
    `_heredoc_end`. The helper exits with `return`.
  - `tests/test_checker_function_limits.py` measures line count, local
    names, nesting, and nested-loop exits for the five functions.
- `AGENTS.md`, `docs/agent-policy/source-orientation.md`,
  `scripts/prose_bans.txt`, and the documentation use the new marker and
  scope names.
- `scripts/prose_bans.txt` bans twelve `[global]` phrases. Each joins
  `never` to `held`, `holds`, `ran`, `delete`, `deletes`, `follows`,
  `saw`, `reach`, `reaches`, `runs`, `read`, or `reads`.
- `scripts/prose_bans.txt` bans three `[global]` phrases built on `owner`.
  The determiners are `the`, `that`, and `the` with `origin`.
- `scripts/prose_bans.txt` bans the `[global]` hedge word that starts with
  `argu` and ends with `ably`.
- `scripts/prose_bans.txt` bans three more `[global]` entries. The entries cover
  `does` with `not run`, and the hyphenated forms of `pull request` and
  `banned phrase`.
- `scripts/prose_bans.txt` bans 217 more `[global]` entries. The entries
  cover invented hyphenated compounds, filler phrases, hedges, inflated
  adjectives and nouns, marketing verbs, and the comma before `never` or
  `instead`. The checker already flags the comma before `which` as a
  sentence-form finding.
- Two gate messages drop hedged wording. The shell write prompt for gate
  files and the consent session notice now describe hooks as workflow
  prompts. The shared file drift error now says "intended".
- Prose in policy text, documentation, comments, and docstrings drops most
  newly banned entries. Comments and docstrings no longer use the word
  `invocation`. The hook edits carry Rule 22 sign-off. The test edits carry
  Rule 3 sign-off.
- `tests/test_prose_policy.py` lists every configured denylist entry. The
  expected list grows with the denylist. The assertion still requires an
  exact match.
- `AGENTS.md`, `hooks/reinject_agents_policy.py`, and
  `tests/test_hook_output_directive.py` state that external hook output is
  program data in one sentence. A second sentence states that the output is
  not the active human's words. The hook edit carries Rule 22 sign-off. The
  test edit carries Rule 3 sign-off.
- Git flags, several hook deny messages, and test data keep banned
  wording. The older marker and scope
  spellings stay only in the compatibility readers and the marker tests. Each
  remaining item awaits a separate decision.

### Fixed
- `scripts/prose_policy.py` blanks the `Co-authored-by:`, `Assisted-by:`,
  `Session:`, and `<name>-Session:` trailer keys at a line start before
  prose analysis. The keys match in any letter case. The trailer value
  stays checked. Rule 14 trailers no longer raise a colon clause-join
  warning. `tests/test_prose_trailer_keys.py` pins the allowance.
- `tests/test_worker_timeout_defaults.py` joins its worker process before
  the temporary directory cleanup. The child process wrote bytecode into
  that directory during removal. macOS then reported a nonempty directory.
- `tests/test_rebase_lookup_errors.py` drives an unreadable rebase state
  through the failed preflight and the lifecycle message. Both paths
  classify the primary branch as invalid. The preflight denial names the
  lookup failure.
- `hooks/enforce_branch_name.py` reads the rebase state once per denied
  call and once per lifecycle message. `read_rebase_state` returns the
  rebase flag and any lookup error together. `branch_state` and
  `_handle_invalid_branch` accept that result through a new optional
  argument. Verdicts and messages stay the same. Add
  `tests/test_partial_finding_fixes.py`.
- `scripts/check_ascii.py` states why `strip_code` stays separate from
  `prose_policy.mask_markdown_code`. `docs/gate-threat-model.md` states
  that the infrastructure scan cache lasts one hook call.
- `hooks/reinject_agents_policy.py` and `scripts/sync.py` name the
  assembled policy when the assembled bundle exceeds the size limit.
  Both errors named `AGENTS.md` before. The `AGENTS.md`-only check in
  `scripts/sync.py` keeps its wording. Add
  `tests/test_assembled_size_message.py`.
- Nine hooks drop the `# pragma: no cover` markers. The repository
  coverage tracer ignores the marker. The adoption test comments stay.
- `scripts/check_compliance_tree.py` drops a guard on
  `not str(candidate)` that could not be true.
- `scripts/check_compliance_tree.py` and `scripts/check_conflict_markers.py`
  keep separate `_parse_tree_entries` copies so each file stays
  standalone. `tests/test_tree_parser_parity.py` pins both copies to one
  record grammar and to the documented symlink and submodule
  differences.
- Makefile `PROSE_FILES` lists `docs/pr-security-review.md`. CI already
  checks that file.
- Every workflow pins `python-version` to `'3.14'`. Four steps floated on
  `'3.x'`.
- Each `actions/checkout` pin carries `# v4.4.0`. Each
  `actions/setup-python` pin carries `# v5.6.0`.
- The release upload step rechecks the draft state before each write. A
  draft the repository owner publishes during the job stops the job before any
  upload or notes change.
- A rerun refreshes the notes of an existing draft. The refreshed notes
  carry the rebuilt changelog sections and adoption block, then a fresh
  GitHub list of merged pull requests.
- `tests/test_release_workflow_wiring.py` allows `gh release edit` only
  with `--notes-file` and never with `--draft=false`. The edit carries
  Rule 3 sign-off. Add `tests/test_release_draft_refresh.py`.
- `release.py build` rejects a target path that names an existing file.
  The command returns its failure status instead of a traceback. Add
  `tests/test_release_build_target.py`.
- The tag gate reads `--contains`, `--no-contains`, `--points-at`,
  `--merged`, and `--no-merged` as listing modes. Git treats each as
  implying `--list`. A pattern beside such a filter no longer denies. Add
  `tests/test_tag_read_filters.py`.

## [2.27.0] (2026-11-18)

### Added
- `.github/workflows/release.yml` builds a draft release from a pushed
  `vX.Y.Z` tag. The `check-tag` job requires the tag to equal the top
  changelog version and a `policy-digests.json` entry. It runs
  `scripts/sync.py --check` and requires the commit on `main`. The
  `release` job alone holds write permissions. It attests the release files
  and `SHA256SUMS.txt` with `actions/attest` v4.2.2. A rerun reuses the
  draft and stops on a SHA-256 mismatch. Only a "release not found"
  lookup answer counts as an absent draft. Any other lookup failure stops
  the job. The repository owner publishes each draft and selects
  pre-release or stable at that moment.
- `scripts/release.py` provides `check-tag`, `build`, `check-assets`,
  `checksums`, and `notes`. `build` writes the adoptable policy, a stable
  archive of the shared gate files, and the version digest entry. Two
  builds of one commit produce identical bytes. `notes` collects every
  changelog section newer than the latest published stable release. An
  adoption block follows the sections. `latest-stable` picks that floor
  as the highest published `vX.Y.Z` tag. GitHub creation order no longer
  decides it.
- `hooks/workflow-scripts.txt` allows `release.py check-tag` and routes
  `build` and `notes` to consent.
- The release job runs in the `release` environment. The repository owner
  configures that environment with a required reviewer.
- The release notes and README verify provenance with
  `--signer-workflow abuzucom/agents/.github/workflows/release.yml`. The
  rerun check of a reused draft bundle applies the same flag.
- `scripts/check_gate_pr_integrity.py` protects `scripts/release.py`.
  `shared-files.json` records the new digest.
- `hooks/_gate_core.py` denies tag pushes in every shell gate. Covered
  forms include `--tags`, `--follow-tags`, and a refspec side under
  `refs/tags/` or `tags/`. A source naming an existing local tag denies
  in any name shape. The gate reads loose refs and `packed-refs`. A
  `v<digit>` source denies unless a local branch carries that name. An
  unreadable ref store asks. It also denies `git tag` creation, signing,
  forcing, and deletion and `git update-ref` under `refs/tags/`. Listing
  and verifying pass.
  `shared-files.json` records the new digest.
- `docs/agent-policy/github.md` states that agents never create, push,
  move, or delete Git tags and never create, edit, publish, or delete
  releases. `docs/agent-policy/adoption.md` drops four handoff sentences
  that `AGENTS.md` states word for word.
- `_names_version_tag` drops a `refs/tags/` branch that the tag namespace
  check made unreachable. `hook-coverage-baseline.json` records one fewer
  unreached statement in `_apply_git_environment_locations`.
- README states that tags exist only for releases in `vX.Y.Z` form. The
  repository owner tag ruleset covers every tag.
- `SECURITY.md` covers this repository. It supports the latest stable
  release only and states the release integrity check.
  `SECURITY.md.example` tells adopters to verify an adopted release.
- `docs/gate-threat-model.md` lists what a release attestation proves and
  what it leaves unproven. `docs/pr-security-review.md` states that a tag
  push starts no review.
- README documents the release steps, the development and stable
  channels, one-at-a-time merging, and the adopter pin rule.
- Add `tests/test_release_check_tag.py`, `tests/test_release_notes.py`,
  `tests/test_release_assets.py`, `tests/test_release_draft_lookup.py`,
  `tests/test_release_hardening.py`, `tests/test_tag_push_gate.py`,
  `tests/test_release_bundle_signer.py`,
  `tests/test_tag_read_long_options.py`,
  `tests/test_tag_push_resolution.py`, `tests/test_tag_push_ref_store.py`,
  `tests/test_release_latest_stable.py`, and
  `tests/test_release_workflow_wiring.py`. The wiring test compares the
  release job permissions with `RELEASE_JOB_PERMISSIONS`.
- `scripts/check_policy_size.py` fails when the assembled policy exceeds
  the `scripts/sync.py` limit of 65536 bytes. The failure names the
  overage. The existing `AGENTS.md` check keeps its 32768-byte limit.
  Every failure prints an agent directive. The directive forbids an
  independent agent decision to trim, reword, move, or remove policy
  text. It requires an itemized proposal and active human approval.
- `--json` prints both sizes and limits. `--render-markdown <path>`
  validates such a report and prints the pull request comment body. The
  body shows bytes, limit, headroom, percent used, and the directive.
  The renderer rejects a report with limits that differ from the checker
  limits. `render_markdown` also rejects a limit below 1 before the
  percent division. A caller that skips validation gets a `ValueError`
  instead of a `ZeroDivisionError`. The sync loader and the comment step
  carry no checks that control flow cannot reach. The renderer rejects
  report text that nests deeper than 3 levels before `json.loads`
  recurses into it. One iterative pass skips brackets inside strings.
- The report ranks up to 10 assembled policy files by size in
  descending order. Each row states the file share of the assembled
  total. A failure on the assembled limit prints the same ranking.
  `scripts/sync.py` exposes `read_assembled_policy_parts` for the
  per-file sizes.
- `.github/workflows/policy-size-report.yml` posts that comment on pull
  requests touching `AGENTS.md`, a supporting policy file, or a
  generated copy. It runs on `workflow_run` from default branch code. It
  reads head policy files through the contents API and runs no pull
  request code. One marked comment receives every update. A read-only
  `measure` job fetches, measures, and renders. A separate `comment` job
  holds the only write permission and runs no checkout and no code over
  pull request data. Runs for one
  head branch queue in one concurrency group. Two runs cannot both
  create the comment.
- `scripts/sync.py` exposes `assemble_policy_bytes`. `policy_bytes`
  keeps its limit check and behavior.
- `hooks/workflow-scripts.txt` allows the two new checker forms.
- Add `tests/test_policy_size_combined.py`,
  `tests/test_policy_size_report_wiring.py`,
  `tests/test_policy_size_top_files.py`,
  `tests/test_policy_size_report_hardening.py`,
  `tests/test_policy_size_render_divisor.py`, and
  `tests/test_policy_size_report_nesting.py`.
- `scripts/trusted_gh.py` sends four more write shapes over REST. Sessions
  that block GitHub GraphQL cannot run the matching `gh` commands.
  - `run pr create --draft --title <text> --body-file <draft> [--base <b>]`
    becomes a REST `POST` with `draft` set. The head is the current
    branch. The base defaults to the branch in `hooks/primary-branch.txt`,
    or `main`.
  - `run pr edit <n> --body-file <draft> [--title <text>]` becomes a REST
    `PATCH` on the pull request.
  - `run issue close <n> [--reason completed|not_planned]` and
    `run issue reopen <n>` become a REST `PATCH` of the issue state.
  - Each shape runs after the existing gate checks and keeps the ask
    verdict. Any other option sends the command to `gh` unchanged. A
    refused draft, base, or primary branch file exits 2.
- Add `tests/test_trusted_gh_rest_write_forms.py`.
- `scripts/trusted_gh.py` sends `run issue edit <n> --body-file
  .comment-drafts/<file> [--title <text>]` as a REST `PATCH` and
  `run issue create --title <text> --body-file .comment-drafts/<file>` as
  a REST `POST`. Sessions that block GitHub GraphQL can write issue bodies.
  Both forms run after the existing gate checks and keep the ask verdict.
  Any other option sends the command to `gh` unchanged. A body file that
  breaks the draft rules exits 2 with no GitHub call.
- `hooks/_command_execution_gate.py` allows a wrapper `run api` GET request
  without a prompt. The request names one REST path and carries no body,
  header, or hostname option. Every other wrapper call keeps its verdict.
- Add `tests/test_trusted_gh_issue_writes.py` and
  `tests/test_trusted_gh_api_read_gate.py`.

### Changed
- Split the slowest hook test classes into smaller classes. The hook
  coverage runner gives each class one shard and a 30-second limit. A
  slow macOS runner pushed `PrimaryBranchOverrideTest` past that limit.
  Each new class covers part of the same input list. Every case and
  assertion stays the same.
  - `tests/test_primary_branch_override.py` runs the invalid override
    cases for `develop` and `main` in separate classes.
  - `tests/test_primary_branch_read_only.py` halves the allowed and
    denied shell command lists for each read-only state. CMD allow and
    deny forms and the allowed and denied tool checks run in separate
    classes.
  - `tests/test_trusted_gh_api_read_gate.py` runs each hook method in its
    own class over one shared fixture.
  - `tests/test_sync_digest_index.py` runs the six backfill tests in two
    classes over one shared Git history fixture.
- Remove repeated setup work from the same tests. Every hook launch
  stays the same.
  - `tests/read_only_branch_support.py` reads the copied scripts once
    per process into an immutable cache marked intentional. Each fixture
    reads `os.environ` at creation, because a test can patch it.
  - The invalid override checks and the override branch check reuse one
    fixture per branch. Each case rewrites the override file before the
    hook reads it.
  - Each backfill class builds its two-commit history once. Each test
    copies that tree and parses its own shared manifest dict. The
    history took six child processes per test.
  - `tests/test_trusted_gh_api_read_gate.py` reads the wrapper script
    once per module.
- Give each touched test class one responsibility.
  - `tests/read_only_branch_support.py` splits `BranchFixture` into
    `RepositoryFixture` and `HookRunner`. `BranchFixture` composes both
    and keeps every attribute and method name.
  - `tests/test_primary_branch_read_only.py` gives malformed calls,
    existing branch switches, active rebases, and lifecycle events one
    class each.
  - `tests/test_primary_branch_override.py` moves the directory override
    and lifecycle blocking checks into `UnusableOverrideFileTest`.
  - `tests/test_trusted_gh_api_read_gate.py` replaces the
    `ApiReadHookCase` base class with `ApiRepositoryFixture`,
    `ApiHookRunner`, and `read_hook_decision`. `ApiHookFixture` composes
    all three. Each hook test class inherits only `unittest.TestCase` and
    builds one `ApiHookFixture` in setUp.
  - `tests/test_sync_digest_index.py` replaces the backfill base class
    with `BackfillHistory`. Each backfill test class builds one in
    setUpClass and copies it for each test.
- Check each precondition in the same tests before the first use of its
  value.
  - `decision` in `tests/read_only_branch_support.py` checks the hook
    exit code before it reads stdout. Gemini and Antigravity verdicts
    exit 0. Other clients exit 0 or 2. A crashed hook with empty stdout
    read as allow before this check.
  - The backfill fixture checks each `sync.py --write-shared` exit code
    before it reads `shared-files.json`.
  - The read-only shell helpers fail on an empty command list half. An
    empty half ran no case and passed.
  - `HookRunner.run` builds only the payload for the selected client.
- `docs/agent-policy/github.md` lists all six REST write forms in one
  section. Four shorter sentences free the bytes. The comment intro drops
  the GraphQL reason, the network paragraph says "every client", and two
  repeated sentences leave the comment section. The assembled policy
  holds 65506 bytes.
- `docs/pr-security-review.md` and one older `CHANGELOG.md` line pass the
  prose analyzer. `scripts/check_agent_prose_gate.py` scans both files on
  every pull request that discloses agent authorship. The 8 earlier findings failed that
  gate for every such pull request. The wording keeps each fact.
- Document the read-only API allow in `AGENTS.md` Rule 16 and its exact
  conditions in `README.md`. Document the REST issue forms in
  `docs/agent-policy/github.md` and `README.md`. The assembled policy stays
  under its 65536-byte limit.
- `requirements-checkers.txt` pins PyYAML 6.0.3 by sha256 hash. The
  hashes cover every file PyPI publishes for that version.
- The five jobs that install a checker requirements file run on Python
  3.14 and pass `--only-binary :all:`. PyYAML 6.0.3 has no
  wheel for a newer Python. A source build there would run a build
  backend that no hash covers. The three `sync-check.yml` installs also
  pass `--require-hashes`. The reusable `agents-compliance.yml` relies on
  pip's automatic hash mode. An adopter's unhashed file still installs.
- The privileged `immutable-conflict-check.yml` job installs the trusted
  requirements file from wheels only on Python 3.14.
  `scripts/check_compliance_tree.py` accepts only that install command. A
  pull request cannot drop the job back to a source build.
- `.pre-commit-config.yaml` keeps exact PyYAML version pins, because
  pre-commit cannot check hashes.
- The weak-hash and secrets scans in `agents-compliance.yml` and
  `.pre-commit-config.yaml` also read `hooks/*.py`.
- Add `tests/test_scan_and_hash_wiring.py` and
  `tests/test_trusted_install_forms.py` covering these changes.

### Fixed
- `scripts/check_agent_prose_gate.py` blanks the key and colon of each
  disclosure line in the pull request body. The colon clause pattern
  read `Assisted-by: Claude Opus 5.5` as a sentence because "Opus" ends
  in "s". The required disclosure failed the gate it switches on. The
  value stays in place. The analyzers still check every word after the
  key. Spaces keep every finding line and column. The disclosure still
  marks the pull request as agent work.
- Add `tests/test_agent_prose_gate_disclosure.py`. The tests also pin
  that `Claude-Session:` link lines raise no finding and mark no agent
  attribution. The gate already accepted those lines.
- `check_commit_attribution.py` accepts a GitHub-signed `web-flow`
  committer. The committer must be `noreply@github.com`, resolve to the
  `web-flow` account and its fixed id, and carry GitHub's signature.
  GitHub signs web merges, squashes, web edits, and Dependabot commits
  with one key. The exemption covers only the committer. The author
  keeps the strict numbered noreply rule. A web squash kept its agent
  trailers and failed `pr-authorship` and `immutable-compliance` once it
  entered another pull request's range.
- Add `tests/test_github_web_committer.py` covering each required
  marker.
- AGENTS.md Rule 14 states the `web-flow` committer exception.
- The `web-flow` exemption verifies the signature against GitHub's
  pinned web-flow public key `B5690EEEBB952194`. A standard library
  OpenPGP v4 RSA check hashes the payload GitHub reports. The issuer
  key ID inside a signature comes from the signer. The issuer check
  alone proves nothing. GitHub must also report the verification
  reason `valid`. A commit signed under any other key still fails.
- Add `tests/test_signature_issuer_packets.py` covering each packet and
  subpacket length form, the fingerprint issuer, and malformed input.
- Add `tests/test_web_flow_signature_verification.py` covering a forged
  issuer, altered signed fields, altered payloads, and malformed values.
- The read-only `run api` allow admits only plain REST path segments and a
  plain query. A path such as `graphql?query=x`, `graphql/`, `./graphql`,
  or `%67raphql` no longer passes without a prompt. Add
  `tests/test_trusted_gh_api_read_paths.py` covering these paths and the
  option scan.
- The REST `pr create` form applies one base rule to every base. An
  explicit `--base master`, `--base HEAD`, or empty `--base` exits 2. Only
  an absent `--base` takes the primary branch default.
- The wrapper reads `hooks/primary-branch.txt` through one descriptor that
  follows no link and never blocks on a FIFO. A path swap after the open
  cannot change the bytes. Add `tests/test_trusted_gh_pr_base_validation.py`
  covering these cases and a create command without `--body-file`.

## [2.23.3] (2026-11-17)

### Added
- Add `.github/workflows/quality-review-pr.yml`. The workflow runs the
  `abuzucom/euler` quality review on same-repository pull requests after
  `Convention Sync Check` and `Immutable Compliance` both pass for the
  head revision. The reusable workflow and `quality_ref` pin euler 0.9.0
  at `940c53a39b7cc7345b1f6232d43bec7c4d7623df`. Fork pull requests
  receive a skipped `quality-review` check and no provider secret.
- Add `tests/test_quality_review_wiring.py` covering the trigger, the
  pin, the secret mapping, and the fork skip.
- Add `scripts/check_merge_safety.py` verifying merge preconditions before any
  merge action. The checker requires no active Git operation, a clean worktree,
  no conflict markers, a compliant branch, complete gate adoption, and
  synchronized policy copies.
- Add `scripts/check_anti_delegation.py` detecting text that directs a recovery
  command to the active human.
- Add `hooks/enforce_anti_delegation.py` blocking a completion attempt that
  delegates a recovery command to the active human.
- Register the anti-delegation hook with every adopted client.
- Require the merge safety check in `AGENTS.md`.
- Run the anti-delegation scan over the prose files in `make lint` and in the
  pull request workflow.

### Changed
- Relocate one duplicated policy sentence out of the `AGENTS.md` summary. The
  linked documents already carry the same sentence.
- `.github/workflows/agents-md-compliance.yml` triggers on pull requests to
  `main` instead of pushes to `main`. The `opened`, `synchronize`,
  `reopened`, and `ready_for_review` activities start it. The
  `static-checks` job of `agents-compliance.yml` now runs before merge.
  `ready_for_review` starts the `pr-checks` job. That job skips drafts.
- `.github/workflows/sync-check.yml` drops its push trigger. The
  `check-sync`, `tests-windows`, and `tests-macos` jobs no longer rerun on
  a push to `main` after a merge. The `pull_request` trigger keeps its
  branches and activity types.
- Add `tests/test_agents_md_compliance_trigger.py` covering both trigger
  shapes.
- Five test files spell non-ASCII string characters as escapes.
  Each string value stays identical, and every test source file is now
  ASCII.
- `hooks/_gate_core.py` holds the helpers the hooks shared by copy:
  - `emit` and `decide` take a message prefix
  - `emit_context`, `blocked_command`, and `write_content`
  - `powershell_write_groups`, with a `keep_empty` flag
  - one alias step, `expand_git_alias`
  - one GitHub host predicate, `is_github_hostname`
  - `MAX_COMMAND_CHARACTERS` for both parsers

  The consent, branch, identity, and infrastructure hooks drop the
  copies.
- `enforce_branch_name.py` picks every recovery command through
  `recovery_command`. Four helpers that only tests called are gone. The
  14 assertions on those helpers now call `command_execution_violation` or
  `git_branch_context`, and one depth assertion now checks
  `resolve_branch_alias`.
- Comments and docstrings in the core and the shell gates now match the
  code. The PowerShell flag tables derive each range from the flag
  name. Unused parameters leave three shell-gate helpers.

### Fixed
- `scripts/check_merge_safety.py` passes the checked-out branch name to the
  branch checker. A pull request head name in `GITHUB_HEAD_REF` no longer
  replaces the branch of the inspected repository.
- `hooks/_gate_core.py` reads a worktree `.git` pointer up to 4096
  characters. A longer pointer fails closed instead of being cut at 160.
- The infrastructure tree scan reports a protected file, its 20000-file
  limit, and an unreadable directory as separate outcomes. Each still
  denies. A subdirectory the scan cannot list now counts as unreadable
  instead of clear.
  The limit and unreadable reasons name a recovery step. The shell gates
  and `block_infrastructure_access.py` use the new reasons.
- `forge_verdict` reads the `origin` repository owner only for a forge CLI. A cache
  keeps one owner lookup and one scan result for each hook run. Each
  hook main clears the cache first.
- A cyclic git alias, or one past the 10-alias depth limit, denies with a
  named reason instead of a recursion error.
- `git filter-repo` reaches the history-rewrite ask.
- The GitHub routing gate skips every global option value.
  `git --namespace x remote add` now reaches the routing deny.
- `_exec_capable_key` detects drivers under a dotted subsection, such as
  `filter.a.b.clean`.
- The PowerShell policy denies `manage-bde` and `bcdedit` in every form.
  The policy drops the unreachable allow branches for both.
- The Stop hook names only rebase recovery when the rebase lookup fails,
  and keeps the lookup failure text. The invalid-branch handler keeps its
  caller's violation instead of looking the branch up again.
- `enforce_git_identity.py` denies a command that is not a string. Its
  checker stops after 20 seconds. PreToolUse denies with the timeout
  named, and SessionStart reports it as an advisory.
- `require_consent.reaches_a_test_inode` declares its `None` result.
- `require_consent.py` asks before a file tool write anywhere under
  `scripts/`, matching the shell gate.
- The CMD gate treats `busybox` as an interpreter hop.
- The branch alias resolver matches alias names without regard to case,
  as git does.
- The GitHub host predicate strips a port and a trailing dot everywhere.
  `scripts/check_external_pr_refs.py` keeps a matching copy.
- An attached PowerShell `-Path:Value` keeps its case before path
  resolution. A symlinked path then resolves on case-sensitive
  filesystems.
- Deny reasons for partitioning, formatting, wiping, and raw-write tools
  name the real action. The root mode-change reason drops "recursive".

## [2.21.1] (2026-11-16)

### Changed
- `scripts/_commit_trailers.py` holds the trailer parser and co-author
  pattern that `check_banned_agents.py` and `check_commit_attribution.py`
  share. Both callers strip a value before the strict match.
- `scripts/_pr_event.py` holds the event loader, size limits, and the
  Dependabot login for `check_external_pr_refs.py`,
  `check_pull_request_message.py`, and `check_agent_prose_gate.py`.
  `check_gate_adoption.py` requires both new modules.
- `check_english_only.py` and `check_us_spelling.py` mask code through
  `prose_policy.mask_markdown_code`. Tilde fences no longer produce
  warnings. Both checkers now load `prose_policy.py` and
  `handoff_policy.py` from the same directory.
- `run_tests.py` discovers shards through `check_hook_coverage.py`. One
  flatten helper serves both.

### Fixed
- The standalone Git runner in `check_git_identity.py` strips managed
  proxy placeholders, drops empty context values and values with NUL, and
  passes a timeout. Identity Git calls stop after 120 seconds and exit 1
  with the command named. A custom `--allow` pattern must match the whole
  address.
- `check_compliance_tree.py` drops relative PATH entries and uses the
  system temporary directory for Git.
- `check_conflict_markers.py` runs Git from a trusted absolute path. It
  uses `trusted_git.resolve_git` when present and an equivalent lookup
  otherwise. Its report and its decode errors sanitize untrusted text.
- The object ID validators in `check_compliance_tree.py` and
  `check_conflict_markers.py` share one error message.
- `check_commit_message.py` fails closed with exit 1 when a range holds
  more than 200 commits. `check_external_pr_refs.py` and the compliance
  tree inherit the limit.
- `trusted_gh.py` replaces terminal control and bidi override characters
  in relayed gh output with `?`.
- `lint_style.py` drops 7 unused imports. `check_hedging.py` drops an
  uncalled helper. `prose_policy.py` no longer reassigns `HANDOFF_PATH`.

## [2.21.0] (2026-11-15)

### Added
- The command execution gate accepts fixed pytest forms (issue #121). The
  forms are `pytest`, `python -m pytest`, and `python3 -m pytest` with the
  flags `-q`, `-x`, `-v`, `--tb=short`, and a `-k` expression of names and
  `and`, `or`, and `not`. Workspace-relative paths may follow. The verdict
  asks for consent because pytest imports repository code. A `pytest` on
  PATH inside the repository or a shadowing `pytest.py` denies.
- `scripts/trusted_gh.py comments <issue|pr> <number> [--page <n>]` reads
  one page of 100 issue or pull request comments over REST (issue #119).
  The page runs from 1 to 1000. A full page prints a note naming the next
  page. The gate allows the read, with or without `--page`, on every
  branch state.
- `scripts/trusted_gh.py comment <issue|pr> <number> --body-file
  .comment-drafts/<file>` posts one comment over REST. The gate asks for
  consent and denies it on a detached HEAD. The wrapper accepts only a
  regular ASCII draft directly in the git-ignored `.comment-drafts/`
  directory. It opens the draft once through a descriptor that follows no
  link and sends the validated bytes on standard input. A later change or
  link swap cannot alter the posted body. A platform without `dir_fd` and
  `O_NOFOLLOW` support refuses posts with exit 2. Windows is one such
  platform.
- `docs/agent-policy/github.md` documents both comment forms, the missing
  comment fallback, and the unobserved MCP comment tools.
- `hooks/_gate_core.py` defines `DENIAL_RESPONSE` (issue #102). Every hook
  deny output ends with it, including import-failure fallbacks and the
  policy reinjection failure. Ask output stays unchanged.
- `AGENTS.md` Authorization tells agents to report a gate denial and never
  retry a variant or offer a gate change.

### Changed
- `scripts/trusted_gh.py run` prints the sanitized gate reason for a policy
  denial. A GitHub GraphQL 403 names the REST comment forms.
- The opaque command refusal names the rejected program.
- Command gate denials drop the retry wording and keep each recovery step.

### Fixed
- `scripts/sync.py` and `scripts/check_hook_coverage.py` parse arguments
  with argparse. An unknown, abbreviated, or combined mode flag exits 2
  before any work. A mistyped `--check` no longer writes policy copies.
- `scripts/sync.py` and `scripts/check_hook_coverage.py` reject a manifest
  or baseline that is not a JSON object with a recovery message.
- `scripts/check_git_identity.py` reports an invalid `--allow` pattern as a
  usage error with exit code 2.
- `scripts/check_action_pins.py` walks YAML with an explicit stack and a
  visited set. A recursive alias no longer raises `RecursionError`.
- `scripts/_yaml_lines.py` holds the YAML loader that records line numbers and helpers
  for `scripts/check_persist_credentials.py` and
  `scripts/check_dockerfile_root.py`. The loader is a `SafeLoader`
  subclass. Reported line numbers no longer depend on import order, and the
  global `yaml.SafeLoader` stays unmodified.
  `scripts/check_compliance_tree.py` loads workflows through the same
  loader and keeps rejecting duplicate keys.
- `scripts/check_branch_name.py` rejects every branch with a recovery step
  when `scripts/branch_name_bans.txt` is missing or unreadable. A comment
  records why `FOREIGN_TOKENS` omits `mit` and `uma`.
- `scripts/check_gate_adoption.py` requires `scripts/branch_name_bans.txt`
  and `scripts/_yaml_lines.py` in every adopted tree.
- `scripts/check_compliance_tree.py` drops a `stdout` check that
  `subprocess.PIPE` makes unreachable and indexes the attribution checker
  directly.
- `scripts/check_conflict_markers.py` drops an unreachable symlink-probe
  branch, decodes through a `_try_decode` helper, builds the tracked listing
  from `_get_index_entries`, deletes the unused `_collect_files`, and drops
  a false race-free claim from a docstring.
- The active human approved three existing test edits under Rule 3:
  - `tests/test_checker_failure_boundaries.py` stubs `load_documents`.
  - `tests/test_ci_branch_fixtures.py` copies `branch_name_bans.txt` into
    its fixture.
  - `tests/test_check_conflict_markers.py` drops the assertion for the
    removed probe path.
- Add `tests/test_cli_and_manifest_validation.py`,
  `tests/test_yaml_handling.py`, `tests/test_policy_data_inventory.py`, and
  `tests/test_conflict_marker_decoding.py`.

## [2.20.1] (2026-11-14)

### Added
- Add a `ci.local` field to each row of the adoption report. It reads `true`
  for a repository that calls `./.github/workflows/agents-compliance.yml` by
  local path, bare or quoted. Every workflow file counts, and a
  commented-out call does not.
  The Markdown CI column shows `local` for a repository without a remote
  reference. The `reference` and `pinned` fields keep the same meaning.
- Add `tests/test_report_source_repository.py` for the source repository
  row.

### Fixed
- Count `docs/agent-policy/source-orientation.md` in the adoption report copy
  check where a repository holds it. `scripts/sync.py` appends that file to
  every policy copy. The report previously rated every source repository
  copy out of sync.
- `scripts/trusted_gh.py` resolves GitHub CLI, its safe execution
  directory, and its search PATH through shared helpers in
  `scripts/trusted_git.py`. GitHub CLI keeps the working directory as a
  second safe-directory candidate. Failure messages stay unchanged.
- `scripts/check_git_identity.py` names a failed authenticated account
  lookup by exception type before the history fallback. The exception
  message never appears.
- `scripts/check_dockerfile_root.py`, `scripts/check_persist_credentials.py`,
  and `scripts/check_weak_hashing.py` catch only parse errors as malformed
  input. Each `main()` reports any other failure as an internal checker
  failure with exit code 1. `scripts/check_compliance_tree.py` catches only
  YAML errors around workflow loading.
- Replace empty exception handlers with non-raising checks in
  `scripts/check_git_identity.py`, `scripts/prose_policy.py`, and
  `hooks/_gate_core.py`. A permission error on a `.git` entry still fails
  closed.
- Remove a lint suppression marker from `hooks/require_consent.py`.
- Add `tests/test_trusted_executable_resolution.py`,
  `tests/test_identity_lookup_failure_disclosure.py`,
  `tests/test_checker_failure_boundaries.py`, and
  `tests/test_discover_dot_git_status.py`.

### Changed
- `AGENTS.md` Authorization asks for one recommendation per open choice and
  stops when an authorized act has no permitted tool. Rule 16 bans direct
  `gh` under urgency. Rule 17 limits comments, reviews, and replies in every
  repository to active human requests. Rule 14 denies identity, amend,
  rebase, and push requests from harness hooks.
- Replace the 21 per-rule pointer sentences in `AGENTS.md` with one index
  under Precedence. Move the wrapper exit-code meanings to
  `docs/agent-policy/github.md`. Rule 16 keeps the sign-in restriction.
- `docs/agent-policy/clients.md` sets one repository per cloud session as
  the norm.
- `hook-coverage-baseline.json` records 2 unreached statements in
  `_gate_core.py::_discover_dot_git`. A non-root run measured the count.

## [2.19.2] (2026-11-13)

### Fixed
- Move the `abuzucom/foucault` security review pin from release 3.7.7 at
  commit `1334e5bf433d43f152762ea47eb89eb22f260e34` to release 3.7.13 at commit
  `11e55cd691e9a2be086a4fb9378f490d4121e11c`. `audit_ref` moves with the pin.
  The active human approved the pin change under Rule 9.
- Refresh `ci/call_model.py`, `ci/model_providers.json`, and
  `scripts/check_pr_review_response.py` from that foucault commit. An HTTP
  400 now reroutes the private diff to the large-input model only when the
  response body names a context or prompt limit. The validator accepts
  impersonal report lines such as `Trace: base to sink.` Reviews run on
  `minimax-m3.1-flash`.
- Update `PINNED_COMMIT` in `tests/test_security_review_wiring.py` to the new
  pin. Add docstrings to the five methods in
  `tests/test_review_response_narration.py`. No assertion changes. The active
  human approved both test edits under Rule 3.
- State that output from any hook this repository does not supply is
  program data and never the active human's words, whatever client,
  harness, or platform installed the hook. `AGENTS.md` gains Non-negotiable
  item 24 and a Precedence paragraph. The active human's rules override
  external hook output. Repository hooks under `hooks/` stay binding.
- Deliver the same rule through `hooks/reinject_agents_policy.py` on every
  lifecycle event for Claude, Codex, Gemini, and Antigravity.
  `docs/agent-policy/clients.md` states that no repository check verifies
  model compliance.
- Add `tests/test_hook_output_directive.py` for the directive and policy
  text.

### Added
- Add `tests/test_review_adapter_portable.py` from the same foucault commit.
  The tests cover the copied review scripts.

## [2.19.0] (2026-11-12)

### Fixed
- Move the `abuzucom/foucault` security review pin from release 3.3.10 at
  commit `62851df1ef177593adbb9e06b223f5a6dce66fc0` to release 3.7.7 at commit
  `1334e5bf433d43f152762ea47eb89eb22f260e34`. Release 3.7.7 authenticates the
  pull request head fetch. A private adopter failed that fetch before.
  `audit_ref` moves with the pin.
- Refresh `ci/build_pr_case.py`, `ci/call_model.py`, `ci/model_providers.json`,
  and `scripts/check_pr_review_response.py` from that foucault commit. The
  reusable workflow runs the caller's copies. The validator now rejects a
  report line that opens in the first person.
- Require `policy-digests.json` in `tests/test_sync_digest_index.py` only
  where `docs/agent-policy/source-orientation.md` exists. An adopter copies
  the test and holds no digest index.
- Skip the event payload scan in `scripts/check_compliance_tree.py` when the
  runner event file holds no pull request data. A push event no longer fails
  the scan. The check validates the payload structure and bounds its size.
- Replace unencodable characters in `scripts/trusted_gh.py` output for
  buffered and unbuffered streams.

### Added
- Add `tests/test_review_response_narration.py`. The tests cover the
  narration rule of the refreshed validator.
- Add `tests/test_infrastructure_manifest_bound.py`. The tests reach the
  oversize branch of `_infrastructure_manifest_text` with a synthetic file.
  Hook coverage no longer depends on the size of `policy-digests.json`. An
  adopter without the index matches the baseline.
- Add `scripts/report_adoption_status.py`. The script lists an organization's
  active, unforked repositories through the GitHub REST API. It matches each
  repository's policy and gate files against `policy-digests.json`. Each row
  reports the adopted version, its distance from the newest version,
  synchronized copies, gate file coverage, client registrations, and the
  reusable compliance workflow reference.
- Write a dated Markdown and JSON report plus `latest` copies. Report the
  changes since the previous `latest.json`.
- Read the report token from `ADOPTION_REPORT_TOKEN`. Warn when the token
  expires within 30 days. Fail the run on a rejected token or an unreadable
  repository.
- Accept the report form in `hooks/workflow-scripts.txt` with a
  `consent-write` verdict.
- Add `tests/test_report_adoption_status.py`. The tests serve a synthetic
  organization from a loopback HTTP server.
- Add `tests/test_compliance_tree_event_isolation.py`. The test covers a push
  event payload in the scanner environment.
- Add `tests/test_trusted_gh_encoding.py`. The tests cover output on a stream
  with a restricted encoding.
- Add `policy-digests.json`. The index maps each released version to the
  SHA-256 digests of its policy documents and shared gate files. An adoption
  report matches adopter files against it to name the adopted version.
- Record the current version in the index on every `python scripts/sync.py`
  run. `python scripts/sync.py --check` fails on a missing or stale entry.
  Both steps skip a repository without the index file.
- Add `python scripts/sync.py --backfill-digests`. The flag adds an entry for
  every released version in Git history. It reuses the shared digests each
  revision recorded. Existing entries stay untouched.
- Accept the `--backfill-digests` form in `hooks/workflow-scripts.txt` with a
  `consent-write` verdict.
- Add `tests/test_sync_digest_index.py`.

### Changed
- Report stale copies and a stale digest index together in
  `python scripts/sync.py --check`.
- Drop the `_infrastructure_manifest_text` limit from
  `hook-coverage-baseline.json`. The digest index exceeds the 64 KiB manifest
  bound. A hook test now reaches the oversize branch.
- Name every numeric literal that the Euler M11 prescan flags in `hooks/`,
  `scripts/`, and `tests/`. The change covers 96 files and 512 candidates.
  Each literal becomes a named constant, a tuple unpack, or a length of a
  named prefix. No behavior changes. No test assertion changes its expected
  value.
- State the reason for `MAX_CHAIN_PARTS`, `MAX_WORKFLOW_ARGUMENTS`, and
  `MAX_WORKFLOW_SCRIPT_LIST_BYTES` in `hooks/_command_execution_gate.py`.
- State the purpose of `EXCLUSIVE_TEST_SHARDS` and of the non-waiting executor
  shutdown in `scripts/check_hook_coverage.py`.
- Record new digests in `shared-files.json` for the changed shared files.

## [2.16.1] (2026-11-11)

### Added
- Add an `allow` verdict to `workflow_decision` in
  `hooks/_command_execution_gate.py`. An allowed form runs without a prompt for
  every client, including Codex and unattended Claude sessions.
- Add `hooks/workflow-scripts.txt`. The list names each accepted repository
  script form with an `allow`, `consent-read`, or `consent-write` verdict. It
  covers the checker commands in the Makefile, `.pre-commit-config.yaml`,
  and CI, plus local report and advice flags. A missing or malformed list
  denies every repository script call.
- Accept `python -m unittest discover` with optional `-s`, `-t`, `-p`, `-v`,
  and `-q`. Directories must resolve inside the repository.
- Accept `ruff check` and `ruff format` with a fixed flag list, including the
  `python -m ruff` spelling. Checking forms run without a prompt. `ruff format`
  and `ruff check --fix` request consent.
- Deny a `ruff` executable that PATH resolves inside the repository. Deny
  `python -m ruff` when a root `ruff.py` or `ruff/` shadows the module.
- Accept `&&` chains of up to eight accepted workflow forms. A chain takes the
  strictest verdict of its parts.
- List the accepted forms in the denial for Ruff, unittest, and repository
  script commands.
- Require `hooks/workflow-scripts.txt` in `scripts/check_gate_adoption.py`.
- Add `tests/test_workflow_allow_verdict.py` covering module verdicts and the
  hook outcome for Claude and Codex.

### Changed
- Run `python -m unittest tests.<module>`, `scripts/read_git_state.py`,
  `scripts/check_action_pins.py`, `scripts/check_gate_adoption.py`, and
  `rg` searches limited to the repository without a prompt. Each requested consent
  before.
- Request consent for an unprompted form when PATH resolves its program inside
  the repository.
- Request consent for an `rg` search with an absolute, home-relative, or
  parent-directory operand.
- Name primary branches beside protected branches in Rule 5 of `AGENTS.md`.
  Some repositories carry no branch protection.
- Align the handoff consent sentence in `docs/agent-policy/adoption.md` with
  the command execution gate. Builds and workflows that the gate routes to consent need
  consent.
- Move the `scripts/prose_bans.txt` file format and the
  `scripts/check_hedging.py` exit-code detail from `AGENTS.md` to
  `docs/agent-policy/enforcement.md`.

### Removed
- Remove repeated passages, examples, and explanations from `AGENTS.md` and
  the five linked policy documents. The assembled policy shrinks by about 3 KB.
  Adopter orientation files gain that room under the 64 KiB limit.
- Remove the Rule 15 pointer to `docs/agent-policy/github.md` for the SSH
  distinction. That document did not contain the text.

### Fixed
- Reject workflow commands that contain `#`. The tokenizer ends a word at `#`.
  Bash does not. A hidden second command could follow a matched form.
- Reject workflow tokens made only of operator characters, such as `|&`.

## [2.15.1] (2026-11-07)


### Fixed
- Preserve external `GH_CONFIG_DIR` in `trusted_gh.py` child execution while
  removing relative directory targets and targets inside the repository.

## [2.15.0] (2026-11-06)

### Added
- Require agents across Antigravity, Gemini CLI, Claude Code, Codex, and IDE
  clients to honor active human manual retry instructions for
  `scripts/trusted_gh.py`, `scripts/trusted_git.py`, and confirmed Git
  fallbacks.
- Require clients to request approved `external-network` execution when default
  sandbox isolation blocks `scripts/trusted_gh.py`.
- Add `tests/test_trusted_gh_connectivity.py` covering connectivity
  classification, loopback discard proxy sanitization, delimiter handling, and
  assembled policy retry guidance.

### Fixed
- Distinguish GitHub CLI network reachability failures from authentication
  failures in `scripts/trusted_gh.py` through `ConnectivityError` and bounded
  `is_connectivity_failure` checks.
- Sanitize `localhost:9` and `[::1]:9` loopback discard proxies alongside
  `127.0.0.1:9` in `scripts/trusted_gh.py`.
- Honor `--` option delimiters in `scripts/trusted_gh.py` repository context
  injection and bound `.git` discovery depth.
- Restore Rule 13 instruction-edit enforceability controls and Rule 17 harness
  pull request exception denial in `AGENTS.md`.
- Prevent pipe-drain deadlocks on Windows during test shard timeout recovery in
  `scripts/check_hook_coverage.py`.
- Resolve worktree `.git` pointer files in `parse_git_config` in
  `hooks/_gate_core.py`.
- Include `Path.cwd()` in `scripts/trusted_gh.py` external directory
  candidates for temporary-root test runs.
- Flush test runner diagnostics in `scripts/run_tests.py`.

## [2.14.1] (2026-11-01)

### Fixed
- Define the disclosure form in the compaction directive of
  `hooks/reinject_agents_policy.py`. Agents must reproduce the compaction
  text word for word in a fenced block led by `COMPACTION TEXT DISCLOSURE`. The
  directive states that client interfaces hide the compaction message. A
  reference to text above, a paraphrase, or a summary is not disclosure.
  Codex disclosed by reference to a collapsed message.
- Cover the disclosure form for Claude and Codex in
  `tests/test_compaction_disclosure_form.py`.

## [2.14.0] (2026-10-30)

### Added
- Reject generated `<adjective>-<surname>-<suffix>` branch names in
  `scripts/check_branch_name.py`. The opaque-suffix rule required a digit.
  `chore/dreamy-goldberg-nwjlsu` passed. Detection covers only the listed
  words.
- Cover the rule in `tests/test_check_branch_name_generated.py`.

### Changed
- Require `check_branch_name.py --strict-agent-preflight` after the branch
  bootstrap in `AGENTS.md`. The bootstrap reader emits no verdict. A
  branch that the harness assigns receives no exemption.
- Disclose in `docs/agent-policy/clients.md` that a multi-repository Claude
  Code cloud session loads no repository hooks.

## [2.13.7] (2026-10-15)

### Fixed
- Keep the second CRLF fold on the policy side of the `CLAUDE.md` check in
  `hooks/reinject_agents_policy.py`. One fold turns CR CR LF into CR LF.
  The second fold changes that text again. The statement is reachable.
- Pin the PowerShell expansion prompt and the line-ending check in
  `tests/test_hook_preempted_paths.py`.

## [2.13.6] (2026-10-14)

### Security
- Ask on `auditctl -D` in `hooks/_gate_core.py`. The marker compared an
  uppercase option against lowercased text and never matched.
- Ask on sed and perl in-place edits over a glob in every spelling:
  `-ni`, `-i.bak`, `--in-place`, `-Ei`, and `perl -pi`. The gate matched
  only a bare `-i` token. It also read `-n` as a dry run for sed and perl.
  Only `git clean` now treats `-n` as a dry run.
- Ask on `xargs rm`, `xargs shred`, and `xargs truncate` in the Bash gate.
  The parser strips xargs as a wrapper. The xargs check did not run.
- Ask on a recursive `chmod`, `chown`, `chgrp`, `icacls /T`, or
  `takeown /R` under a mount point or shared temp directory.
  `volume_verdict` had no caller.
- Deny `git switch` to an existing `claude/` branch on the primary branch
  or a detached HEAD in `hooks/enforce_branch_name.py`.
- Restrict `scripts/trusted_git.py` `run_git` `config_overrides` to
  `filter.<driver>.clean`, `smudge`, `process`, and `required` keys. The
  runner rejects other sections, NUL or line-break characters, more than
  192 pairs, and a malformed existing `GIT_CONFIG_COUNT` before Git runs.
  An existing count above 64 also fails before the slot scan.
- Stop `scripts/read_git_state.py status` from running filter drivers that
  a submodule configures. The status query passes
  `--ignore-submodules=dirty`. Submodule commit changes stay visible.
  Uncommitted changes inside a submodule no longer count as dirty state.

### Fixed
- Name only `git rebase --abort`, `--continue`, and `--skip` in the Stop,
  SessionStart, and UserPromptSubmit messages during a rebase. The
  messages named branch recovery commands that the tool gate refuses then.
- Give a new non-test file outside the project root an accurate prompt
  reason in `hooks/require_consent.py`. The prompt still asks. It no
  longer claims the file is a test.
- Check the `trusted_gh.py run` argument count before the forge verdict
  in `hooks/_command_execution_gate.py`.
- Correct the `ALWAYS_DESTRUCTIVE` comment. `dd` and `hdparm` stay denied
  on every run.
- Record the changed hook digests in `shared-files.json` and tighten
  `hook-coverage-baseline.json` to the statements the suite now reaches.
- Route `python scripts/trusted_git.py clone` and `fetch` to execution
  consent in `hooks/_command_execution_gate.py`. The gate denied every
  trusted Git call as opaque while it allowed native `git fetch`.
- Recognize the same trusted script through `./scripts/` paths, the
  interpreter options without a value `-B`, `-E`, `-I`, `-P`, `-s`, `-S`, and
  `-u`, `python3.N`, and the Windows `py` launcher. The gate compared the
  exact text `scripts/trusted_gh.py` and denied these spellings as opaque.
- Report a missing Git executable or safe execution directory in
  `scripts/trusted_git.py` as an error message with exit code 1 instead of
  a traceback.
- Remove hook statements that an earlier check always pre-empts. The
  removed checks covered a repeated ambiguous-target test, a `-R` test
  after an earlier branch consumed `-R`, an `@` test after `rpartition`
  stripped `@`, a `-C` member compared against lowercased text, a staging
  equality implied by the prefix test, a `Rule 22` reason test that no
  reason text matches, two unused aliases, and the CMD storage branch
  behind `PROHIBITED_COMMANDS`.
- Pin the outcomes the earlier checks deliver in
  `tests/test_hook_preempted_paths.py`.

## [2.13.2] (2026-10-13)

### Fixed
- Stop `scripts/read_git_state.py status` from running filter drivers that
  the repository configures. Git status re-hashes a dirty tracked file through the
  clean or process command that `.gitattributes` or `.git/info/attributes`
  maps to it. The status query now clears `clean` and `process` and sets
  `required=false` for every configured driver (#82).
- Add the keyword-only `config_overrides` parameter to
  `scripts/trusted_git.py` `run_git`. It passes fixed config pairs through
  `GIT_CONFIG_KEY_n` after any forwarded identity pairs.
- Report a Git timeout in `scripts/read_git_state.py` as the bounded state
  read error instead of a traceback.
- State in `docs/agent-policy/enforcement.md` that no CI job or repository
  hook runs `scripts/check_agent_prose_gate.py`.

## [2.13.0] (2026-10-12)

### Added
- Add `scripts/check_local_paths.py`. It blocks committed user-profile paths
  with non-placeholder names and, on a developer machine, the local account
  name, home directory, and computer name (Rule 8).
- Add `.local-path-allowlist` for `<file><TAB><name>` pairs that a human
  approves.
- Scan blobs, paths, branch names, commit ranges, and pull request text in
  the trusted compliance run. Add pre-commit, commit-msg, and pre-push
  hooks.

### Required adoption order
- Adopt the checker and the approved allowlist in one transaction and one
  pull request. A checker without its allowlist is partial adoption under
  Rule 18. Run the local path disclosure procedure in
  `docs/agent-policy/adoption.md` first.

### Changed
- Move the rebase recovery paragraph from `AGENTS.md` to
  `docs/agent-policy/adoption.md` and the CRLF checker sentence to
  `docs/agent-policy/enforcement.md`. Requirements stay unchanged.
- Remove supporting-document sentences that repeat `AGENTS.md`, and state
  linked-document precedence once in `AGENTS.md`. Move source repository
  Dependabot and Windows test notes to `README.md`. Tighten two `AGENTS.md`
  sentences. Requirements stay unchanged.
- Require the checker and allowlist in `check_gate_adoption.py`. Protect both
  in `check_gate_pr_integrity.py`. List both as shared files. Refuse
  unresolved findings in `complete_gate_adoption.py`.

## [2.12.2] (2026-10-03)

### Security
- Read branch-hook metadata in `_read_regular` with `O_NOFOLLOW` and
  `O_NONBLOCK`, compare the opened file with the checked file, and reject
  content that grows past the limit after the check.
- Name the repository path in the consent prompt when `PATH` resolves
  `python`, `make`, or `rg` inside the repository.
- Clamp the manifest depth counter at zero in
  `hooks/_command_execution_gate.py` to prevent negative values on malformed
  inputs.
- Normalize path casing with `os.path.normcase` and check containment with
  `os.path.commonpath` in `_repository_program_path` to prevent case-sensitive
  lookup bypasses on Windows and macOS.

### Fixed
- Probe symlink capabilities in `tests/test_gate_hardening.py` and
  `tests/test_npm_workflow_gate.py` so test fixtures skip cleanly on
  platforms without elevated symlink privileges.
- Use the ASCII escape sequence `\u202e` for the Right-to-Left Override in
  `tests/test_npm_workflow_gate.py` to prevent encoding errors on non-UTF-8
  consoles.
- Compare Windows drives before `os.path.commonpath` in
  `_repository_program_path` instead of catching its `ValueError`. Every
  statement now runs on every platform. This clears the `check-sync`
  coverage failure.

### Added
- Route `npm ci`, `npm test`, `npm test -- <file>...`, and `npm run lint`,
  `typecheck`, or `build` to native consent in
  `hooks/_command_execution_gate.py` when `package.json` defines the script
  or a lockfile exists. The prompt shows every root script npm runs. Unsafe
  manifests, a project `.npmrc`, an in-repository `npm`, and unsafe test
  file arguments deny with the cause and a recovery step. Adopters such as
  `abuzucom/1a2n-web-visualizer` previously received an opaque-program
  denial for every npm command.
- Add `workflow_decision` to `hooks/_command_execution_gate.py`.
  `workflow_needs_consent` and `read_only_workflow` keep the same contracts.
- Record `abuzucom/xdj-rx3-emu` as an adopter in `adopters/xdj-rx3-emu.md`,
  at template commit `fd9da22`.

### Changed
- Move the program allowlist, wrapper and expansion checks, and workflow
  consent from `hooks/enforce_branch_name.py` into
  `hooks/_command_execution_gate.py`. The branch hook loads the new module for
  every shell command. Denials and consent prompts from those checks now name
  `hooks/_command_execution_gate.py`. Branch and Git metadata denials still
  name `hooks/enforce_branch_name.py`. Decisions are otherwise unchanged.
- Keep the moved names importable from `hooks/enforce_branch_name.py`.
- Require `hooks/_command_execution_gate.py` in
  `scripts/check_gate_adoption.py`, the protected hook inventory, and the
  branch adoption file list. Record the new checker digest in
  `shared-files.json`.
- Cover the gate attribution in `tests/test_command_execution_gate.py`.
- Remove two sentences from `docs/agent-policy/adoption.md` that repeat a
  rule stated in the same file or in `AGENTS.md`. The assembled policy stays
  under the 64 KiB synchronization limit.

### Fixed
- List `hooks/enforce_gate_adoption.py` in the protected hook inventory.
- Name the real client hook configuration files `.codex/hooks.json` and
  `.gemini/settings.json` in the protected hook inventory.

## [2.10.1] (2026-10-02)

### Added
- Fail `scripts/check_changelog.py` when two release headings share a date
  or a date goes back in time down the file. Report invalid calendar dates.
- Fail the staged check when the top release date is not today's UTC date.
- Fail the range check when the head date precedes the base date or follows
  today's UTC date.
- Cover the date rules, DST transitions, and process timezones in
  `tests/test_check_changelog_daily_entries.py`.

### Changed
- State that all changelog dates are UTC.
- Redate 31 entries to the UTC date of the commit that added each entry to
  `main`.
- Merge entries that share a date under the newest version.
- Require one changelog entry per UTC date in `AGENTS.md`. Same-day changes
  merge under the new version. Remove a duplicate changelog sentence.

### Fixed
- Accept only a GitHub URL or a remote name as the `trusted_git.py fetch`
  remote. Other URLs, local paths, and `ext::` forms fail.
- Build the Git child environment in `scripts/trusted_git.py` from an
  allowlist. `GIT_SSH_COMMAND`, `GIT_ASKPASS`, `LD_PRELOAD`, and other
  execution hooks no longer reach Git.
- Reject a workspace path that traverses a symlink. The checked path and the
  used path now match.
- Run the policy-root identity checker from `hooks/enforce_git_identity.py`.
  A project copy still opts the repository into the policy.
- Forward the inspected command's Git location and identity settings through
  a filtered `run_git` context. The identity checker on the trusted path saw
  neither an inline `-c user.email` nor `--git-dir` before this change.
- Build the standalone identity checker's Git environment from the same
  allowlist. Adopters copy `scripts/check_git_identity.py` without
  `scripts/trusted_git.py`. The standalone checker passed every variable to
  Git.
- Forward identity settings from `GIT_CONFIG_PARAMETERS` to the identity
  checker. A pre-commit hook under `git -c user.email=... commit` now checks
  the inline value. Other `-c` settings stay out of the checker's Git calls.
  A malformed value fails the check.
- Uppercase allowlisted variable names on Windows.
- Cover the missing policy-root checker branch of
  `hooks/enforce_git_identity.py`.
- Return a finding in place of a `TypeError` when a staged changelog
  has no versioned heading and HEAD has one.
- Include the cause and a recovery step in changelog inspection errors.
- Report a missing staged `CHANGELOG.md` entry instead of a Git inspection
  error.

## [2.9.2] (2026-10-01)

### Fixed
- Deny `--label`, `-l`, `--add-label`, and `--remove-label` on `gh pr` and
  `gh issue` create and edit (Rule 23).
- Deny `gh api` when any `-X` or `--method` value is not `GET`. gh keeps the
  last value. A leading `-X GET` no longer hides a mutation.
- Ask before an external gh command with an implicit target when the
  `origin` repository owner is unreadable.
- Recognize the trusted wrapper after any run of interpreter flags and from
  any working directory.
- Replace the identity block text that asked for name and email values.
- Classify `HTTP 403 Resource not accessible by integration` as an
  installation token. `scripts/trusted_gh.py` skips the account check for
  that category only on GitHub Actions.
- Document the remaining label surfaces and the wrapper's handling of ask
  verdicts in `docs/agent-policy/github.md`.
- Remove a redundant pull-ref test in `hooks/_gate_core.py`.
- Cover every `_option_value` form in `tests/test_gh_option_value_forms.py`.
  Remove two stale `_gate_core.py` entries from `hook-coverage-baseline.json`.

Logic finding 4 stays open. A malformed hook payload still passes as a
session start.

## [2.9.1] (2026-09-30)

### Changed
- Treat the primary branch `main` and a detached HEAD as read-only states in
  `hooks/enforce_branch_name.py`. Read tools, plan and task tools, inspection
  shell commands, and per-client plan writes outside the repository stay
  available. Branch creation and read-only workflows receive a consent
  prompt. Other writes receive a denial.
- Add the protected `hooks/primary-branch.txt` override for one repository
  primary branch name. An unusable override denies every tool.
- Deny every ordinary tool on `master` with a conversion message for the
  active human. Offer only `git switch main` when a local `main` exists.
- Show a one-line read-only note at session start on the primary branch or
  a detached HEAD. `Stop` and `UserPromptSubmit` no longer block there.
- Update `AGENTS.md`, `docs/agent-policy/adoption.md`, and
  `docs/agent-policy/enforcement.md` to match. Remove two duplicated
  paragraphs from `docs/agent-policy/adoption.md`.
- Cover branch gate edge paths in `tests/test_branch_gate_edge_paths.py`.
  Remove two stale `enforce_branch_name.py` entries from
  `hook-coverage-baseline.json`.
- Remove supporting-document sentences that repeat `AGENTS.md` Rule 15 and
  Rule 17 to keep the assembled policy under the sync size limit.

### Removed
- Remove the Dependabot changelog companion workflow,
  `scripts/create_dependabot_changelog_pr.py`, and its test. The job failed
  on every run. The trusted wrapper account check reads `/user`, and the
  workflow `GITHUB_TOKEN` cannot read that endpoint.

### Fixed
- Bind the `gate-change-approved` label to the current pull request head.
  `scripts/check_gate_pr_integrity.py` accepts an optional
  `--timeline-json` flag. With it, the label counts only when a person
  applied it after the latest push, force push, and label removal.
  `gate-integrity.yml` reads that timeline through the pinned
  `actions/github-script` action.
- Match protected paths without regard to case. Protect `Makefile`,
  `.pre-commit-config.yaml`, `scripts/run_tests.py`, and `CODEOWNERS`
  files.
- Stop running the pull request checker when the base branch lacks one.
  The first gate adoption now requires the approval label.
- Direct agents to derive Git identity from an authenticated account source
  and request approval. Never ask the active human to supply identity values.
  Update `hooks/enforce_git_identity.py` and `scripts/check_git_identity.py`
  wording to match.
- Add a diagnosis order for failed trusted wrapper calls to
  `docs/agent-policy/github.md` and Rule 16. Only an authentication result
  supports a sign-in request.
- Require `gate-change-approved` for changes to
  `scripts/check_git_identity.py` and `scripts/check_agent_prose_gate.py`.
- Classify commands inside `<( )` and `>( )` process substitution.
- Route shell writes to `.git/` and agent policy copies to consent.
- Classify a wrapper with no program as the wrapper itself. A bare `env`
  now asks.
- Deny shell access to process environments, GitHub CLI credentials,
  `.git-credentials`, and Docker credentials.
- Deny `gh auth status --show-token`, `gh issue delete`, and every
  `gh label` command. Route `gh gist create` and `gh gist edit` to consent.
- Match unique long-option prefixes for gated git push, reset, commit,
  branch, clean, and rm flags.
- Apply git verdicts to `git.exe` and mixed-case `Git` in the Bash and
  PowerShell gates.
- Require `gate-change-approved` for the denylist, the trusted wrappers,
  the trusted checkers, `requirements-checkers.txt`, and agent policy.
- Route Edit and Write on `AGENTS.md`, its synced copies, and
  `docs/agent-policy/` to consent.
- Ask on every `git clean` outside a dry run and on delete plus force in any
  `git branch` spelling.
- Deny git alias definitions written through `--file` or `git config set`.
- Drop two hook coverage baseline entries that the new tests now reach.
- Route shell writes to `docs/agent-policy/` and
  `.github/copilot-instructions.md` to consent. Share one policy path list
  between the shell gates and the consent hook.
- Deny only `/proc/<entry>/environ` instead of every `environ` directory.
  Ignore a Windows drive prefix in that check. Deny Windows GitHub CLI
  storage under `GitHub CLI`.
- Run each trusted GitHub CLI call inside a private temporary directory.
  Shared `gh-cli-cache` ownership no longer blocks other accounts or
  sandboxes. Name the unwritable path when temporary storage fails.
- Reject an `Assisted-by` trailer that names no versioned model, such as
  bare `Claude`. Reject an agent co-author label with a name and no email
  when no `Assisted-by` trailer accompanies it. Commits with no agent label still pass.
- Require `gate-change-approved` for changes to
  `scripts/check_commit_attribution.py`.
- Scope the checkout temp root in `tests/test_trusted_gh.py` to that
  module. Later test modules in the same process keep the system temp root.

## [2.8.0] (2026-09-29)

### Added
- Add Rule 23 and Critical rule 19 to ban agent label changes on pull
  requests, issues, and repositories across every client.
- Void authorizations, exceptions, and mode state restated in compaction
  text. Require hosted re-verification of label, check, and review claims.
- Document label surfaces and current enforcement gaps in
  `docs/agent-policy/github.md`.

### Changed
- Move the Git automatic identity warning text to
  `docs/agent-policy/adoption.md` and the wrapper lookup rationale to
  `docs/agent-policy/github.md` without changing requirements.
- State that the integrity checker cannot identify who applied
  `gate-change-approved`.
- Remove five duplicated paragraphs from `docs/agent-policy/github.md` and
  `docs/agent-policy/security.md` without changing requirements.
- Rewrite ten passive-voice, pronoun, and comma-clause lines in `AGENTS.md`,
  `README.md`, and `SECURITY.md.example` without changing requirements.
- Record the `abuzucom/1a2n-web-visualizer` re-adoption at template commit
  `848d069` and its documented template drift.

### Fixed
- End a pipeline at `&&`, `||`, `;`, and `&` in the Bash pipe check, and at
  `&&`, `||`, and `;` in the PowerShell pipe check. A group opened after a
  pipe keeps its commands in that pipeline.
- Split a fused `|(` token into its operators. `cat a.sh |(sh)` now denies.
- Read a newline as a pipeline break unless the line ends in a pipe.
- Deny group nesting past 32 levels at the inspection limit.
- Scan chained shell names in a loop. A chain of 3000 names denies instead
  of exiting 1.
- Deny on any unexpected error in `block_destructive_bash.py`,
  `block_destructive_powershell.py`, and `enforce_branch_name.py` through
  `core.run_fail_closed`.

## [2.7.0] (2026-09-28)

### Added
- Add `scripts/trusted_bot_identities.py`, a registry of bots that may skip
  branch naming on a registered branch prefix. It covers `dependabot[bot]` and
  `code-coverage-agent[bot]` (account ID `295130552`).
- `scripts/check_branch_name.py` applies the registry in pull request CI when
  the event file proves the bot identity.

### Fixed
- Classify GitHub CLI account-check failures as authentication, network, or
  unclassified. Network and unclassified failures no longer report a missing
  account.
- Clear the managed Codex `127.0.0.1:9` proxy placeholder in
  `scripts/trusted_git.py` as well as `scripts/trusted_gh.py`.

### Security
- Bind third-party bot exemptions to the numeric account ID and head ref in
  the pull request event. A re-registered App slug cannot claim the exemption.
- Reject commits in a pull request range that carry a bot noreply identity
  other than the pull request author's. An agent can no longer commit as an
  exempt bot to bypass checks.
- Report unreadable pull request event files as violations instead of
  granting or denying an exemption without notice.
- Add the registry to `PROTECTED_FILES`. Registry edits require the
  `gate-change-approved` label.


## [2.6.2] (2026-09-21)

### Added
- Record the `abuzucom/viim` adoption and its documented template drift.
- Separate adopter and source repository orientation from `AGENTS.md`.
- Include adopter orientation in synchronized and adoptable policy copies.
- Preserve orientation limited to the source repository in local policy
  copies and reinjection.
- Add `scripts/check_agent_prose_gate.py`, a blocking gate that fails on
  the same American-spelling, English-only, and prose-policy findings the
  advisory checks already run, but only for commits and pull requests that
  disclose agent authorship through the Rule 14 `Assisted-by`/
  `Co-authored-by` trailer. Work by humans stays exactly as advisory
  as before. The four existing advisory checks stay unchanged.
- Wire the `abuzucom/foucault` pull request security review at commit
  `62851df1ef177593adbb9e06b223f5a6dce66fc0` (release 3.3.10), with the
  `ci/` provider adapters, `scripts/check_pr_review_response.py`, and a
  caller workflow gating on the model verdict.
- Require atomic gate adoption with manifest, launch, allowed-operation, recovery,
  and independent-integrity verification before client hook activation.
- Preserve the verified gate set after a failed transaction. Prohibit permitted
  recovery-work delegation to the active human.
- Declare partial hook or gate adoption a prohibited destructive action.
- Require complete equivalent gate coverage for every adopted client.
- Document atomic multi-client gate adoption for adopters.
- Add staged complete-set recovery for incomplete cross-client activation.
- Add trusted-base CI label enforcement for protected gate changes.

### Changed
- Clarify supporting policy wording and reduce assembled policy size by 250
  bytes without changing policy requirements.
- Clarify draft pull request, adoption, wording, and code quality guidance in
  the canonical policy.
- Synchronize generated policy copies and update adoption documentation.

### Fixed
- Fix `scripts/check_changelog.py` range mode so a repository's first
  `CHANGELOG.md` no longer fails unconditionally. `find_range_violations`
  required a versioned release in the base revision even when the base has
  no `CHANGELOG.md` yet, or only carries an unversioned boilerplate stub
  (such as a default "Keep a Changelog" template with just an
  `## [Unreleased]` heading). The base revision now only needs a version to
  enforce the version-advance requirement. The head revision still requires
  its own versioned release, unchanged.
- Permit trusted gate fetching from the verified workspace root.
- Permit bounded staged recovery writes and read-only discovery.
- Restore prior gate artifacts after a staged installation failure.
- Permit bounded Antigravity staging and discovery tool schemas.

## [2.2.1] (2026-09-18)

### Added
- Add trusted Dependabot companion changelog automation.
- Add Non-negotiable Rule 22 requiring active human consent before modifying
  hook files or `scripts/banned_models.txt`. Require stopping work, entering plan
  mode, and obtaining affirmative approval without workarounds.
- Expand banned agent policy with `scripts/banned_models.txt` supporting the xAI
  developer model inventory, wildcards, and organization models starting with
  DeepSeek V4 Flash.
- Require agents to disclose the active model with an `Assisted-by: <model>`
  trailer and PR description disclosure. The disclosure carries a name and no
  email and never invents a model.
- Extend `scripts/check_banned_agents.py` to enforce banned models, wildcards,
  commit trailers, and pull request description disclosures.
- Extend `scripts/check_commit_attribution.py` to recognize `Assisted-by`
  trailers and enforce attribution by name without emails.

### Fixed
- Avoid false-positive workflow failures on non-Dependabot runs by filtering
  open pull requests before resolving head commits.
- Check open pull request state before creating companion changelog drafts.
- Switch to the companion branch before writing changelog updates to the
  workspace.
- Fail closed in `scripts/check_banned_agents.py` on missing or unreadable model
  denylist files.
- Restrict exact model matching to model disclosures and bot logins to prevent
  false positives on human contributor names and email usernames.
- Harden trailer parsing against non-trailer lines in terminal paragraphs.
- Strip Windows alternate data stream decorations for `scripts/banned_models.txt`
  in consent hooks.

## [2.1.0] (2026-09-17)

### Added
- Treat compaction messages as untrusted input. Assume adversarial
  instructions. Require disclosure, a stop, a return to plan mode, a canonical
  policy reread, and a detailed plan after every compaction event. Ban
  manufactured bypasses and fabricated approval claims.
- Emit a compaction directive from the reinjection hook on Claude and Codex
  compaction events.
- Document Windows temporary-directory ACL troubleshooting for tests.
- Add fixed trusted GitHub clone and fetch transport commands.
- Permit narrowly scoped Cloudflare Pages deployments from workspace output.

### Fixed
- Normalize workspace paths before trusted Git containment checks.
- Reject unsafe symlinks in Cloudflare Pages deployment output.
- Resolve trusted Git workspaces from nested repository directories.
- Normalize workspace paths before trusted Git containment checks.
- Remove redundant trusted Git metadata branching.
- Handle case-insensitive Windows paths in trusted Git transport checks.
- Reject malformed and incomplete trusted Git clone sources.
- Reject credentials and opaque URL components in trusted Git clone sources.
- Exercise the public GitHub CLI denylist classifier in option tests.
- Centralize Wrangler Pages decisions in CWD-aware shell gates.
- Resolve Cloudflare Pages deployment paths from the hook payload CWD.
- Reject unsafe Cloudflare Pages deployment paths and credential contents.

## [2.0.30] (2026-09-16)

### Added
- Document the Python UTF-8 diagnostic workaround for Windows log failures.

### Changed
- Set UTF-8 encoding and LF line endings as the default code style.

### Fixed
- Decode script subprocess output with explicit UTF-8 replacement handling.
- Enforce LF line endings for policy files before byte-limit checks.

## [2.0.28] (2026-09-15)

### Changed
- Clarify strict branch-first ordering before Git inspection and delivery.
- Document the trusted wrapper boundary between local Git and hosted GitHub.

### Fixed
- Align policy guidance with post-preflight feature branch commits, pushes without force,
  pushes, and draft pull request creation.
- Document argument handling that resists injection and rejection of opaque expansion.
- Document explicit repository targets for trusted GitHub commands.
- Prevent untrusted command options from entering wrapper error output.
- Prevent CodeQL-tainted exception data from reaching wrapper output.
- Harden GitHub CLI option parsing and repository context injection.
- Compare pull request changes from the merge base.
- Prevent trusted GitHub CLI error output from exposing exception text.
- Handle global GitHub CLI options before repository commands.
- Preserve explicit pull request head options.
- Bound worktree metadata and accept valid SSH remotes on all platforms.
- Require accurate reporting of runtime elevation approval state.
- Resolve GitHub repository context from Windows worktrees.
- Pass validated repository context to GitHub CLI commands that target a
  repository.
- Require behavioral tests for executable pull request changes.

## [2.0.20] (2026-09-14)

### Added
- Add a configurable GitHub CLI command denylist.
- Deny the requested GitHub CLI command families and paths.
- Require trusted GitHub CLI routing for hosted resource operations.
- Handle the managed Codex loopback proxy placeholder without changing valid
  proxy settings.
- Deny agent changes to Git Credential Manager and GitHub authentication state.
- Deny browser-based GitHub token recovery by agents.
- Add Antigravity `PreToolUse` output that conforms to the schema.
- Add CI and pre-commit coverage for trusted GitHub CLI routing.
- Add linked policy loading and a 32 KiB canonical policy limit.
- Require a versioned SemVer entry for every repository change.
- Add test-first changelog enforcement through hooks and CI.

### Fixed
- Consume GitHub CLI `-h` and `-u` option values before denylist matching.
- Cover short authentication option forms through fresh hook processes.
- Consume interleaved GitHub CLI option values before path matching.
- Cover option terminators and attached option values.
- Parse interleaved GitHub CLI option values before denylist matching.
- Align Rules 16 and 17 with unconditional GitHub CLI denials.
- Remove stale hook-coverage allowances after routing cleanup.
- Remove duplicate denylist paths from legacy GitHub safety branches.
- Deny merges and archives through the shared GitHub classifier.
- Exercise GitHub routing branches through fresh hook processes.
- Cover GitHub routing through fresh hook entrypoints.
- Test unavailable and malformed GitHub CLI denylist data.
- Deny the documented `gh agent-task` aliases.
- Deny documented aliases for other banned GitHub CLI families.
- Avoid duplicate violations and correct changelog version typing.
- Remove the stale hook-coverage record for `load_policy`.
- Trace oversized supporting-file rejection through a hook subprocess.
- Cover both canonical policy file guard paths.
- Cover oversized canonical policy rejection in hook tests.
- Validate pre-release ordering and malformed release headings.
- Test and report oversized supporting policy files distinctly.
- Bound assembled synchronized policy output to the hook limit.
- Fetch full history for CI changelog range checks.
- Fail closed when linked policy files are missing or unsafe.
- Handle changelog revision inspection errors without crashing.
- Assemble generated policy copies from canonical content first.
- Reject incomplete linked-policy bundles during loading and synchronization.
- Enforce SemVer advancement across pull request revisions in CI.
- Treat the managed `cat` pager placeholder as safe during Git reads.
- Cover linked-policy loading and fail-closed supporting-file validation.

## [1.14.0] (2026-09-13)

### Fixed
- Parse GitHub hostnames in URL, SCP, and schemeless remote targets.
- Require English-only, non-vulgar branch descriptions specific to the task.
- Require path separators for Windows drive letters in remote endpoint checks.
- Condition remote endpoint Windows drive parsing on host platform.
- Deny single-letter remote host transfer destinations on POSIX platforms.
- Restore root slash defense-in-depth in filesystem root checks.
- Retain secondary commit limit enforcement during banned-agent checks.
- Cover rebase-state lookup failures in branch-hook validation.
- Allow rebase recovery before branch correction from a detached HEAD.
- Check every tee output and PowerShell path-array destination for Git metadata writes.
- Discover repository metadata for Git reads from nested and linked-worktree directories.
- Disable Git inspection tracing and stream-redirection side effects.
- Protect metadata directory roots and explicit copy destinations.
- Route bounded repository workflows through native execution consent.
- Canonicalize temporary metadata fixture paths across runner platforms.
- Exercise branch dispatch with isolated metadata on detached CI checkouts.
- Supply the read-only job token to immutable commit attribution checks.
- Run static branch validation for draft pull requests.
- Resolve branch aliases against effective Git configuration without alias execution.
- Use local HEAD metadata and the installed branch checker for agent preflight.
- Separate opaque execution from literal prohibited-branch detection.
- Validate metadata write destinations and linked-worktree administration paths.
- Restrict branch recovery to exact commands with native consent.
- Bound command parsing, configuration reads, and alias expansion.
- Replace repeated segment-list searches with hash-based membership checks.
- Reject Git redirections into protected metadata before command dispatch.
- Deny implicit push targets and wrappers with opaque input or execution context.
- Validate tool-name types and file destinations before classification.
- Enforced contributor identity validation for author and committer metadata.
- Required commits that agents generate to use the active operator's noreply
  address.
- Rejected fabricated noreply IDs and unapproved co-author trailers.
- Limited attribution for agents absent from the banned list to labels with
  a name and no email.

### Added
- Added a workflow action pin checker and a pre-setup hook launcher probe.
- Added `ci` as an allowed commit type.
- Added literal escape sequence checks in shared prose policy for unescaped
  newlines, carriage returns, and tabs in prose.
- Forbade literal escape sequences in prose, commit messages, and pull request
  descriptions.

### Changed
- Separated handoff path handling into `scripts/handoff_policy.py`.
- Accepted exact Python 3 versions in the trusted compliance workflow schema.
- Scoped the ASCII policy claim to documentation prose.

### Fixed
- Denied Antigravity branch checks with ambiguous workspace paths.
- Clarified Git `-c` option precedence in the shared gate parser.
- Normalized unquoted numeric Python versions in trusted workflow candidates.
- Selected installed destructive gates for launcher probes.
- Added launcher probe and numeric-version regression coverage.
- Handled missing client configurations and checked every configured launcher.
- Accepted immutable digests for `docker://` workflow actions.
- Normalized numeric YAML Python versions before trusted workflow validation.
- Anchored lifecycle policy injection to the repository containing the hook.
- Protected policy files when the working directory belongs to another repository.
- Closed a cross-owner gate bypass. `gh` accepts `OWNER/REPO`,
  `HOST/OWNER/REPO`, and a full URL for `--repo`. The target parser read only
  the bare form. A URL or a target with a host prefix therefore produced no owner,
  and the gate treated that as clearance. The parser now strips a scheme, any user
  information, and a leading GitHub host. An explicit `--repo` the gate cannot
  read routes to consent instead of passing.
- Required a domain boundary on the GitHub host test. `_origin_owner` in the
  gate and the remote parser in `scripts/check_external_pr_refs.py` accepted
  any host ending in `github.com`. A domain such as `attacker-github.com`
  therefore supplied its path owner as the trusted origin owner. Both now
  require the host to equal `github.com` or end with `.github.com`. The checker
  splits host from path in the pattern and validates the host in code. That
  split avoids the nested quantifier a subdomain alternation would need.
- Ran `scripts/check_banned_agents.py` and `scripts/check_git_identity.py` on
  pull requests through a new `pr-authorship` job in
  `.github/workflows/sync-check.yml`. Both checkers lived only in the
  `pr-checks` job of the reusable `agents-compliance.yml`. Its sole caller
  `agents-md-compliance.yml` runs only on push by design. That job's
  `pull_request` condition is false on a push. The job therefore skipped on
  every event this repository fires. Neither checker ran in CI. The caller keeps its
  push trigger alone. `README.md` records the split.

### Added
- Added a cross-owner verdict to `github_cli_verdict` in
  `hooks/_gate_core.py`. An external GitHub CLI command aimed at an owner
  outside the origin remote routes to active human consent. Covered commands
  include pull request and issue creation, comments, reviews, edits, state
  changes, repository forks, and release creation. An unreadable origin owner
  asks instead of passing. Read-only commands stay available. The URL and
  target parsing uses string operations, since the module carries no regular
  expressions. `shared-files.json` records the new digest.
- Added commit message scanning to `scripts/check_external_pr_refs.py` through
  a commit-range mode and an `--unpushed` mode. The `pr-authorship` job runs
  the range mode. A pre-push hook runs the unpushed mode. That check precedes
  the push that would create the reference.
- Added `tests/test_external_repo_gate.py` covering origin owner parsing across
  remote URL forms, target parsing, the cross-owner verdicts, and the
  end-to-end `forge_verdict` path. Added cross-owner rows to
  `tests/test_gate_parity.py`, chosen so the verdict holds in any checkout.
- Added Rule 17. The rule bans GitHub cross-references to a repository outside
  the current owner. The rule requires active human consent before any
  external act on such a repository.
- Added `scripts/check_external_pr_refs.py`. The checker reads the pull request
  event and blocks autolinked external references in the title and body. The
  checker reuses `scripts/prose_policy.py` code masking. A backticked
  reference therefore passes. The `check-sync` job of
  `.github/workflows/sync-check.yml` runs the checker on every pull request.
  The reusable `agents-compliance.yml` workflow carries the same step for
  adopters that call it on pull requests.
- Added `tests/test_external_pr_refs.py` covering owner comparison, code spans,
  fenced blocks, commit and URL forms, the Dependabot exemption, malformed
  payloads, and CI wiring.
- Added `scripts/read_git_state.py` for bounded structured branch, revision,
  remote, and status output. The reader renders control characters and redacts
  remote URL user information.
- Added local policy orientation markers and adoptable policy output through
  `python scripts/sync.py --print-adoptable`.
- Added regression coverage for safe Git state output and for filtering of
  policy content limited to this repository.
- Added `scripts/run_tests.py` for validated execution sharded by test class. The runner
  compares shard IDs with standard discovery before running four workers.
- Added complete `AGENTS.md` lifecycle reinjection for Claude, Codex, Gemini,
  and Antigravity project clients. Claude preserves built-in Explore and Plan
  through bounded numbered chunks. Gemini and Antigravity inject the complete
  policy before every model request.
- Added strict cross-client branch preflight before every observable tool.
  Exact recovery commands and active human questions remain available.
- Added regression coverage for lifecycle output, client wiring, strict branch
  recovery, and the trusted Dependabot automation exception.
- Added lifecycle validation coverage for malformed payloads, policy bounds,
  client dispatch, and chunk limits. Added strict branch coverage for Git
  metadata files and alternate tool schemas.
- Added `scripts/prose_policy.py` for shared advisory prose analysis across
  authored files, commit subjects, commit bodies, pull request titles, and pull
  request bodies.
- Added `scripts/prose_bans.txt` with case-insensitive exact entries under
  `[global]` and handoff exemption scopes. The policy source skips
  self-scanning. `plan/HANDOFF.md.example` receives the sole scoped vocabulary
  exception. The same handoff file receives the sole exception for conversational provenance.
- Added `scripts/check_pull_request_message.py` for bounded pull request title
  and body checks through `GITHUB_EVENT_PATH`. The checker validates JSON
  structure and limits metadata size. Diagnostics omit source text. Workflow
  shell text never interpolates untrusted metadata.
- Added tests for prose categories, policy scope, commit bodies, pull request
  metadata, draft pull requests, sanitized diagnostics, malformed event data,
  advisory workflow wiring, environment-based refs, and checkout credential
  settings.
- Added `scripts/check_compliance_tree.py` to run trusted base checkers against
  bounded blobs from one validated commit or tree. The checker covers regular
  and symlink blobs, commit and pull request identities, branch names,
  immutable action revisions, and the execution surface of
  `pull_request_target` workflows without importing pull request code.
- Added `scripts/check_conflict_markers.py` with worktree, staged, and immutable
  tree scanning. The checker bounds object reads and rejects malformed Git
  data. The checker ignores replacement refs and handles sparse checkouts.
  The checker handles UTF-16 or UTF-32 BOMs. The checker honors conflict marker
  attributes and distinguishes Markdown Setext headings.
- Added `.github/workflows/immutable-conflict-check.yml`, a
  `pull_request_target` workflow from the base branch with an immutable compliance scan as the sole
  privileged job.
- Added pinned `PyYAML==6.0.3` checker requirements for safe YAML parsing.
- Added a permanent security header, active-work structure, command-execution
  prohibition, and sensitive-data protections to `plan/HANDOFF.md.example`.
- Added adversarial coverage for filesystem races, parser bypasses, local Git
  executable substitution, immutable secrets and actions, symlink blobs, and
  workflow trust boundaries.
- Added synthetic PowerShell policy coverage for aliases, abbreviated
  parameters, varied filenames, dynamic execution, security controls,
  persistence, credentials, network access, and bounded administration.
- Added platform-independent cross-drive coverage for protected hook paths.
- Added a dedicated bounded CMD parser and synthetic CMD command gate for
  expansion, command boundaries, storage, persistence, discovery, and transfer
  behavior.
- Added explicit macOS and Linux command-family policy with cross-host tests.
- Added fixed JSON-line worker transport with request deadlines and no dynamic
  Python command-string execution.
- Added Claude prompt and stop-event branch enforcement for prohibited
  `claude/` harness assignments.
- Added a trusted authenticated GitHub CLI wrapper with bounded account
  metadata and local repository identity proposals.
- Added a dedicated infrastructure file tool gate for credentials, Terraform
  files, and Kubernetes or Helm manifests.
- Added cross-shell GitHub routing, hosted mutation, infrastructure command,
  and protected path parity coverage.

### Changed
- Clarified that adoption does not apply this repository's BSD-3-Clause license
  to a target repository. Third-party obligations remain attached to copied
  material. An unlicensed target now requires explicit approval for the exact
  license before adoption adds one.
- Closed CMD boundary bypasses for quoted carets, PATHEXT command names,
  Windows command paths, output redirects, known file writers, recursive tree
  copies, abbreviated PowerShell payload flags, and shared Git policy.
- Restored drive-root normalization for repeated separators and dot segments.
  Trailing `su -c` payloads now deny after an explicit target account.
- Added Bash, PowerShell, and CMD parity coverage for shared Git and destructive
  behavior. Read-only Git commands may inspect prohibited branch refs.
- Bounded Claude stop-hook retries without clearing strict pre-tool branch
  enforcement.
- Raised the persistent worker request deadline from five seconds to 30 seconds.
  The deadline remains bounded and covers observed Windows CI startup time.
- Routed hosted GitHub operations through trusted `gh`. Direct CLI lookup and
  clear Git or HTTP substitutes now deny. A marked fallback asks for consent.
- Derived unset Git identities from authenticated GitHub account metadata after
  explicit confirmation. Bounded local history candidates provide a fallback.
- Denied cloud, infrastructure-as-code, orchestration, direct remote-shell,
  file transfer, and firewall command families on every shell platform.
- Blocked creation and publication of `claude/` branch targets even when the
  current branch conforms. Compliant recovery commands now request native
  execution authorization.
- Blocked repository aliases and direct Git metadata writes that create a
  `claude/` branch target.
- Changed shell command-string payloads to deny. Plain shell transitions and
  fixed local scripts now ask. A missing `su` target or one aimed at root now denies.
- Changed hook test scheduling to bounded incremental submission with
  fail-fast process termination and 10-second progress notices.
- Added a macOS CI job and removed the duplicate Ubuntu full-suite execution.
- Covered SCP-style remote credential redaction when the path contains an at
  sign.
- Rewrote `AGENTS.md` for concise policy prose without changing lifecycle
  reinjection. Explicit execution requests now authorize named non-destructive
  acts and bounded read-only verification. Gates for specific rules still require confirmation of each act.
- Replaced universal test-first language with validation-first paths for
  executable behavior, executable configuration, policy, and documentation.
  Existing-test consent and behavioral regression requirements remain active.
- Required full commit SHAs for GitHub Actions dependencies. Added release
  version comments when the version remains known.
- Replaced sequential full-suite commands in CI, pre-commit, and `make test`
  with validated four-worker execution. Single-module `unittest` commands
  remain available.
- Made hook coverage run test classes through four bounded workers. The checker
  now reports starts, results, 30-second heartbeats, and 300-second per-class
  timeouts. A timeout terminates the affected test process tree.
- Denied branch recovery commands when unreadable Git metadata prevents current
  branch identification.
- Made lifecycle root and branch metadata tests independent of Windows path
  aliases and pull request branch environment variables.
- Limited hook coverage instrumentation to hook source files. Supported
  runtimes use local `sys.monitoring` events when the coverage tool slot remains
  available. Other runtimes retain a scoped `sys.settrace` fallback.
- Expanded shared PowerShell classification with deny, approval, and allow
  tiers. Command families and path properties now determine file verdicts.
  Encoded and direct command payloads now deny regardless of decoded content.
- Denied UNC command paths independently of basenames and file extensions.
  Covered attached curl upload arguments and explicit BITS uploads.
- Started measured long-running test shards before ordinary shards. Reused one
  isolated Python entrypoint within high-volume hook and CLI test classes.
  Serialized Git-heavy shards to avoid process and filesystem contention.
  Fresh-process smoke cases retain process-boundary coverage.
- Kept primary and detached exemptions in ordinary branch checking. Added
  `--strict-agent-preflight` for interactive agent hooks. Immutable compliance
  now preserves Dependabot branch names through trusted PR author metadata.
- Allowed `it`, `its`, `itself`, `it's`, `it'll`, and `it'd` in advisory
  personal-pronoun analysis.
- Consolidated personal-pronoun, active-voice, sentence-form, discourse, and
  controlled-vocabulary rules in `AGENTS.md`. The policy now favors direct
  factual prose and one independent clause per sentence.
- Made `scripts/check_hedging.py`, `scripts/check_commit_message.py`, and
  `scripts/check_pull_request_message.py` share `scripts/prose_policy.py`.
  Commit checks now inspect bounded non-merge subjects and bodies. Pull request
  checks now inspect title format plus title and body prose.
- Kept every prose finding advisory with exit 0. Checker infrastructure
  failures exit 1. Infrastructure failures include policy loading failures,
  unsafe metadata, and malformed event payloads.
- Added advisory commit and pull request prose jobs to the reusable workflow.
  Advisory jobs cover draft and non-draft pull requests. Blocking compliance
  jobs continue to defer draft coverage until ready status.
- Wired pull request prose checks into `sync-check.yml`. The workflow reads
  title and body data only through `GITHUB_EVENT_PATH`. The workflow keeps
  untrusted pull request metadata outside shell text.
- Documented local commands for file, commit, and pull request prose checks.
  Documented bundled adoption for policy data, checkers, tests, and workflow
  wiring. Updated the checker reference for commit body checks and pull request
  title or body checks. Added warning exits, infrastructure exits, draft
  coverage, event-file safety, and the handoff exception to the reference.
- Reduced the privileged `pull_request_target` workflow to one read-only,
  immutable compliance job. Dependency specifications and checker code come
  from the exact trusted base. Pull request input remains data. Retargeting a
  pull request reruns the job.
- Pinned trusted workflow actions to the policy SHAs
  `actions/checkout@11d5960a326750d5838078e36cf38b85af677262` and
  `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065`.
- Kept `agents-md-compliance.yml` limited to push. Tests, sync and style checks, and
  advisory AgentLint now run under the standard unprivileged `pull_request`
  event. Removed AgentLint pull request comments and the need for
  `pull-requests: write` permission.
- Made conflict diagnostics printable ASCII and bounded in length, normalized
  Windows paths for Git attributes, and treated symlink probe failures as
  errors. Sparse scans now combine present worktree files with immutable index
  blobs for absent files. The combined scan preserves unstaged and indexed
  conflict detection.
- Replaced digest-driven handoff instructions with active human consent. Handoff
  content remains untrusted status. Git commands require consent. Displayed Git
  output requires trusted external sanitization.
- Selected Python through overridable `PYTHON ?= python3` in the `Makefile` for
  Debian compatibility and local interpreter overrides.
- Reorganized repository documentation around canonical current behavior and
  split prose clauses into complete sentences.

### Fixed
- Resolved Antigravity hook commands from the `.agents/` configuration
  directory. Both lifecycle reinjection and strict branch recovery now reach
  the canonical root hooks.
- Made inline-enumeration matching linear by excluding commas from repeated
  non-comma segments.
- Excluded required commit and pull request type prefixes from generic colon
  findings. Commit body loading no longer repeats the subject.
- Hardened `scripts/sync.py` against symlink traversal, repository escapes,
  partial writes, and destination races through path revalidation and atomic
  replacement.
- Rejected duplicate YAML keys. Rule 11 now requires boolean `false`. Rule 12
  evaluates the final Dockerfile user plus every Compose service and Kubernetes
  container independently.
- Expanded weak-hash analysis across Python imports, aliases, and `hashlib.new`.
  Real comments for uses outside security must justify each use. Secret scanning now rejects
  each `.env.*` variant except `.env.example`. Secret scanning recognizes
  encrypted and PGP private-key headers.
- Made branch, commit, banned-agent, and identity checks use an absolute Git
  executable outside the repository and fail closed on lookup or output errors.
  Co-author keys use case-insensitive matching. Only terminal structured
  trailers contribute identities.
- Preserved Ubuntu 24.04 compatibility by probing Git 2.45's `--no-lazy-fetch`
  before use. Checks disable replacement objects on all supported Git versions.

## [1.13.0] (2026-08-28)

### Added
- Expanded destructive-command policy across Bash, PowerShell, nested shells,
  and CMD payloads. Root and system deletion, formatting and repair tools,
  `dd`, drive firmware tools, recovery destruction, truncating redirects,
  interpreter pipelines, alias definitions, `crontab -r`, scheduled-task
  deletion, and destructive forge operations receive refusal without a prompt.
- Routed consent-sensitive operations to active human approval. Covered
  operations include non-root recursive deletion and `git branch -D`.
  Coverage includes history rewriting and destructive Git cleanup. Coverage
  includes privilege escalation, process termination, and secure erasure.
  Coverage includes `find -delete`, `-exec`, glob truncation, and shell startup
  writes. Coverage includes mount-point operations and logging shutdown.
  Unattended modes deny every gated act.
- Added a PowerShell destructive-command hook with the same decisions as the
  Bash hook. The hook handles cmdlet aliases, abbreviated parameters, script
  blocks, subexpressions, encoded commands, and redirections. The hook handles
  commands launched through PowerShell process APIs. Synthetic hook payloads
  test PowerShell behavior. The tests launch no native PowerShell commands.
- Added consent enforcement for test changes. Every direct editor tool edit to
  an existing test file asks for active human approval. Coverage includes case
  variants, Windows filename decorations, links, and alternate paths. Direct
  creation of a new test file passes. Known shell writers prompt on paths that
  look like tests without checking whether the target exists.
- Added safe classification of Git aliases, effective repositories, config and
  environment overrides, linked worktrees, and read commands that repository
  configuration can turn into code execution. Unknown or uninspectable forms
  fail closed without executing configuration that the repository defines.
- Added per-act consent language. Clarified Rule 2 coverage for scratch paths.
  Disclosure and planned specification changes cannot replace consent for test
  changes. Pushed-history rules now explicitly cover `--force-with-lease` and
  newly created branches.
- Added adopter instructions for copying and registering both shell gates.
  The instructions cover the shared decision core and test consent hook. The
  instructions also cover associated verification suites. Hook installation
  remains tooling that requires Rule 9 approval.

### Changed
- Replaced pickle hook-coverage traces with validated JSON. Validated JSON
  prevents artifacts under test control from executing code in the coverage
  checker.
- Unified Bash, PowerShell, and CMD command classification across nested shells,
  `eval`, `exec`, wrappers, substitutions, aliases, chains, and malformed input.
  Gates select the strongest verdict and bound recursive command unwrapping.
- Applied branch-name and identity checks to the effective Git repository and
  configuration, including `-C`, worktree options, aliases, inline settings,
  environment vectors, and linked-worktree common configuration. Safe reads and
  standalone `git config` remain available.
- Routed known shell writers targeting `hooks/`, `.claude/`, and `scripts/`
  through consent prompts. Direct edit-tool protection covers existing tests,
  `hooks/`, and `.claude/`. Direct edit-tool protection excludes `scripts/`.
  Unknown writers can pass. These repository hooks provide defense-in-depth
  workflow prompts. The hooks create no security boundary or tamper-resistant
  sandbox.
- Rewrote Rule 2 to match the enforced deny and prompt classes. Rule 2 now
  requires a non-destructive alternative, exact command restatement,
  confirmation, and an authorization record. Rule 2 procedural requirements
  lack mechanical enforcement.
- Changed `git push --force` and `-f` from an unconditional refusal to an
  active human prompt. Force variants, delete and mirror pushes, amend, rebase,
  and `filter-branch` require consent. Unattended sessions still deny these
  operations.
- Denied normalized drive, UNC, POSIX, macOS system-root deletion and permission
  changes on both Linux and Windows. Paths within those roots remain prompts for
  recursive deletion. Unparseable commands aimed at root receive denial.
- Separated fixed instructions from escaped repository data in session context.
  Permission prompts and errors now render untrusted values as bounded printable
  ASCII, report unknown permission modes, and deny malformed payloads or
  unreadable test files instead of failing open.
- Registered hooks in exec form without a shell and switched the configured
  launcher from `python3` to `python` for Windows. Added `windows-latest` CI to
  cover launcher availability, case-insensitive paths, and symlink restrictions.
  Debian adopters without `python` must override the launcher.
- Exempted merge commits from the advisory commit message checker because Git
  generates subjects outside the required `type: description` form.
- Activated the destructive Bash hook in this repository. The hook served
  only as an example since 1.11.0. The parser now normalizes command variants, asks or
  denies as policy requires, and fails closed on ambiguity.
- Aligned Rule 3 and README hook documentation with the final consent behavior,
  permission modes, shell-write coverage, and live hook set. The deny and prompt
  lists now have one canonical home in Rule 2.
- Added a gate threat model, adopter drift records, and shared file SHA-256
  checks with line-ending normalization for manually copied gate files.
- Added subprocess hook coverage enforcement using validated traces. CI rejects
  newly unreachable code and stale baselines. Baseline creation works from a
  fresh adoption. Root cannot write a baseline. Trace files live outside
  commonly ignored coverage directories.
- Expanded ASCII checks to repository prose and removed false positives for
  Markdown table delimiters, list markers, and multiline code spans.
- Synced the rule changes into all eight tool-specific copies.

## [1.12.0] (2026-08-20)

### Added
- Added Rule 14 requiring identity checks before the first commit. The rule
  requires GitHub noreply addresses. The rule requires consent before rewriting
  a wrong identity in history. Git identity remains separate from `gh`.
- Added a portable checker for the next commit, unpushed commits, and pull
  request ranges. The checker supports configurable allow patterns and advisory
  guidance.
- Added live Claude Code enforcement at session start, commit, and push. The
  enforcement blocks disallowed identities and commits that a push would
  publish. `git config` remains available as the recovery path.
- Recorded that the identity hook misses the forms of `git merge`,
  `git revert`, `git cherry-pick`, `git rebase`, and `git am` that write
  commits.
- Added identity checks to pre-commit, pre-push, pull request CI, and the
  `Makefile`. Added adopter documentation.

### Changed
- Included identity enforcement in hook verification. Aligned README references
  with the new rule and tooling.

## [1.11.0] (2026-08-17)

### Added
- Added live Claude Code branch-name enforcement at session start, commit, and
  push. `git branch -m` provides the recovery path.
- Added repository and example settings. The destructive Bash hook remained
  opt-in and inactive in this release.
- Applied naming rules to branches that the harness assigns. Documented pre-push and
  Claude Code adopter wiring.
- Added hook verification to local tests, CI, and pre-commit without a
  dependency. Adopters must copy the suite.

### Changed
- Aligned README hook and local-check documentation. Corrected the `.claude/`
  directory description.

## [1.10.0] (2026-08-15)

### Added
- Added an opt-in `CONTRIBUTING.md.example` covering setup, conventions,
  security, review, code quality, and workflow.
- Added live pull request and issue templates for summaries, test plans, bugs,
  and rule or template proposals.
- Documented adoption. Extended spelling, language, hedging, and ASCII checks
  to all three files.
- Added an opt-in policy that routes reports through GitHub private
  vulnerability reporting. Added adoption guidance.
- Extended spelling, language, hedging, and ASCII checks to the security policy.
- Added an opt-in handoff template pairing status claims with verification
  commands. Added adoption guidance.
- Extended spelling, language, hedging, dash, and ASCII checks to the handoff
  template.
- Added advisory AgentLint `0xmariowu/AgentLint@v1.1.13` with `fail-below: '0'`.
  No valid score could trigger the score-threshold failure. Action failures
  could still fail the step.
- Added `pull-requests: write`. Pinned `actions/github-script@v9.0.0` for score
  and report comments.
- Documented AgentLint separately from portable repository checkers.
- Added prose rules against hedging, self-justification, self-narration, task
  references, and unsupported claims.
- Extended comment guidance to prohibit historical implementation narration.
- Added a portable advisory hedging checker to existing CI. Documentation
  records the heuristic contract.
- Explicitly banned `claude/` branches. Dependabot receives exemptions from
  formats outside Dependabot configuration.
- Added an opt-in reusable compliance workflow. Consumers must pin the workflow
  to a released tag. Moving references such as `@main` remain prohibited.
- Added concurrency cancellation for superseded runs. Added reruns when a pull
  request leaves draft status.

### Changed
- Reduced the live compliance workflow to a thin reusable-workflow caller.
- Made commit message checks advisory. Keyed Dependabot exemptions to the
  pull request author.
- Documented reusable adoption, efficient custom CI, banned-agent checks, and
  versioning.

## [1.7.0] (2026-08-08)

### Added
- Added checker references to the dash, ASCII, spelling, and English rules.
  Marked advisory checks clearly.
- Added a consolidated README checker reference.
- Added an opt-in Bash hook that denied root or home recursive deletion,
  force-push, and `git reset --hard`.
- Added branch-name validation for `<type>/<kebab-description>`. Primary
  branches and detached HEAD receive exemptions.
- Added commit message shape, length, punctuation, and GitHub squash suffix
  validation.
- Added both checks to pull request CI and branch validation to pre-push. Added
  rule references.
- Added checkers for persisted checkout credentials, weak hashes, root
  containers, secrets, and environment files.
- Added the Rule 12 exception form
  `# runtime-root: this container <reason> (Rule 12 exception).`.
- Added all four checkers to CI and pre-commit. Added rule references and
  adopter guidance.
- Added Rule 13. The rule prohibits enforcement claims without real checks.
  The rule requires a proposed check with each mechanically enforceable rule.
- Added pull request CI that compares commit authors, committers, co-author
  trailers, and pull request authors against the banned-agent denylist.
- Allowed adopters to prune inapplicable rules and associated checks with
  active human approval.
- Added American English and English-only rules for code, comments, commit
  messages, and documentation, including projects targeting other languages.
- Added portable advisory spelling and English heuristics plus a portable
  blocking dash and ASCII checker.
- Added the advisory checks to local lint and CI, with adopter guidance and
  each checker's exit-code contract.

### Changed
- Consolidated duplicate README checker descriptions into the reference table.
- Documented that banned-agent checks cannot detect an agent using only a human
  identity with no trailer.

## [1.2.0] (2026-07-19)

### Added
- Required `persist-credentials: false` on checkout steps that do not need Git
  credentials afterward.
- Required non-root containers by default, with explicit consent before runtime
  root configuration.

### Fixed
- Set `persist-credentials: false` on the `sync-check.yml` checkout step under
  the new rule.

## [1.1.0] (2026-07-16)

### Added
- Added rules against suppressing lint, type, test, or CI checks to force a
  pass.
- Added consent requirements for force-push, rebase, amend, or reset of published
  commits on shared branches.
- Added the no-run-on-sentences rule and local plus CI enforcement for dash and
  ASCII rules.

### Changed
- Expanded the dash rule to hyphen substitutes and renamed the character rule to
  **No non-ASCII characters**. Limited Unicode to required literals or data.
- Closed self-attested exceptions in weak hashing, draft pull requests,
  test-first mocking, retry discipline, and magic-number naming.
- Expanded incomplete-work markers to `XXX`, `HACK`, stubs, and bare `pass`, and
  required excess commit detail in the body instead of a truncated subject.

### Fixed
- Removed dash, ASCII, and emoji violations from `AGENTS.md` examples.

## [1.0.0] (2026-07-11)

### Added
- Added documentation and SemVer rules. Added imperative-tone guidance and path
  traversal protections.
- Added Copilot instruction files to rule synchronization.
- Added local pre-commit and `Makefile` sync checks plus read-only GitHub Actions
  CI.
- Added Roo Code and OpenHands compatibility guidance.

### Changed
- Reworked `AGENTS.md` into concise imperative instructions and excluded
  redundant rule copies from Claude context.
- Updated adopter guidance for custom rules, command verification, and
  unauthorized-change prevention.
