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
- A git read command (`status`, `diff`, `log`, `show`, `blame`, `grep`) in a
  repository whose own config declares a key naming a program git runs.
- A git alias, resolved from the repository config rather than executed.

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

A hook is not a sandbox.

- A command behind an alias to a shell function, a wrapper script on `PATH`, or
  a variable holding a program name is invisible. Where the shape is
  detectable, it fails closed to `ask`; otherwise it is not seen.
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

Three inputs decide whether an edit is released: the environment grant,
`.claude/settings.json`, which decides whether the hook runs at all, and the
hook's own source, which decides what it does. Whoever edits any of them before
the hook runs has already won.

Writes to `hooks/` and `.claude/` are gated, which raises the cost. It does not
remove it, and a local hook cannot be its own root of trust. The server-side
backstop is the adopting repository's to provide. This template ships none.

## Modes and limits

`INTERACTIVE_MODES` lists the `permission_mode` values a person can answer a
prompt in. An unrecognized value denies, which is right for
`bypassPermissions` and wrong for an interactive mode Claude Code adds later: a
legitimate session then fails in a way that reads as a security feature. The
deny reason names the value it did not recognize, so the cause is visible rather
than mysterious. Review this list when Claude Code adds a mode.

The inode walk that resolves hard links runs only when `st_nlink > 1`, skips
`.git` and `node_modules`, and carries a budget. Exceeding it returns `ask`. The
hook timeout is 30 seconds and a hook that times out fails open, so the walk
must end before it does.

## Keeping this current

Every finding, from any round, lands here as a covered item or as a stated
non-goal. A non-goal is recorded so it is visible to the user and the adopter,
never to argue a finding away.
