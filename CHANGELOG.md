# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
with one deviation: a version heading parenthesizes its date,
`## [1.2.3] (2026-01-01)`, rather than setting it off with a spaced hyphen.
The house style bans that hyphen and `scripts/check_ascii.py` enforces the ban
on this file.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added `scripts/check_compliance_tree.py` to run trusted base checkers against
  bounded blobs from one validated commit or tree. It covers regular and
  symlink blobs, commit and pull request identities, branch names, immutable
  action revisions, and the execution surface of `pull_request_target`
  workflows without importing pull request code.
- Added `scripts/check_conflict_markers.py` with worktree, staged, and immutable
  tree scanning. It bounds object reads, rejects malformed Git data, ignores
  replacement refs, handles sparse checkouts and UTF-16 or UTF-32 BOMs, honors
  conflict marker attributes, and distinguishes Markdown Setext headings.
- Added `.github/workflows/immutable-conflict-check.yml`, a base-defined
  `pull_request_target` workflow whose immutable compliance scan is the sole
  privileged job.
- Added pinned `PyYAML==6.0.3` checker requirements for safe YAML parsing.
- Added a permanent security header, active-work structure, command-execution
  prohibition, and sensitive-data protections to `plan/HANDOFF.md.example`.
- Added adversarial coverage for filesystem races, parser bypasses, local Git
  executable substitution, immutable secrets and actions, symlink blobs, and
  workflow trust boundaries.

### Changed
- Reduced the privileged `pull_request_target` workflow to one read-only,
  immutable compliance job. Dependency specifications and checker code come
  from the exact trusted base. Pull request input remains data, and retargeting
  a pull request reruns the job.
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
  blobs for absent files, preserving unstaged and indexed conflict detection.
- Replaced digest-driven handoff instructions with active-user consent. Handoff
  content remains untrusted status, Git commands require consent, and displayed
  Git output requires trusted external sanitization.
- Selected Python through overridable `PYTHON ?= python3` in the `Makefile` for
  Debian compatibility and local interpreter overrides.
- Reorganized repository documentation around canonical current behavior and
  split prose clauses into complete sentences.

### Fixed
- Hardened `scripts/sync.py` against symlink traversal, repository escapes,
  partial writes, and destination races through path revalidation and atomic
  replacement.
- Rejected duplicate YAML keys. Rule 11 now requires boolean `false`, and Rule
  12 evaluates the final Dockerfile user plus every Compose service and
  Kubernetes container independently.
- Expanded weak-hash analysis across Python imports, aliases, and `hashlib.new`,
  with real non-security justification comments required. Secret scanning now
  blocks every `.env.*` variant except `.env.example` and recognizes encrypted
  and PGP private-key headers.
- Made branch, commit, banned-agent, and identity checks use an absolute Git
  executable outside the repository and fail closed on lookup or output errors.
  Co-author keys are case-insensitive and only terminal structured trailers
  contribute identities.
- Preserved Ubuntu 24.04 compatibility by probing Git 2.45's `--no-lazy-fetch`
  before use. Replacement objects remain disabled on all supported Git versions.

## [1.13.0] (2026-08-25)

### Added
- Expanded destructive-command policy across Bash, PowerShell, nested shells,
  and CMD payloads. Root and system deletion, formatting and repair tools,
  `dd`, drive firmware tools, recovery destruction, truncating redirects,
  interpreter pipelines, alias definitions, `crontab -r`, scheduled-task
  deletion, and destructive forge operations deny outright.
- Routed consent-sensitive operations to the user, including non-root recursive
  deletion, `git branch -D`, history rewriting and destructive Git cleanup,
  privilege escalation, process termination, secure erasure, `find -delete` or
  `-exec`, glob truncation, shell startup writes, mount-point operations, and
  logging shutdown. Unattended modes deny every gated act.
- Added a PowerShell destructive-command hook with the same decisions as the
  Bash hook. It handles cmdlet aliases, abbreviated parameters, script blocks,
  subexpressions, encoded commands, redirections, and commands launched through
  PowerShell process APIs. Its behavior is tested with synthetic hook payloads
  only, not by launching native PowerShell commands.
- Added consent enforcement for test changes. Every direct editor-tool edit to
  an existing test file asks the user, including edits through case variants,
  Windows filename decorations, links, and alternate paths. Direct creation of
  a new test file passes. Known shell writers prompt on test-shaped paths
  without checking whether the target exists.
- Added safe classification of Git aliases, effective repositories, config and
  environment overrides, linked worktrees, and read commands that repository
  configuration can turn into code execution. Unknown or uninspectable forms
  fail closed without executing repository-defined configuration.
- Added per-act consent language, clarified that Rule 2 covers scratch paths,
  and stated that disclosure or a planned specification change cannot replace
  consent for changing tests. Pushed-history rules now explicitly cover
  `--force-with-lease` and newly created branches.
- Added adopter instructions for copying and registering both shell gates, the
  shared decision core, the test consent hook, and their verification suites.
  Hook installation remains tooling that requires Rule 9 approval.

### Changed
- Replaced pickle hook-coverage traces with validated JSON so test-controlled
  artifacts cannot execute code in the coverage checker.
- Unified Bash, PowerShell, and CMD command classification across nested shells,
  `eval`, `exec`, wrappers, substitutions, aliases, chains, and malformed input.
  Gates take the strongest verdict and bound recursive command unwrapping.
- Applied branch-name and identity checks to the effective Git repository and
  configuration, including `-C`, worktree options, aliases, inline settings,
  environment vectors, and linked-worktree common configuration. Safe reads and
  standalone `git config` remain available.
- Routed known shell writers targeting `hooks/`, `.claude/`, and `scripts/`
  through consent prompts. Direct edit-tool protection covers existing tests,
  `hooks/`, and `.claude/`, but not `scripts/`. Unknown writers can pass. These
  repository hooks remain defense-in-depth workflow prompts, not a security
  boundary or tamper-resistant sandbox.
- Rewrote Rule 2 to match the enforced deny and prompt classes. It now requires
  a non-destructive alternative, exact command restatement, confirmation, and an
  authorization record. Those procedural requirements are not mechanically
  enforced.
- Changed `git push --force` and `-f` from an unconditional refusal to a user
  prompt. Force variants, delete and mirror pushes, amend, rebase, and
  `filter-branch` require consent, while unattended sessions still deny them.
- Denied normalized drive, UNC, POSIX, macOS system-root deletion and permission
  changes on both Linux and Windows. Paths within those roots remain prompts for
  recursive deletion, and unparseable root-targeting commands deny.
- Separated fixed instructions from escaped repository data in session context.
  Permission prompts and errors now render untrusted values as bounded printable
  ASCII, report unknown permission modes, and deny malformed payloads or
  unreadable test files instead of failing open.
- Registered hooks in shell-free exec form and switched their configured
  launcher from `python3` to `python` for Windows. Added `windows-latest` CI to
  cover launcher availability, case-insensitive paths, and symlink restrictions.
  Debian adopters without `python` must override the launcher.
- Exempted merge commits from the advisory commit-message checker because Git
  generates subjects outside the required `type: description` form.
- Activated the destructive Bash hook in this repository after it had remained
  example-only since 1.11.0. Its parser now normalizes command variants, asks or
  denies as policy requires, and fails closed on ambiguity.
- Aligned Rule 3 and README hook documentation with the final consent behavior,
  permission modes, shell-write coverage, and live hook set. The deny and prompt
  lists now have one canonical home in Rule 2.
- Added a gate threat model, adopter drift records, and shared-file SHA-256
  checks with line-ending normalization for manually copied gate files.
- Added subprocess hook coverage enforcement using validated traces. CI rejects
  newly unreachable code and stale baselines, baseline creation works from a
  fresh adoption, root cannot write a baseline, and trace files live outside
  commonly ignored coverage directories.
- Expanded ASCII checks to repository prose and removed false positives for
  Markdown table delimiters, list markers, and multiline code spans.
- Synced the rule changes into all eight tool-specific copies.

## [1.12.0] (2026-08-20)

### Added
- Added Rule 14 requiring identity checks before the first commit, GitHub noreply addresses, and consent before
  rewriting a wrong identity in history. Git identity remains separate from `gh`.
- Added a portable checker for the next commit, unpushed commits, and pull request ranges, with configurable
  allow patterns and advisory guidance.
- Added live Claude Code enforcement at session start, commit, and push. It blocks disallowed identities and
  commits a push would publish, while leaving `git config` available as the recovery path.
- Recorded that the identity hook does not match commit-writing forms of
  `git merge`, `git revert`, `git cherry-pick`, `git rebase`, or `git am`.
- Added identity checks to pre-commit, pre-push, pull request CI, and the `Makefile`, plus adopter documentation.

### Changed
- Included identity enforcement in hook verification and aligned README references with the new rule and tooling.

## [1.11.0] (2026-08-17)

### Added
- Added live Claude Code branch-name enforcement at session start, commit, and push, with `git branch -m` as
  the recovery path.
- Added repository and example settings. The destructive Bash hook remained opt-in and inactive in this release.
- Applied naming rules to harness-assigned branches and documented pre-push plus Claude Code adopter wiring.
- Added hook verification to local tests, CI, and pre-commit without a dependency. Adopters must copy the suite.

### Changed
- Aligned README hook and local-check documentation and corrected the `.claude/` directory description.

## [1.10.0] (2026-08-15)

### Added
- Added an opt-in `CONTRIBUTING.md.example` covering setup, conventions, security, review, code quality, and workflow.
- Added live pull request and issue templates for summaries, test plans, bugs, and rule or template proposals.
- Documented adoption and extended spelling, language, hedging, and ASCII checks to all three files.

## [1.9.0] (2026-08-15)

### Added
- Added an opt-in policy that routes reports through GitHub private vulnerability reporting, plus adoption guidance.
- Extended spelling, language, hedging, and ASCII checks to the security policy.

## [1.8.0] (2026-08-15)

### Added
- Added an opt-in handoff template pairing status claims with verification commands, plus adoption guidance.
- Extended spelling, language, hedging, dash, and ASCII checks to the handoff template.

## [1.7.3] (2026-08-15)

### Added
- Added advisory AgentLint `0xmariowu/AgentLint@v1.1.13` with `fail-below: '0'`,
  so no valid score could trigger its score-threshold failure. Action failures
  could still fail the step.
- Added `pull-requests: write` and pinned `actions/github-script@v9.0.0` for score and report comments.
- Documented AgentLint separately from portable repository checkers.

## [1.7.2] (2026-08-15)

### Added
- Added prose rules against hedging, self-justification, self-narration, task references, and unsupported claims.
- Extended comment guidance to prohibit historical implementation narration.
- Added a portable warning-only hedging checker to existing CI and documented its heuristic contract.

## [1.7.1] (2026-08-15)

### Added
- Explicitly banned `claude/` branches and exempted Dependabot from formats it cannot configure.
- Added an opt-in reusable compliance workflow. Consumers must pin it to a released tag, never `@main`.
- Added concurrency cancellation for superseded runs and reruns when a pull request leaves draft status.

### Changed
- Reduced the live compliance workflow to a thin reusable-workflow caller.
- Made commit-message checks warning-only and keyed Dependabot exemptions to the pull request author.
- Documented reusable adoption, efficient custom CI, banned-agent checks, and versioning.

## [1.7.0] (2026-08-08)

### Added
- Added checker references to the dash, ASCII, spelling, and English rules, with advisory checks marked clearly.
- Added a consolidated README checker reference.
- Added an opt-in Bash hook that denied root or home recursive deletion, force-push, and `git reset --hard`.

### Changed
- Consolidated duplicate README checker descriptions into the reference table.

## [1.6.0] (2026-08-08)

### Added
- Added branch-name validation for `<type>/<kebab-description>`, exempting primary branches and detached HEAD.
- Added commit-message shape, length, punctuation, and GitHub squash suffix validation.
- Added both checks to pull request CI and branch validation to pre-push, with rule references.

## [1.5.0] (2026-08-08)

### Added
- Added checkers for persisted checkout credentials, weak hashes, root containers, secrets, and environment files.
- Added the Rule 12 exception form
  `# runtime-root: this container <reason> (Rule 12 exception).`.
- Added all four checkers to CI and pre-commit, with rule references and adopter guidance.

## [1.4.0] (2026-08-08)

### Added
- Added Rule 13, which prohibits enforcement claims without real checks and
  requires proposing a check with each mechanically enforceable rule.
- Added pull request CI that compares commit authors, committers, co-author
  trailers, and pull request authors against the banned-agent denylist.
- Allowed adopters to prune inapplicable rules and their checks with user
  approval.

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
- Set `persist-credentials: false` on the `sync-check.yml` checkout step per the new rule.

## [1.1.0] (2026-07-16)

### Added
- Added rules against suppressing lint, type, test, or CI checks to force a pass.
- Added consent requirements for force-push, rebase, amend, or reset of published
  commits on shared branches.
- Added the no-run-on-sentences rule and local plus CI enforcement for dash and
  ASCII rules.

### Changed
- Expanded the dash rule to hyphen substitutes and renamed the character rule to
  **No non-ASCII characters**, limiting Unicode to required literals or data.
- Closed self-attested exceptions in weak hashing, draft pull requests,
  test-first mocking, retry discipline, and magic-number naming.
- Expanded incomplete-work markers to `XXX`, `HACK`, stubs, and bare `pass`, and
  required excess commit detail in the body instead of a truncated subject.

### Fixed
- Removed dash, ASCII, and emoji violations from `AGENTS.md` examples.

## [1.0.0] (2026-07-11)

### Added
- Added documentation and SemVer rules, imperative-tone guidance, and path traversal protections.
- Added Copilot instruction files to rule synchronization.
- Added local pre-commit and `Makefile` sync checks plus read-only GitHub Actions
  CI.
- Added Roo Code and OpenHands compatibility guidance.

### Changed
- Reworked `AGENTS.md` into concise imperative instructions and excluded
  redundant rule copies from Claude context.
- Updated adopter guidance for custom rules, command verification, and
  unauthorized-change prevention.
