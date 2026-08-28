# Gate coverage and limits

This document summarizes exercised hook behavior and known limits. Repository
hooks are not security boundaries.

## Covered

A model acting through the supported tools on POSIX or Windows, attempting:

- A recursive delete, against any target. Drive roots, UNC share roots, and
  system directories deny. Everything else asks.
- Filesystem formatting, repair, or raw device writes: `mkfs`, `diskpart`,
  `fdisk`, `fsck`, `dd`, `hdparm`, and a redirect onto a device.
- A truncating redirect with no delete in the line: `> file`,
  `cat /dev/null > file`.
- A pipe into an interpreter, whether the source is a download or the shell's
  own history.
- A history rewrite or published-ref deletion: `--force`, `--force-with-lease`,
  `--mirror`, `--delete`, `--prune`, a forced or empty refspec, `--amend`,
  `rebase`, `filter-branch`, `reset --hard`, `branch -D`, `clean -fdx`.
- Privilege escalation, process termination, alias definition, shell profile
  writes, schedule destruction, and forge deletion.
- Recovery destruction: `vssadmin`, `wbadmin`, `wmic shadowcopy`, `bcdedit`.
- Direct editor-tool writes to existing tests. The consent hook also gates
  direct editor-tool writes to protected paths under `hooks/` and `.claude/`.
- Shell writes whose recognized redirect or writer target has a test-shaped
  path. This classification does not check whether the target exists.
- Known Bash and PowerShell writers targeting `hooks/`, `.claude/`, or
  `scripts/`. PowerShell named path and destination parameters accept valid
  unambiguous prefixes and are read independently of their order.
- A git read command (`status`, `diff`, `log`, `show`, `blame`, `grep`) in a
  repository whose effective config declares a key naming a program git runs.
  The classifier accounts for ordered `-c` settings, leading environment
  assignments, config vectors and path overrides, `GIT_DIR`,
  `GIT_COMMON_DIR`, `-C`, `--git-dir`, `--work-tree`, gitfiles, and
  linked-worktree common config. Repository discovery walks upward from an
  effective `-C` directory on the same device, with a depth bound.
  `GIT_CONFIG_PARAMETERS` fails closed.
- A persistent Bash export or PowerShell environment assignment that can make a
  later git read execute a pager, external diff, or configured program. Covered
  forms include `export`, `declare -x`, `typeset -x`, plain and braced
  PowerShell environment references, `Set-Item`, and `Set-Variable`.
- Git commit, push, and aliases resolving to those operations. Aliases are read
  from the effective repository and inline config rather than executed.
  Branch-name and identity checks carry the effective Git cwd, repository
  locations, and inline settings into their checker subprocess. They inspect
  every commit, push, and alias resolving to either operation in a chained
  command. An unknown subcommand is ambiguous only when it may be such an alias
  and its alias sources cannot be inspected.
- A command handed to a shell through another shell. Each gate reads the
  interpreter names of both, so `powershell -Command 'Remove-Item -Recurse
  -Force /etc'` reaching the Bash gate and `bash -c 'rm -rf /etc'` reaching
  the PowerShell gate both deny. POSIX, PowerShell, and CMD delete readings
  live in the shared core and are tried together.
- A command inside a PowerShell script block (`& { ... }`) or handed to a
  program through `Start-Process -ArgumentList`. Wrapper unwrapping is bounded.
  Past the bound the command denies.
- A PowerShell `EncodedCommand`, under every supported abbreviation and alias.
  Base64 and UTF-16LE decoding are strict, and decoded commands re-enter the
  bounded classifier. Missing, malformed, or over-nested payloads deny.

Editor-tool handling resolves the named target with `realpath`. It checks the
raw name, resolved name, and hard-linked test inodes. It also gates test-shaped
targets outside the project root. The shell gates instead parse command text.
Their test-path check is lexical and handles case variants, alternate data
streams, and trailing dots or spaces. Known protected-path targets are
canonicalized, but shell handling does not perform the editor gate's inode
scan. Do not infer general shell symlink, hard-link, or short 8.3 coverage.

For the destructive and consent gates, malformed top-level JSON and non-object
payloads deny. Branch and identity hooks treat malformed input as an empty
`SessionStart` payload. For applicable tools, a non-object tool input,
non-string command, or non-null non-string editor path denies. A null editor
path is treated as absent. Existing-test editor paths ask in an interactive
mode. An unrelated malformed field such as a null or numeric `old_string` does
not independently deny. An unrecognized `permission_mode` changes a gated
verdict from ask to deny. It has no effect when the call does not otherwise
need a gated verdict.

The shared reason builders apply `sanitize` to displayed Git subcommands,
permission modes, environment names, selected program and target names, editor
target basenames, and file-open errors. The function bounds text and renders
non-printable or non-ASCII characters visibly. Branch and identity
`SessionStart` warning builders sanitize checker output before placing it in
`additionalContext`. This is not a universal output guarantee. Import-error
text and checker stderr emitted by other paths remain untrusted output.

## Explicit non-goals

A repository hook is not a sandbox or authorization boundary. Anyone who can
write the repository can alter the hook source and registration.
Tamper resistance requires an external harness, filesystem isolation, or
server-side controls. This template ships none.

- A command behind an alias to a shell function, a wrapper script on `PATH`, or
  a variable holding a program name is invisible. An unknown writer, a write
  program with an unrecognized parameter shape, and a command whose program is
  hidden in a variable remain heuristic gaps. Where the shape is detectable,
  it fails closed to `ask`. Otherwise, it is not seen.
- Rate and volume analytics are out of reach. "N deletions in M minutes", and
  correlation with an anomalous login, need telemetry a per-call hook does not
  have. The gates read one command's shape.
- A tool the gates are not registered for is not gated.
- Rule 4 is not enforceable here. A hook sees the proposed action and no
  statement of scope, so it cannot separate an in-scope fix from an out-of-scope
  one.
- Content filtering is not a goal. The shared gate values listed above receive
  character rendering and length bounds. Other checker output can remain
  untrusted, and no displayed wording determines authorization.

## Modes and limits

`INTERACTIVE_MODES` lists the `permission_mode` values in which a person can
answer a gated prompt. For a gated verdict, an unrecognized value denies. This
is correct for `bypassPermissions` and incorrect for an interactive mode Claude
Code adds later. A legitimate gated action then fails closed. Review this list
when Claude Code adds a mode.

The editor-tool inode walk for hard-linked tests runs only when `st_nlink > 1`,
skips `.git`, `node_modules`, `.venv`, and `__pycache__`, and carries a budget.
Exceeding it returns an incomplete result that the caller gates conservatively.
Directory traversal and candidate stat errors also return an incomplete result
rather than clearing the write.

PowerShell coverage uses synthetic hook payloads passed to the Python
classifier. No live PowerShell tool call has been exercised.

## Coverage baseline

The suites run each gate as a subprocess, so tracing uses a `sitecustomize`
module on `PYTHONPATH` to measure function-owned statements the full suite does
not reach. The baseline records them by function and requires a reason for each
entry:

- The `_bash_parser` entries and the Bash and PowerShell parser entries retain
  malformed, missing-operand, alternate `env -S`, direct-caller, and
  maximum-depth branches that the subprocess entry points reject earlier or
  that require syntactic forms outside the regression corpus.
- The Git config and repository-discovery helpers, including
  `_apply_git_config_argument`, `_apply_git_path_argument`,
  `_environment_config`, `_parent_repository_dir`, and
  `_read_invocation_configs`, retain bounds, missing optional files, invalid
  keys, and filesystem errors. The suite exercises representative fail-closed
  classes and executable settings, but not every equivalent arm.
- The commit and push context helpers, `git_checker_environment`,
  `_alias_write_label`, `_shell_alias_write_label`, and both enforcement
  handlers retain malformed global options, alias-depth and shell-alias
  variants, absent config sources, and error-reporting arms.
- `_protected_path`, `_is_system_root`, `_mentions_device`,
  `_segment_program`, `device_write_verdict`, `forge_verdict`,
  `logging_verdict`, `mass_operation_verdict`, `posix_delete_verdict`,
  `remote_execution_verdict`, `schedule_verdict`, `unparseable_verdict`, and
  `volume_verdict` retain platform, device, mount, and uncommon program arms.
  Corpus rows exercise representative outcomes without building real devices
  or mounts.
- `read_payload`, `resolved_under`, and `sanitize` retain defensive exceptions
  or direct-caller bounds. The hook entry points reject those states earlier.
- The consent entries retain cross-drive path handling, absent path fields, and
  the top-level exception boundary. Narrow OS-boundary tests cover out-of-tree
  paths, open errors, the hard-link budget, and ordinary denial paths.

`scripts/check_hook_coverage.py` runs this in CI. It compares the run against
`hook-coverage-baseline.json`, counted per function so an edit above a function
does not churn it, and fails in both directions: a function gaining unreached
statements is new code no test reaches, and a function losing them is a
stale baseline.

Every entry in that baseline needs a reason here. An entry nobody can explain
is untested code, not a recorded one.

The baseline tool conservatively refuses to write one as root. Permission-mode
tests use real files. Narrow patches at `os.open` and `os.stat` exercise error
boundaries independently of account privileges, so Windows and Linux record
the same consent-hook branches.
