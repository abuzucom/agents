# Gate threat model

What the hooks in `hooks/` cover, and what they do not. It exists so each
review round starts from what is already known instead of rediscovering it, and
so an adopter reads the limits rather than inferring them.

This is a record, not a completion gate. An item appearing under Covered is
evidence that a case has a test behind it, never a verdict that the gates are
finished.

## Covered

A model acting through the `Bash`, `PowerShell`, `Edit`, `Write`, `MultiEdit`,
and `NotebookEdit` tools, on POSIX and Windows, attempting any of:

- A recursive delete, against any target. Drive roots, UNC share roots, and
  system directories deny; everything else asks.
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
- Any edit to a test file that already exists, through an edit tool or through
  a Bash redirect, here-document, `tee`, `sed -i`, `cp`, or `mv`.
- Known Bash and PowerShell writes to `hooks/` or `.claude/`, through redirects
  and recognized write programs. PowerShell named path and destination
  parameters accept valid unambiguous prefixes and are read independently of
  their order. Literal targets resolve directory links before classification.
  This preserves prompt consistency only. It does not protect a writable
  repository root.
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
- A git alias, resolved from the effective repository and inline config rather
  than executed. Branch-name and identity checks carry the effective Git cwd,
  repository locations, and inline settings into their checker subprocess.
  They inspect every Git write in a chained command. An unknown subcommand
  becomes an ambiguous write when its alias sources cannot be inspected.
- A command handed to a shell through another shell. Each gate reads the
  interpreter names of both, so `powershell -Command 'Remove-Item -Recurse
  -Force /etc'` reaching the Bash gate and `bash -c 'rm -rf /etc'` reaching
  the PowerShell gate both deny. The three delete readings, POSIX, PowerShell,
  and CMD, live in the core and are tried together, so neither gate can learn
  a spelling the other does not.
- A command inside a PowerShell script block (`& { ... }`) or handed to a
  program through `Start-Process -ArgumentList`. Wrapper unwrapping is bounded;
  past the bound the command denies.
- A PowerShell `EncodedCommand`, under every supported abbreviation and alias.
  Base64 and UTF-16LE decoding are strict, and decoded commands re-enter the
  bounded classifier. Missing, malformed, or over-nested payloads deny.

Path spellings that reach a covered target are covered with it: symlinks, hard
links resolved by inode, case variants on a case-insensitive filesystem,
alternate data streams, trailing dots and spaces, short 8.3 names, `\\?\`
prefixes, and paths resolving outside the project root.

Malformed and hostile payload fields are covered: a non-object tool input, a
non-string command, a null or numeric `old_string`, an unrecognized
`permission_mode`, and a payload that will not parse. Each denies at exit 2
rather than raising, because Claude Code treats any non-zero exit other than 2
as non-blocking, so a hook that crashes is a hook that is not there.

Untrusted text reaching a prompt or the model's context is rendered inert. Every
value that reaches `permissionDecisionReason`, stderr, or `additionalContext`
passes an allowlist that keeps printable ASCII and escapes everything else
visibly, then bounds the length. A denylist would miss the cases that matter:
zero-width characters, bidi overrides, and Unicode tag characters are not
control characters, and they render invisibly or reverse the text around them,
so the filename a person authorizes would not be the filename being written.
`SessionStart` warnings separate hook-authored instructions from repository data
under labeled headings, so a commit author field or a branch name cannot sit
between imperative sentences.

## Explicit non-goals

A repository hook is not a sandbox, authorization boundary, or security
boundary. Repository writers can alter the hook source and registration.
Tamper resistance requires an external harness, filesystem isolation, or
server-side controls. This template ships none.

- A command behind an alias to a shell function, a wrapper script on `PATH`, or
  a variable holding a program name is invisible. An unknown writer, a write
  program with an unrecognized parameter shape, and a command whose program is
  hidden in a variable remain heuristic gaps. Where the shape is detectable,
  it fails closed to `ask`; otherwise it is not seen.
- Rate and volume analytics are out of reach. "N deletions in M minutes", and
  correlation with an anomalous login, need telemetry a per-call hook does not
  have. The gates read one command's shape.
- A tool the gates are not registered for is not gated.
- Rule 4 is not enforceable here. A hook sees the proposed action and no
  statement of scope, so it cannot separate an in-scope fix from an out-of-scope
  one. A mechanism exists in principle: the payload carries `transcript_path`,
  and reading only the user-authored turns would preserve the isolation that
  makes a hook work. It is new capability nobody asked for, so it stays a
  proposal.
- Content filtering is declined. The untrusted values here are filenames, commit
  authors, and git config values, which have to be rendered inert rather than
  scanned for bad phrases. A keyword or fuzzy filter is a denylist over
  attacker-chosen text, and Best-of-N results show content filters fall to
  sufficient variation. A filter that loses to a persistent attacker while
  implying coverage is worse than none, because the reader of a permission
  prompt is deciding whether to authorize an act.

## Cannot be fixed from inside a hook

`.claude/settings.json` decides whether a hook runs, and the hook source decides
what it does. Whoever edits either before the hook runs controls the result.
Recognizing shell paths and prompting on known writes to those files does not
close this writable-root bypass. Only controls outside the repository can
provide tamper resistance.

## Modes and limits

`INTERACTIVE_MODES` lists the `permission_mode` values a person can answer a
prompt in. An unrecognized value denies, which is right for
`bypassPermissions` and wrong for an interactive mode Claude Code adds later: a
legitimate session then fails in a way that reads as a security feature. The
deny reason names the value it did not recognize, so the cause is visible rather
than mysterious. Review this list when Claude Code adds a mode.

The inode walk that resolves hard links runs only when `st_nlink > 1`, skips
`.git` and `node_modules`, and carries a budget. Exceeding it returns an
incomplete result that the caller gates conservatively. The hook timeout is 30
seconds, so the walk must end before it does. Directory traversal and candidate
stat errors also return an incomplete result rather than clearing the write.

## What no test reaches

The suites run each gate as a subprocess, so in-process coverage sees almost
none of the decision code. Tracing every interpreter through a `sitecustomize`
module on `PYTHONPATH` reaches them, and against the full suite it leaves 120
statements in `hooks/` unrun, out of 1,758.

Two unreachable helpers, `find_reason` and `find_consent_reason`, were deleted
after the tracing pass showed that neither repository called them.

The baseline entries fall into these recorded groups:

- The `_bash_parser` entries and the Bash and PowerShell parser entries retain
  malformed, missing-operand, alternate `env -S`, direct-caller, and
  maximum-depth branches that the subprocess entry points reject earlier or
  that require syntactic forms outside the regression corpus.
- The git-read helpers from `_environment_config` through
  `_read_invocation_configs` retain bounds, malformed pointer files, missing
  optional files, invalid keys, and filesystem errors. Tests cover each
  fail-closed class and every executable setting, but not every equivalent arm.
- The git-write context helpers, `git_checker_environment`,
  `_alias_write_label`, and both enforcement handlers retain malformed global
  options, alias-depth and shell-alias variants, absent config sources, and
  error-reporting arms. Real subprocess tests run the effective-repository,
  inline-identity, configured-alias, and inline-alias paths.
- `_protected_path`, `_is_system_root`, `_mentions_device`,
  `_segment_program`, `device_write_verdict`, `forge_verdict`,
  `logging_verdict`, `mass_operation_verdict`, `posix_delete_verdict`,
  `remote_execution_verdict`, `schedule_verdict`, `unparseable_verdict`, and
  `volume_verdict` retain platform, device, mount, and uncommon program arms.
  Corpus rows cover their classifier outcomes without building real devices or
  mounts.
- `read_payload`, `resolved_under`, and `sanitize` retain defensive exceptions
  or direct-caller bounds. The hook entry points reject those states earlier.
- The consent entries retain permission-dependent filesystem errors, alternate
  out-of-tree path explanations, absent path fields, and the top-level
  exception boundary. The hard-link budget and ordinary denial paths run.

`scripts/check_hook_coverage.py` runs this in CI. It compares the run against
`hook-coverage-baseline.json`, counted per function so an edit above a function
does not churn it, and fails in both directions: a function gaining unreached
statements is new code no test reaches, and a function losing them is a
baseline going stale. The second matters as much as the first. A recorded limit
nobody maintains stops being a limit and becomes a place to hide.

Every entry in that baseline needs a reason here. An entry nobody can explain
is untested code, not a recorded one.

The baseline is measured in CI, and the tool refuses to write one as root. A
mode 000 file is readable for root, so the two `OSError` branches in
`require_consent.py` that a permission denial would take never fire in a root
shell and do fire for an ordinary user. A baseline written as root records
fewer unreached statements than CI finds and fails the check it exists to
satisfy.

That difference also means `test_unreadable_test_file_is_gated` passes without
testing what it names when the suite runs as root: the file it chmods to 000
stays readable, so the ordinary path runs and the assertion holds for the wrong
reason. The gate surfaced it; whether to change the test is the maintainer's
call under Rule 3.

## Keeping this current

Every finding, from any round, lands here as a covered item or as a stated
non-goal, and in `tests/gate_corpus.py` as a row carrying the reason it exists.
A round's findings arrive as data rather than as another test class nobody
rereads, and both repositories import the same corpus, so a fix landing in one
and not the other fails the other's suite.

A non-goal is recorded so it is visible to the user and the adopter, never to
argue a finding away.
