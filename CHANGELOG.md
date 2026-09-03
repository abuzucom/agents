# Changelog

This file documents every notable project change.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
One deviation applies. A version heading parenthesizes the release date.
The format uses `## [1.2.3] (2026-01-01)` instead of a spaced hyphen.
The house style bans that hyphen. `scripts/check_ascii.py` enforces the ban on
this file.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added Rule 17. The rule bans GitHub cross-references to a repository outside
  the current owner. The rule requires active-human consent before any
  outward-facing act on such a repository.
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
- Added repository-only orientation markers and adoptable policy output through
  `python scripts/sync.py --print-adoptable`.
- Added regression coverage for safe Git state output and repository-only
  policy filtering.
- Added `scripts/run_tests.py` for validated class-sharded execution. The runner
  compares shard IDs with standard discovery before running four workers.
- Added complete `AGENTS.md` lifecycle reinjection for Claude, Codex, Gemini,
  and Antigravity project clients. Claude preserves built-in Explore and Plan
  through bounded numbered chunks. Gemini and Antigravity inject the complete
  policy before every model invocation.
- Added strict cross-client branch preflight before every observable tool.
  Exact recovery commands and active-human questions remain available.
- Added regression coverage for lifecycle output, client wiring, strict branch
  recovery, and the trusted Dependabot automation exception.
- Added lifecycle validation coverage for malformed payloads, policy bounds,
  client dispatch, and chunk limits. Added strict branch coverage for Git
  metadata files and alternate tool schemas.
- Added `scripts/prose_policy.py` for shared advisory prose analysis across
  authored files, commit subjects, commit bodies, pull request titles, and pull
  request bodies.
- Added `scripts/prose_bans.txt` with case-insensitive exact entries under
  `[global]` and `[handoff-exempt]` scopes. The policy source skips
  self-scanning. `plan/HANDOFF.md.example` receives the sole scoped vocabulary
  exception. The same handoff file receives the sole conversational-provenance
  exception.
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
- Added `.github/workflows/immutable-conflict-check.yml`, a base-defined
  `pull_request_target` workflow whose immutable compliance scan is the sole
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
  metadata and repository-local identity proposals.
- Added a dedicated infrastructure file-tool gate for credentials, Terraform
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
  file-transfer, and firewall command families on every shell platform.
- Blocked creation and publication of `claude/` branch targets even when the
  current branch conforms. Compliant recovery commands now request native
  execution authorization.
- Blocked repository aliases and direct Git metadata writes that create a
  `claude/` branch target.
- Changed shell command-string payloads to deny. Plain shell transitions and
  fixed local scripts now ask. Missing or root-targeted `su` now denies.
- Changed hook test scheduling to bounded incremental submission with
  fail-fast process termination and 10-second progress notices.
- Added a macOS CI job and removed the duplicate Ubuntu full-suite execution.
- Covered SCP-style remote credential redaction when the path contains an at
  sign.
- Rewrote `AGENTS.md` for concise policy prose without changing lifecycle
  reinjection. Explicit execution requests now authorize named non-destructive
  acts and bounded read-only verification. Rule-specific gates still require
  act-specific confirmation.
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
- Kept `agents-md-compliance.yml` push-only. Tests, sync and style checks, and
  advisory AgentLint now run under the standard unprivileged `pull_request`
  event. Removed AgentLint pull request comments and the need for
  `pull-requests: write` permission.
- Made conflict diagnostics printable ASCII and length-bounded, normalized
  Windows paths for Git attributes, and treated symlink probe failures as
  errors. Sparse scans now combine present worktree files with immutable index
  blobs for absent files. The combined scan preserves unstaged and indexed
  conflict detection.
- Replaced digest-driven handoff instructions with active-user consent. Handoff
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
  Real non-security comments must justify each use. Secret scanning now blocks
  every `.env.*` variant except `.env.example`. Secret scanning recognizes
  encrypted and PGP private-key headers.
- Made branch, commit, banned-agent, and identity checks use an absolute Git
  executable outside the repository and fail closed on lookup or output errors.
  Co-author keys use case-insensitive matching. Only terminal structured
  trailers contribute identities.
- Preserved Ubuntu 24.04 compatibility by probing Git 2.45's `--no-lazy-fetch`
  before use. Checks disable replacement objects on all supported Git versions.

## [1.13.0] (2026-08-25)

### Added
- Expanded destructive-command policy across Bash, PowerShell, nested shells,
  and CMD payloads. Root and system deletion, formatting and repair tools,
  `dd`, drive firmware tools, recovery destruction, truncating redirects,
  interpreter pipelines, alias definitions, `crontab -r`, scheduled-task
  deletion, and destructive forge operations receive refusal without a prompt.
- Routed consent-sensitive operations to active-human approval. Covered
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
- Added consent enforcement for test changes. Every direct editor-tool edit to
  an existing test file asks for active-human approval. Coverage includes case
  variants, Windows filename decorations, links, and alternate paths. Direct
  creation of a new test file passes. Known shell writers prompt on test-shaped
  paths without checking whether the target exists.
- Added safe classification of Git aliases, effective repositories, config and
  environment overrides, linked worktrees, and read commands that repository
  configuration can turn into code execution. Unknown or uninspectable forms
  fail closed without executing repository-defined configuration.
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
  prevents test-controlled artifacts from executing code in the coverage
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
  active-human prompt. Force variants, delete and mirror pushes, amend, rebase,
  and `filter-branch` require consent. Unattended sessions still deny these
  operations.
- Denied normalized drive, UNC, POSIX, macOS system-root deletion and permission
  changes on both Linux and Windows. Paths within those roots remain prompts for
  recursive deletion. Unparseable root-targeting commands receive denial.
- Separated fixed instructions from escaped repository data in session context.
  Permission prompts and errors now render untrusted values as bounded printable
  ASCII, report unknown permission modes, and deny malformed payloads or
  unreadable test files instead of failing open.
- Registered hooks in shell-free exec form and switched the configured
  launcher from `python3` to `python` for Windows. Added `windows-latest` CI to
  cover launcher availability, case-insensitive paths, and symlink restrictions.
  Debian adopters without `python` must override the launcher.
- Exempted merge commits from the advisory commit-message checker because Git
  generates subjects outside the required `type: description` form.
- Activated the destructive Bash hook in this repository after example-only
  status since 1.11.0. The parser now normalizes command variants, asks or
  denies as policy requires, and fails closed on ambiguity.
- Aligned Rule 3 and README hook documentation with the final consent behavior,
  permission modes, shell-write coverage, and live hook set. The deny and prompt
  lists now have one canonical home in Rule 2.
- Added a gate threat model, adopter drift records, and shared-file SHA-256
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
- Recorded that the identity hook does not match commit-writing forms of
  `git merge`, `git revert`, `git cherry-pick`, `git rebase`, or `git am`.
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
- Applied naming rules to harness-assigned branches. Documented pre-push and
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

## [1.9.0] (2026-08-15)

### Added
- Added an opt-in policy that routes reports through GitHub private
  vulnerability reporting. Added adoption guidance.
- Extended spelling, language, hedging, and ASCII checks to the security policy.

## [1.8.0] (2026-08-15)

### Added
- Added an opt-in handoff template pairing status claims with verification
  commands. Added adoption guidance.
- Extended spelling, language, hedging, dash, and ASCII checks to the handoff
  template.

## [1.7.3] (2026-08-15)

### Added
- Added advisory AgentLint `0xmariowu/AgentLint@v1.1.13` with `fail-below: '0'`.
  No valid score could trigger the score-threshold failure. Action failures
  could still fail the step.
- Added `pull-requests: write`. Pinned `actions/github-script@v9.0.0` for score
  and report comments.
- Documented AgentLint separately from portable repository checkers.

## [1.7.2] (2026-08-15)

### Added
- Added prose rules against hedging, self-justification, self-narration, task
  references, and unsupported claims.
- Extended comment guidance to prohibit historical implementation narration.
- Added a portable warning-only hedging checker to existing CI. Documentation
  records the heuristic contract.

## [1.7.1] (2026-08-15)

### Added
- Explicitly banned `claude/` branches. Dependabot receives exemptions from
  formats outside Dependabot configuration.
- Added an opt-in reusable compliance workflow. Consumers must pin the workflow
  to a released tag. Moving references such as `@main` remain prohibited.
- Added concurrency cancellation for superseded runs. Added reruns when a pull
  request leaves draft status.

### Changed
- Reduced the live compliance workflow to a thin reusable-workflow caller.
- Made commit-message checks warning-only. Keyed Dependabot exemptions to the
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

### Changed
- Consolidated duplicate README checker descriptions into the reference table.

## [1.6.0] (2026-08-08)

### Added
- Added branch-name validation for `<type>/<kebab-description>`. Primary
  branches and detached HEAD receive exemptions.
- Added commit-message shape, length, punctuation, and GitHub squash suffix
  validation.
- Added both checks to pull request CI and branch validation to pre-push. Added
  rule references.

## [1.5.0] (2026-08-08)

### Added
- Added checkers for persisted checkout credentials, weak hashes, root
  containers, secrets, and environment files.
- Added the Rule 12 exception form
  `# runtime-root: this container <reason> (Rule 12 exception).`.
- Added all four checkers to CI and pre-commit. Added rule references and
  adopter guidance.

## [1.4.0] (2026-08-08)

### Added
- Added Rule 13. The rule prohibits enforcement claims without real checks.
  The rule requires a proposed check with each mechanically enforceable rule.
- Added pull request CI that compares commit authors, committers, co-author
  trailers, and pull request authors against the banned-agent denylist.
- Allowed adopters to prune inapplicable rules and associated checks with
  active-human approval.

### Changed
- Documented that banned-agent checks cannot detect an agent using only a human
  identity with no trailer.

## [1.3.0] (2026-08-08)

### Added
- Added American English and English-only rules for code, comments, commit
  messages, and documentation, including projects targeting other languages.
- Added portable warning-only spelling and English heuristics plus a portable
  blocking dash and ASCII checker.
- Added the warning-only checks to local lint and CI, with adopter guidance and
  each checker's exit-code contract.

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
