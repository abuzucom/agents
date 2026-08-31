# Gate coverage and limits

This document summarizes exercised hook behavior and known limits. Repository
hooks provide advisory controls. The documented controls lack a security
boundary.

## Covered

A model acts through supported tools on POSIX or Windows. Covered attempts
include the following actions:

- The gates classify recursive deletes against every target. Drive roots deny.
  UNC share roots deny. System directories deny. All other targets ask.
- The gates classify filesystem formatting, repair, and raw device writes.
  Covered programs include `mkfs`, `diskpart`, `fdisk`, `fsck`, `dd`, and
  `hdparm`. Coverage also includes a redirect onto a device.
- The gates detect truncating redirects without a delete in the line. Examples
  include `> file` and `cat /dev/null > file`.
- The gates detect pipes into interpreters. Sources include downloads and shell
  history.
- The gates classify history rewrites and published-ref deletion. Covered forms
  include `--force`, `--force-with-lease`, `--mirror`, `--delete`, `--prune`, a
  forced or empty refspec, `--amend`, `rebase`, `filter-branch`, `reset --hard`,
  `branch -D`, and `clean -fdx`.
- The gates classify privilege escalation, process termination, alias
  definition, shell profile writes, schedule destruction, and forge deletion.
- The gates classify recovery destruction through `vssadmin`, `wbadmin`,
  `wmic shadowcopy`, and `bcdedit`.
- The consent hook gates direct editor-tool writes to existing tests. The same
  hook gates direct editor-tool writes to protected paths under `hooks/` and
  `.claude/`.
- The shell gates classify writes with a recognized redirect or writer target
  that has a test-shaped path. This classification ignores target existence.
- The shell gates classify known Bash and PowerShell writers that target
  `hooks/`, `.claude/`, or `scripts/`. PowerShell named path and destination
  parameters accept valid unambiguous prefixes. The parser reads each parameter
  independently of order.
- The gates classify a git read command in a repository whose effective config
  declares a key naming a program that git runs. Covered read commands include
  `status`, `diff`, `log`, `show`, `blame`, and `grep`. The classifier accounts
  for ordered `-c` settings and leading environment assignments. The classifier
  also accounts for config vectors, path overrides, `GIT_DIR`,
  `GIT_COMMON_DIR`, `-C`, `--git-dir`, `--work-tree`, gitfiles, and
  linked-worktree common config. Repository discovery walks upward from an
  effective `-C` directory on the same device. A depth bound limits discovery.
  `GIT_CONFIG_PARAMETERS` triggers fail-closed handling.
- The gates classify persistent Bash exports and PowerShell environment
  assignments that can make a later git read execute a pager, external diff,
  or configured program. Covered forms include `export`, `declare -x`,
  `typeset -x`, plain PowerShell environment references, braced PowerShell
  environment references, `Set-Item`, and `Set-Variable`.
- The gates classify git commit, git push, and aliases that resolve to those
  operations. The gates read aliases from the effective repository and inline
  config without executing the aliases. Branch-name and identity checks pass
  the effective Git cwd into each checker subprocess. The checks also pass
  repository locations and inline settings. The checks inspect every commit and
  push in a chained command. The checks also inspect every alias that resolves
  to either operation. A possible alias creates ambiguity for an unknown
  subcommand. Unavailable alias sources preserve that ambiguity.
- Strict branch preflight reads bounded Git `HEAD` metadata without launching
  Git. The gate blocks every observable ordinary tool on an invalid branch.
  Active-human question tools remain available. One exact correction command
  remains available. Chaining, wrappers, substitutions, and redirects prevent
  correction clearance.
- Lifecycle hooks read bounded canonical `AGENTS.md` content. Claude injects
  numbered chunks into built-in Explore and Plan agents. Codex injects complete
  context at session and subagent lifecycle events. Gemini and Antigravity
  inject complete context before each model invocation.
- The gates classify commands that one shell passes to another shell. Each
  gate reads both interpreter names. The Bash gate denies `powershell -Command
  'Remove-Item -Recurse -Force /etc'`. The PowerShell gate denies `bash -c 'rm
  -rf /etc'`. The shared core contains POSIX, PowerShell, and CMD delete
  readings. The classifier tries all three readings together.
- The PowerShell gate classifies commands inside script blocks such as
  `& { ... }`. The gate also classifies commands that programs pass through
  `Start-Process -ArgumentList`. Wrapper unwrapping has a bound. Commands past
  the bound deny.
- The PowerShell gate classifies `EncodedCommand` under every supported
  abbreviation and alias. Base64 decoding applies strict validation. UTF-16LE
  decoding also applies strict validation. Decoded commands re-enter the
  bounded classifier. Missing payloads deny. Malformed payloads deny.
  Over-nested payloads deny.

Editor-tool handling resolves the named target with `realpath`. The handler
checks the raw name and resolved name. The handler also checks hard-linked test
inodes. The handler gates test-shaped targets outside the project root. The
shell gates parse command text instead. The shell test-path check uses lexical
analysis. The check handles case variants and alternate data streams. The check
also handles trailing dots or spaces. Shell handling canonicalizes known
protected-path targets. Shell handling omits the editor gate's inode scan.
General shell symlink, hard-link, and short 8.3 handling remain outside the
documented coverage.

The destructive and consent gates deny malformed top-level JSON. The same gates
deny non-object payloads. Branch and identity hooks treat malformed input as an
empty `SessionStart` payload. Applicable tools deny a non-object tool input.
Applicable tools also deny a non-string command or non-null non-string editor
path. A null editor path counts as absent. Existing-test editor paths ask in an
interactive mode. An unrelated malformed field leaves the verdict unchanged.
Examples include a null or numeric `old_string`. An unrecognized
`permission_mode` changes a gated verdict from ask to deny. Calls without a
gated verdict ignore an unrecognized `permission_mode`.

The shared reason builders apply `sanitize` to displayed Git subcommands,
permission modes, environment names, selected program and target names, editor
target basenames, and file-open errors. The function bounds text. The function
renders non-printable and non-ASCII characters visibly. Branch and identity
`SessionStart` warning builders sanitize checker output before placement in
`additionalContext`. Universal output sanitization remains outside the
guarantee. Import-error text remains untrusted output. Checker stderr from
other paths also remains untrusted output.

## Explicit non-goals

Repository hooks operate inside the writable repository. A repository writer
can alter hook source and registration. Tamper resistance requires an external
harness, filesystem isolation, or server-side controls. The template omits
those controls.

- The classifier lacks visibility into commands behind aliases to shell
  functions. The classifier also lacks visibility into wrapper scripts on
  `PATH` and variables holding program names. Unknown writers remain heuristic
  gaps. Write programs with unrecognized parameter shapes remain heuristic
  gaps. Commands with program names hidden in variables remain heuristic gaps.
  A detectable shape fails closed to `ask`. An undetectable shape passes
  unseen.
- Per-call hooks lack telemetry for rate and volume analytics. Examples include
  "N deletions in M minutes" and correlation with an anomalous login. Each gate
  reads one command shape.
- Gate registration defines tool coverage. Unregistered tools bypass the gates.
- Codex hosted tools bypass local `PreToolUse` hooks. Claude does not document
  aggregate ordering for parallel subagent policy chunks. Gemini and
  Antigravity do not document hook inheritance for every subagent
  implementation.
- Project hooks require client trust where supported. Client controls can
  disable project hooks. Repository writers can modify every committed hook.
- Hooks cannot enforce Rule 4. A hook sees the proposed action. The hook
  receives the action without a scope statement. The missing scope prevents
  classification of in-scope and out-of-scope changes.
- Content filtering remains outside the goal. The shared gate values above
  receive character rendering and length bounds. Other checker output can
  remain untrusted. Displayed wording never determines authorization.

## Modes and limits

`INTERACTIVE_MODES` lists the `permission_mode` values in which a person can
answer a gated prompt. An unrecognized value denies a gated verdict. The
current behavior correctly handles `bypassPermissions`. A future interactive
mode would also deny. A legitimate gated action would then fail closed. Review
the list when Claude Code adds a mode.

The editor-tool inode walk for hard-linked tests runs only when `st_nlink > 1`.
The walk skips `.git`, `node_modules`, `.venv`, and `__pycache__`. The walk
carries a budget.
Budget exhaustion returns an incomplete result. The caller gates an incomplete
result conservatively. Directory traversal errors also return an incomplete
result. Candidate stat errors produce the same result. An incomplete result
prevents write clearance.

The Python classifier receives synthetic hook payloads for PowerShell coverage.
Coverage lacks an exercised live PowerShell tool call.

## Coverage baseline

The suites run each gate as a subprocess. Tracing uses a `sitecustomize` module
on `PYTHONPATH`. Supported runtimes use local `sys.monitoring` line events when
the coverage tool slot remains available. Other runtimes use a target-scoped
`sys.settrace` fallback. Both implementations record only hook source lines.
The baseline records unreached statements by function. Each entry requires a
reason.

- The `_bash_parser` entries and the Bash and PowerShell parser entries retain
  malformed branches and missing-operand branches. The entries also retain
  alternate `env -S`, direct-caller, and maximum-depth branches. Subprocess
  entry points reject some branches earlier. Other branches require syntactic
  forms outside the regression corpus.
- The Git config and repository-discovery helpers, including
  `_apply_git_config_argument`, `_apply_git_path_argument`,
  `_environment_config`, `_parent_repository_dir`, and
  `_read_invocation_configs`, retain bounds and missing optional files. The
  helpers also retain invalid-key and filesystem-error arms. The suite exercises
  representative fail-closed classes and executable settings. Equivalent arms
  remain outside coverage.
- The commit and push context helpers, `git_checker_environment`,
  `_alias_write_label`, `_shell_alias_write_label`, and both enforcement
  handlers retain malformed global options. The same functions retain
  alias-depth variants and shell-alias variants. Absent config sources and
  error-reporting arms also remain.
- `_protected_path`, `_is_system_root`, `_mentions_device`,
  `_segment_program`, `device_write_verdict`, `forge_verdict`,
  `logging_verdict`, `mass_operation_verdict`, `posix_delete_verdict`,
  `remote_execution_verdict`, `schedule_verdict`, `unparseable_verdict`, and
  `volume_verdict` retain platform, device, mount, and uncommon-program arms.
  Corpus rows exercise representative outcomes. The corpus avoids building
  real devices or mounts.
- `read_payload`, `resolved_under`, and `sanitize` retain defensive exceptions
  and direct-caller bounds. Hook entry points reject those states earlier.
- `current_branch` retains the post-resolution containment check for a replaced
  or linked `.git/HEAD`. A portable test cannot create that filesystem race.
- `load_policy` retains the post-read size check for policy growth after
  `lstat`. A deterministic test cannot create that filesystem race.
- The consent entries retain cross-drive path handling, absent path fields, and
  the top-level exception boundary. Narrow OS-boundary tests cover out-of-tree
  paths and open errors. The tests also cover the hard-link budget and ordinary
  denial paths.

CI runs `scripts/check_hook_coverage.py`. The script compares the run against
`hook-coverage-baseline.json`. Per-function counts prevent churn from edits
above a function. The script fails when a function gains unreached statements.
Such statements represent new code outside test coverage. The script also fails
when a function loses unreached statements. Such a loss marks a stale baseline.
The checker runs each test class in a separate process. Up to four workers run
concurrently. Start notices, completion notices, and 30-second heartbeats expose
progress. A 300-second per-class timeout terminates that process tree and fails
the check. Coverage comparison starts only after every worker succeeds.

Every baseline entry requires a reason in this document. An unexplained entry
represents untested code. A recorded exception requires an explanation.

The baseline tool conservatively refuses baseline writes as root.
Permission-mode tests use real files. Narrow patches at `os.open` and `os.stat`
exercise error boundaries independently of account privileges. Windows and
Linux therefore record the same consent-hook branches.
