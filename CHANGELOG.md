# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
with one deviation: a version heading parenthesizes its date,
`## [1.2.3] (2026-01-01)`, rather than setting it off with a spaced hyphen.
The house style bans that hyphen and `scripts/check_ascii.py` enforces the ban
on this file.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.13.0] (2026-08-25)

### Added
- Denied anything piped into an interpreter, not only a download. `history | sh` hands the choice of what runs to whatever the shell happens to remember, and `cat script.sh | bash` runs a file nobody read. Piping into a reader such as `grep`, `jq`, `less`, or `tee` is untouched.
- Denied `crontab -r`, which removes every scheduled job at once with no copy kept and no prompt from crontab itself, and `schtasks /delete`. Denied the filesystem repair tools (`fsck`, `e2fsck`, `xfs_repair`, `chkdsk`, `ntfsfix`), which rewrite metadata in place and can discard what they cannot reconcile.
- Denied `gh repo delete` and its equivalents for releases, gists, and organizations, across `gh`, `glab`, `hub`, and `tea`. These remove work no local clone holds, and no local action undoes them. Read-only forge commands are untouched.
- Routed `git branch -D` to the user: it discards a branch whose commits may not be merged anywhere else. `git branch -d`, which refuses an unmerged branch, is untouched. Case carries the meaning here, so the check does not lowercase before reading it.
- Denied defining a command alias (`alias`, `Set-Alias`, `doskey`, `git config alias.x`). An alias makes one name run another command, which defeats reading a command to know what it does. Listing aliases is untouched.
- Denied `hdparm` and the other drive-firmware tools, a bare redirect (`> file`), a redirect from an empty device (`cat /dev/null > file`), and any redirect onto a device (`> /dev/sda`). Each empties or overwrites its target without a delete appearing anywhere in the line.
- Denied a recursive `chmod`, `chown`, or `chgrp` across a root or system directory, which breaks every program depending on those permissions. The same command inside a project is untouched.
- Routed writes to a shell startup file to the user: `.bashrc`, `.zshrc`, `.bash_profile`, `.zshenv`, `.profile` and the rest, whether through a redirect or through `sed -i`, `cp`, `mv`, or `tee`. A line added to one runs at the start of every future session. Reading one is untouched.
- Routed `kill`, `killall`, `pkill`, and `taskkill` to the user. What a termination stops, and what that loses, is not something a gate can weigh.
- Added data-destruction detection to the shared core, covering the command forms in the MITRE ATT&CK T1485 family (DET0146). Denied outright: filesystem formatting (`mkfs`, `diskpart`, `format`, `fdisk`, `parted`, `wipefs`); `dd` in every form; a download piped into an interpreter (`curl | bash`, `wget -qO- | sh`), because the remote host chooses what runs and nothing reads it first; `mv` to `/dev/null`, `/dev/random`, or `/dev/zero`, which is a delete that reads as a move; `chmod 000` and its symbolic equivalents; recovery destruction (`vssadmin delete shadows`, `wmic shadowcopy delete`, `wbadmin delete`, `bcdedit` recovery flags); and a glob rooted at a system directory. Routed to the user: `shred` and `sdelete` on a file, `find -delete` and `-exec`, `git clean -xfd`, `sed -i` and `truncate` over a glob, recursive acts under a mount point or shared temp directory, and logging disablers such as `aws cloudtrail stop-logging` and `auditctl -D`.
- Routed every `sudo`, `su`, `doas`, `pkexec`, and `runas` invocation to the user, whatever it wraps. Running as another user is a decision about authority rather than about the command, so it is asked for on its own terms and the wrapped command is judged separately: `sudo ls` asks, `sudo rm -rf /` still denies.
- Derived the fail-closed keyword list from the core's own program sets. It was hardcoded to `rm` and `git`, so a command that would not tokenize and named anything else, `cipher /w:C:\\` among them, was waved through by the path meant to fail closed.
- Added `repo_executes_on_read` to `_gate_core.py`, which routes `git status`, `diff`, `log`, `show`, `blame`, and `grep` to the user when the repository's own config declares a key naming a program git runs: `diff.external`, `filter.<driver>.clean`, `log.showSignature`, `core.fsmonitor`, `core.sshCommand`, `core.hooksPath`, and the rest. It reads `.git/config` as a file rather than asking `git config`, because running git to decide whether running git is safe is the bug. A repository declaring none of them prompts on nothing, and a command that clears the key with `-c key=` passes.
- Resolved git aliases from the same parse. `git myalias` read as an unknown subcommand and passed; its expansion is now classified. An alias beginning with `!` is a shell command, so it is reported rather than expanded or run, and a subcommand that is neither known nor a declared alias asks.
- Added `hooks/block_destructive_powershell.py`, registered under a `PowerShell` matcher in both settings files. The Bash matcher covered only Bash, so `Remove-Item -Recurse -Force` on a Windows session met no gate at all. Every decision comes from `_gate_core.py`, which the Bash gate also imports, so only the parsing is shell-specific: statement boundaries, the call operator and the cmdlets that run another command, PowerShell's redirection forms, and `Remove-Item` with its aliases. PowerShell parameters abbreviate to any unambiguous prefix, so `-Recurse`, `-Rec`, and `-r` are one switch, matched case-insensitively. Verified against synthetic payloads only.
- Added `tests/test_gate_parity.py`, which feeds both gates an equivalent corpus and fails when their verdicts differ. It also asserts that neither gate defines a decision function of its own, so a fix cannot land in one and miss the other. Parity is otherwise a promise, and this repository has already watched `check_commit_message.py` diverge between two copies undetected.
- Added `hooks/require_consent.py`, a Claude Code hook backing Rule 3 from the harness. The only unprompted edit to an existing test file is a verified append at the end of it: the new text must begin with the old text, the addition must start on a new line, and the old text must sit at the end of the file. An earlier form of this check asked only whether the old text still appeared somewhere in the new text, which passed an assertion that had been commented out, wrapped in a string, moved into a branch that never runs, or extended on the same line. On `PreToolUse` (`Edit|Write|MultiEdit|NotebookEdit` matcher) it routes an edit that removes or rewrites existing test content, drops an assertion, or introduces a skip marker to the user as a permission prompt. A new test file passes, and so does an append to an existing one, detected by the old string surviving verbatim inside the new one, so the mandated test-first workflow stays unprompted. On `SessionStart` it states which gates are live and carries the checklist a question must satisfy before it is written. The checklist sits there rather than on an `AskUserQuestion` matcher because a `PreToolUse` hook sees a question whose options are already written, and `additionalContext` cannot rewrite them.
- Added an `AGENTS_CONSENT_GRANTED` environment variable for headless runs, releasing only the paths a human names at launch, compared on the canonical path. Paths are resolved before classification, so a symlink with an innocuous name cannot carry an edit into a test file. Any test file resolving outside the project root is gated, whether a link redirected it there or the caller named it directly. An earlier form classified the unresolved string and matched grants by path suffix, so one grant for `tests/test_auth.py` released every file whose path ended the same way. A Bash tool call cannot set it, since shell state does not persist between calls and the hook inherits Claude Code's environment.
- Added `tests/test_require_consent.py`, 19 stdlib `unittest` tests running the hook against synthetic payloads and real files on disk. Covers the additive cases, the gated cases, notebook paths, the fail-closed behavior under an unattended `permission_mode`, the override variable, the question checklist, and whether both settings files register the hook for each event.
- Added `tests/test_block_destructive_bash.py`, pinning every deny, ask, and allow outcome of the Bash gate.
- Added a per-act consent line to the Non-negotiable preamble: approving a plan, a design document, or a task description is not authorization for the individual acts inside it.
- Added a Rule 3 paragraph stating that disclosure is not a substitute for stopping, that a comment recording why a test asserts what it asserts is a person's decision written down, and that a deliberate specification change is still the human's call.
- Added a Rule 2 line stating the rule carries no scope qualifier, so a scratch directory the session created itself is gated like any other target.
- Added a pushed-history line stating that `--force-with-lease` is not an exception and neither is a branch you created minutes ago.
- Added Adopting steps 12 through 14 to `README.md`, covering the consent gate, the two shell gates, and a drift record. The list ended at 11 and named neither gate, so a repository could adopt this file and never learn the hooks existed. Step 12 states the failure mode that decides whether the copy is safe: a gate copied without `hooks/_gate_core.py` cannot import it, and a hook that fails to start exits non-zero but not 2, which Claude Code treats as non-blocking, so the gate fails open in the one repository that installed it.
- Added copy instructions to Rules 2 and 3, in the shape Rule 14 and the branch-naming section already use: which files to copy, which matcher registers them, which suite comes with them, and the Rule 9 reminder that a hook is tooling the user approves first.

### Changed
- Rewrote Rule 2 to state the procedure a destructive command follows and to describe what the gates actually enforce. The rule claimed only that `rm -rf` aimed at `/`, `~`, or `$HOME` denies and everything else asks, which had become a large understatement: the refusal list now runs to system directories, formatting and repair tools, `dd`, `hdparm`, truncating redirects, pipes into interpreters, alias definitions, `crontab -r`, recovery destruction, and `gh repo delete`. Rule 13 cuts both ways, and a rule that understates its enforcement misleads an adopter as surely as one that overstates it.
- Added four procedural requirements to Rule 2: do not guess at what a command affects, propose a non-destructive alternative first, restate the command and wait for confirmation after authorization, and record the text that authorized it. Marked plainly as instructions rather than checks: no mechanical signal distinguishes a restatement from any other sentence.
- Changed `git push --force` and `-f` from a refusal to a permission prompt, at the user's direction. A refusal offers no way to consent, and the pushed-history rule is about requiring consent rather than making the act impossible. An unattended session still denies, since consent cannot be given there.
- Denied a `chmod`, `chown`, or `chgrp` targeting a root or system directory whether or not it recurses. `chown nobody /etc` breaks the machine with no `-R` anywhere in the line.
- Normalized POSIX root paths with `posixpath` rather than `os.path`. On Windows `os.path.normpath("/etc")` returns `\\etc`, so the check anchored on a leading slash rejected every POSIX system root on the one platform where it mattered: `/etc`, `/usr`, and `/Applications` asked instead of denying. The `windows-latest` job caught it, and a regression test now substitutes `ntpath` so the same class is covered from Linux.
- Denied rather than asked for the deletion of a drive root, a UNC share root, or a system directory: `/`, `/bin`, `/boot`, `/dev`, `/etc`, `/home`, `/lib*`, `/media`, `/mnt`, `/opt`, `/proc`, `/root`, `/run`, `/sbin`, `/srv`, `/sys`, `/tmp`, `/usr`, `/var`, and the macOS equivalents. Offering that choice is not consent, it is an invitation to a mistake nobody can undo. A path inside one is an ordinary recursive delete and still asks. Paths normalize first, so `/usr/.`, `/etc//`, and `/home/..` reach the same verdict as the directory they name.
- Denied an unparseable command that names a root. `rm -rf C:\\` ends in an unterminated escape and previously asked; no reading of it is a decision to put to a person.
- Skipped the two symlink fixtures with a recorded reason where the platform needs elevation to create a link. Windows raises `WinError 1314` without Developer Mode, so an unconditional fixture failed the suite for an ordinary contributor. The hard-link fixture covers alias resolution and needs no privilege.
- Routed Bash writes that reach a test file through the same consent decision as an `Edit`: a redirect, a here-document, `tee`, `sed -i`, `cp`, and `mv`. Rule 3 applied to the same act through one tool and not the other, and #134 recorded the redirect as a known gap. Reading or running a test is untouched.
- Moved the test-path classifier into `_gate_core.py`, so the consent gate and the shell gates decide from one definition instead of two.
- Classified the command a shell is handed rather than the shell's own name. `bash -c 'rm -rf /tmp/x'` and `sh -c` read as the program `bash` and passed. The payload after `-c` is now classified as a nested command, for `bash`, `sh`, `zsh`, `dash`, `ksh`, `busybox`, and `cmd`, including combined short groups such as `-lc`. A shell invoked without a command string is not gated on its own name.
- Added the CMD deletion verbs `del`, `erase`, `rd`, and `rmdir` to the shared classifier, with slash-prefixed case-insensitive flags. No CMD tool matcher exists, so those verbs arrive nested inside a shell call. `%USERPROFILE%` and `%HOMEPATH%` join the root targets that deny.
- Separated instructions from data in both `SessionStart` warnings. Each spliced checker output into the middle of an imperative block sent to the model as `additionalContext`, and that output carries commit author and committer fields, which whoever wrote a commit chooses. A commit authored as an address followed by a newline and a correction could write instructions into the context the hook exists to make the model obey. Fixed text now sits above a single labeled `REPOSITORY_DATA` block holding every untrusted value, each escaped and on its own line.
- Removed the end-of-file append carve-out from `hooks/require_consent.py`. Every edit to a test file that already exists now asks, in any language; creating a new one is the only exemption left. A textual append check cannot carry the claim it made: appending `ExistingTest.__unittest_skip__ = True`, or rebinding the class to `None`, leaves every assertion above it present and inert, and enumerating those spellings is a denylist over text an attacker chooses. The cost is real and accepted: iterating on an existing test now prompts.
- Wrapped the gate's entry point in an exception boundary that denies and exits 2. A non-string `old_string` raised an uncaught traceback and exited 1, which Claude Code treats as non-blocking, so the edit proceeded ungated. The boundary emits a fixed reason rather than the traceback, keeping internal paths out of the prompt.
- Matched test paths case-insensitively and stripped Windows filename decorations before matching. `Tests/Test_Auth.py`, `SPEC/thing.SPEC.JS`, an alternate data stream (`test_x.py:evil`), and a trailing dot or space each reach a test file while failing the previous pattern.
- Compared paths against the project root with `os.path.commonpath` instead of a string prefix, so a Windows short name or a `\\?\` prefix cannot spell its way out of the tree.
- Resolved hard links by inode against the project's test tree. `realpath` resolves a symlink because a symlink has a target; a hard link has none, so a test could be edited through a name that looks like anything. The walk runs only for files with more than one link and stops at a bounded number of entries, since a gate that exceeds the hook timeout fails open.
- Bound each `AGENTS_CONSENT_GRANTED` entry to the content it was written for, as `path@sha256:<digest>`. A path-only grant released every future edit to that file for the life of the session.
- Gated writes to `hooks/` and `.claude/`, which decide whether the gates run at all. The docstring no longer claims the variable cannot be forged: whoever edits this hook or its settings before it runs decides what it does, and closing that needs a server-side check an adopting repo supplies.
- Rendered every value reaching a permission prompt or stderr as printable ASCII through `_gate_core.sanitize`. A filename carrying newlines or terminal control rewrote the prompt the user reads to decide, and stderr on a deny reaches the model as tool output.
- Canonicalized the checker path in `hooks/enforce_branch_name.py` and `hooks/enforce_git_identity.py` before executing it, and required it to resolve inside the project root. Both joined a payload-supplied directory with a fixed relative path and ran the result.
- Named the unrecognized `permission_mode` in the deny reason, so a mode Claude Code adds later is visible rather than silently denied.
- Consolidated the payload readers into `_gate_core.read_payload`, whose `empty_is_session_start` flag carries the one behavior that differed between the four copies.
- Launched every hook as `python` rather than `python3` in both settings files. Claude Code spawns the exec form directly with no shell, and Windows has no `python3.exe`, so every gate failed to start there. A startup failure exits non-zero but not 2, which Claude Code treats as a non-blocking error, so the gates failed open on that platform in silence. Debian without `python-is-python3` needs the opposite value; the new test names both.
- Added a wiring test asserting `shutil.which()` resolves the launcher string configured in both settings files. The behavioral tests run hooks through `sys.executable`, so they passed against a configuration that never started.
- Added a `windows-latest` job to `.github/workflows/sync-check.yml`. No Linux job can show that the configured launcher resolves on Windows, that the symlink fixtures skip instead of erroring, or that path handling holds on a case-insensitive filesystem.
- Excluded merge commits from `scripts/check_commit_message.py`. `git merge` writes `Merge branch 'x' into y`, which no author chose and which no `type: description` subject can express, so every ordinary branch update failed the check. Added `tests/test_check_commit_message.py`, which builds a throwaway repository and covers the merge case, a real violation, and the advisory exit code.
- Registered every hook in the exec form (`command` plus `args`) instead of a shell string. In shell form an unquoted `${CLAUDE_PROJECT_DIR}` splits a project path containing a space, so `python3 /My Project/hooks/require_consent.py` fails to open `/My`, and the gate silently never runs.
- Made both hooks fail closed on their own inputs. A payload that will not parse, or a `tool_input` that is not an object, is denied instead of being treated as a SessionStart or crashing; Claude Code treats any non-zero exit other than 2 as a non-blocking error, so an unhandled exception waved the command through. A test file that cannot be read or decoded is gated instead of reading as an empty string, which had let a non-UTF-8 test file be overwritten with no prompt.
- Rewrote `hooks/block_destructive_bash.py` to tokenize and normalize the command before deciding, and extended it from a single deny outcome to deny plus ask. The previous string matcher missed every equivalent spelling of the commands it named: `rm -Rf` and `rm -r`, `git -C dir push --force` and other global-option forms, `--force-with-lease=main:<oid>`, a forced `+` refspec, and `git push --mirror`. One of those, `git -C dir push --force`, bypassed a deny rather than an ask. Ambiguity now fails closed: a command that will not tokenize, or a git subcommand hidden behind a variable, is gated. The four previously denied commands still deny and still exit 2. Newly routed to the user: `rm -rf` against any target other than `/`, `~`, or `$HOME`; the `--force-with-lease` and `--force-if-includes` family, which the old `--force` pattern never matched; `git push --delete`; `git commit --amend`; `git rebase`; and `git filter-branch`. An unrecognized or unattended `permission_mode` turns an ask into a deny.
- Wired `block_destructive_bash.py` into `.claude/settings.json`. It had been example-only since 1.11.0, so nothing in this repo ran it.
- Replaced `test_pre_tool_use_entries_target_bash` in `tests/test_enforce_branch_name.py` with a per-hook wiring table asserting that each hook is registered under exactly the matchers it needs, plus a check that every registered hook appears in the table. The blanket assertion that every `PreToolUse` matcher equals `Bash` could not survive a hook that gates `Edit`. Replaced on the user's explicit sign-off, per Rule 3.
- Corrected the Rule 3 enforcement sentence, which still described the removed end-of-file carve-out. It told an adopter that appending to an existing test file is not gated, and that the gate reads content for removed assertions and skip markers. Neither has been true since the carve-out came out: the gate reads the path, and every edit to a test file that already exists asks.
- Backported three files the adopting repository had already improved past this template. `check_ascii.py` and `lint_style.py` name the `127` boundary `MAX_ASCII_CODEPOINT`, and `check_english_only.py` drops `para` from the Portuguese stopword list, where the Spanish list above it already carries the word. `sync.py` covers only the AGENTS.md family, so nothing reported the drift; it was found by comparing the two repositories by hand, which is the case for the drift record in Adopting step 14.
- Added `docs/gate-threat-model.md`, recording what the gates cover and what they do not: the tools and command classes they see, the path spellings that reach a covered target, the malformed payload fields that deny rather than crash, and the untrusted text that reaches a prompt inert. It also states the non-goals plainly. A hook is not a sandbox, it cannot see a command behind an alias or a wrapper script, it has no telemetry for rate analytics, and it cannot enforce Rule 4 because it sees no statement of scope. A non-goal is recorded so an adopter reads the limit rather than inferring it, never to argue a finding away.
- Added `DRIFT.md` and `adopters/1a2n-web-visualizer.md`. `sync.py` covers the AGENTS.md family and nothing else, so every `scripts/`, `hooks/`, and `tests/` file is copied by hand and maintained in the adopting repository, where a local edit is invisible from here. `DRIFT.md` states the three categories and which of the three files owns which field; the adopter file records the adopted-at commit and what that repository took versus declined. Nothing verifies either, and both say so.
- Named the unrecognized `permission_mode` in the deny reason emitted by `_gate_core.decide`, which both shell gates use. `INTERACTIVE_MODES` is a fixed list, so an interactive mode Claude Code adds later denies here, and the reason read identically to a genuinely unattended session. A missing or non-string mode reads `absent` rather than `None`. The mode is payload text, so it renders through the same allowlist as every other untrusted value.
- Rewrote the README hook sections, which described gates two revisions old: two hooks where there are three, `git push --force` as a refusal after it moved to a prompt, the append carve-out as live after it came out, and the Bash redirect as an open gap after the shell gate closed it. The deny and ask lists now live only in rule 2; a second copy is a second thing to disagree with.
- Added `tests/gate_corpus.py`, one table of every known gate bypass with the verdict it must reach and the reason the row exists, imported by the Bash, PowerShell, and consent suites. Writing it found five more bypasses in an afternoon, which is the argument for it: each gate knew only its own shell's interpreters, so `powershell -Command 'Remove-Item -Recurse -Force /etc'` crossed the Bash gate and `bash -c 'rm -rf /etc'` crossed the PowerShell gate, both untouched; a PowerShell script block (`& { ... }`) put a brace where a program name goes and was read as a program named `{`; and `Start-Process -ArgumentList` handed a CMD line to a program without any payload flag the gate recognized.
- Moved all three delete readings, POSIX `rm`, PowerShell `Remove-Item`, and the CMD verbs, into `_gate_core.py`, along with the interpreter and payload-flag sets. Both gates now try all three readings and take the strongest, so neither can learn a spelling the other does not. Wrapper unwrapping is bounded; past the bound a command is unparseable, which prompts rather than passes.
- Added `scripts/sync.py --check-shared` and `--write-shared`, backed by `shared-files.json`: SHA-256 digests of the seven files carrying gate decisions, committed in every repository holding them. `sync.py` copies the AGENTS.md family and can copy nothing that lives in another repository, so the gates are compared rather than copied. A file changed in one repository and not another fails that repository's check, which runs in CI. Line endings are normalized before hashing so a Windows checkout does not report every file as drift. Covered by `tests/test_sync_shared.py`, which builds a synthetic tree rather than touching the real one.
- Fixed a crash in the PowerShell gate's `-ArgumentList` handler, which called `unparseable_verdict` with one argument against a two-parameter function. A payload that would not tokenize raised `TypeError` instead of denying, and a raise is a non-zero exit that is not 2, which Claude Code treats as non-blocking: the gate failed open on exactly the input it exists to catch. The corpus carries the case.
- Brought every hook and script under the adopting repository's ruff ruleset, which is stricter than anything this template runs: named seven magic values, split `git_verdict` into resolution, per-subcommand, and flag readings, and split the three `_program_verdict` functions so each returns at most six times. The shared files have to be byte-identical across both repositories, so the stricter of the two rulesets is the only stable state for them.
- Pointed `check_ascii.py` at this repository's own prose in CI, and fixed what it found: 21 spaced hyphens in `README.md` and 17 in `CHANGELOG.md`. The checker had been wired to the example files only, so the template failed the rule it ships. README bullet definitions now use a colon, and a version heading parenthesizes its date, `## [1.2.3] (2026-01-01)`, which the CHANGELOG header records as a deliberate deviation from Keep a Changelog. `DRIFT.md`, `docs/`, and `adopters/` are covered from the start.
- Closed three false positives in `check_ascii.py` and `lint_style.py`, each a place the checker read syntax or data as prose. A Markdown table delimiter row (`| --- | --- |`) tripped the dash rule; so did a list marker opening its own line (`   - Set the width`); and an inline code span opening on one line and closing on the next leaked its contents, because pairing backticks within a line pairs the wrong ones. The last one matters most: it flagged a preset name carrying a spaced hyphen in an adopter's changelog, where rewriting it would have falsified the record of which preset was removed. Backtick state now carries across lines, and the table and marker exclusions apply to the dash rule alone rather than blinding the em-dash and non-ASCII checks on the same line.
- Added `tests/test_check_ascii.py`, 13 tests. Six of them pin what the rule still catches, since a fix to a linter's false positives is one edit away from a fix to its true ones.
- Removed `find_reason` and `find_consent_reason` from the Bash gate. Both were defined and called by nothing, in either repository, and a reachability pass over the whole suite is what found them.
- Covered the digest-bound form of `AGENTS_CONSENT_GRANTED`, which no test had ever run. The bare `path` grant was covered; `path@sha256:<digest>` was not, so the binding the gate's docstring promises had never been shown to hold. Four tests now cover it, including a stale digest and a digest belonging to another file.
- Recorded the reachability pass in `docs/gate-threat-model.md`: what no test reaches, and why each remaining statement is defensive depth or an environment the suite does not build rather than a gap.
- Added `scripts/check_hook_coverage.py` and `tools/hook-trace/sitecustomize.py`, run in CI. The gates execute as subprocesses, so ordinary in-process coverage sees almost none of their decision code and reports the opposite of the truth; Python imports `sitecustomize` in every interpreter it starts, which is the stdlib way to reach them. The run is compared against `hook-coverage-baseline.json`, counted per function so an edit above a function does not churn it.
- Made that gate fail in both directions. A function gaining unreached statements is new code no test reaches. A function losing them is a baseline going stale, which fails too: a recorded limit nobody maintains stops being a limit and becomes a place to hide. Both directions are proven end to end, not only unit tested.
- Added `tests/test_check_hook_coverage.py`, 13 tests over the comparison and the statement accounting. It does not run the gate end to end, because the gate runs the suite and a suite that runs itself does not terminate.
- Fixed a bootstrap deadlock in the coverage gate, found by installing it a second time. `--write-baseline` runs the suite, and the suite asserted the baseline exists, so the first baseline could never be produced. The baseline tests now skip when there is none. CI still fails on a missing baseline, through the gate rather than the suite.
- Renamed the tracer directory from `tools/coverage` to `tools/hook-trace`. `coverage/` is one of the commonest `.gitignore` entries, and it silently excluded the file from the adopting repository's commit. The gate then reads no traced lines and reports every statement as unreached, so the failure arrives as a wall of noise rather than as the missing file it is. Any adopter with that line would have hit it.
- Made the coverage gate refuse to write a baseline as root, and say so when it disagrees there. A mode 000 file is readable for root, so the two `OSError` branches in `require_consent.py` that a permission denial takes never fire in a root shell. The first baseline was written in one and failed CI, which measures as an ordinary user. The baseline now holds CI's values.
- Synced the AGENTS.md additions into all eight tool copies.

## [1.12.0] (2026-08-20)

### Added
- Added AGENTS.md Rule 14, "Verify the git identity before the first commit", and a matching item 14 in the Non-negotiable summary. The rule requires checking `git config user.name` and `user.email` before the first commit of a session, states that git does not inherit the `gh` identity, restricts commit emails to GitHub noreply addresses, and refers a wrong identity already in history to the existing pushed-history consent rule instead of a rewrite.
- Added `scripts/check_git_identity.py`, a portable blocking checker with three modes: no arguments checks the identity the next commit would use, reading the environment variables git treats as explicit before `user.name` and `user.email`; `--unpushed` checks commits absent from every remote-tracking ref; `--base`/`--head` checks a pull request range. `--allow` takes a regex for repos on another convention, and `--advise` adds `gh` and `user.useConfigOnly` notes that never change the exit code.
- Added `hooks/enforce_git_identity.py`, a Claude Code hook backing Rule 14 from the harness. On `SessionStart` it runs the checker with `--advise` and injects a stop-and-ask instruction into the session context; on `PreToolUse` (`Bash` matcher) it exits 2 on a `git commit` under an unset or disallowed identity, and on a `git push` when either the current config or any commit that push would publish fails. `git config` is never blocked.
- Added `tests/test_enforce_git_identity.py`, 42 stdlib `unittest` tests running the hook and the checker against a throwaway git repo, so results do not depend on the identity configured on the machine running them. Covers both events, unset and disallowed identities, environment-supplied identities, the `git config` escape hatch, the `--unpushed` path, GitHub's squash-merge committer, `[bot]` addresses, and whether both settings files still register the hook for each event.
- Added both `enforce_git_identity.py` entries to `.claude/settings.json` and `hooks/claude-code-settings.example.json`, inside the existing `Bash` matcher.
- Added a `check-git-identity` pre-commit hook and a `check-unpushed-identity` pre-push hook to `.pre-commit-config.yaml`, a "Check commit identities" step to the `pr-checks` job in `agents-compliance.yml`, and an `identity` target to the Makefile.
- Added a README "Git identity enforcement (live)" subsection under Claude Code hooks, a "Git identity outside this repository" section covering the machine, account, and organization settings a repository file cannot reach, and Adopting step 11.

### Changed
- Widened the `hook-tests` pre-commit `files` pattern to cover `scripts/check_git_identity.py`.
- Updated the README critical-rule count to fourteen, the `hooks/` and `tests/` bullets, the Local checks table, and the Checker reference table.
- Synced the AGENTS.md Rule 14 addition into all eight tool copies.

## [1.11.0] (2026-08-17)

### Added
- Added `hooks/enforce_branch_name.py`, a Claude Code hook backing the Branch naming conventions section from the harness instead of the model's memory. On `SessionStart` it runs `scripts/check_branch_name.py` before the session does any git work and injects a stop-and-rename instruction into the session context; on `PreToolUse` (`Bash` matcher) it exits 2 on a `git commit` or `git push` while the branch name is non-conforming.
- Added `.claude/settings.json`, wiring `enforce_branch_name.py` into both events for this repo. `block_destructive_bash.py` stays opt-in and is not wired up.
- Added both `enforce_branch_name.py` hook entries to `hooks/claude-code-settings.example.json`, alongside the existing `block_destructive_bash.py` entry.
- Added a README "Branch-name enforcement (live)" subsection under a renamed "Claude Code hooks" section, splitting the live branch hook from the opt-in destructive-Bash example.
- Added two paragraphs to AGENTS.md's Branch naming conventions section: a harness-assigned or dispatcher-assigned branch name is not an exception and gets renamed before the first commit, and adopting repos wire the branch check in (pre-push hook, plus the two Claude Code hook events) in the same change that adds AGENTS.md.
- Added README Adopting step 10 covering that wiring.
- Added `tests/test_enforce_branch_name.py`, 22 stdlib `unittest` tests covering both hook events, the `git branch -m` escape hatch, read-only git commands, non-Bash tools, empty and malformed stdin, an absent checker, and whether `.claude/settings.json` and `hooks/claude-code-settings.example.json` still register the hook for each event. No new dependency.
- Added a `test` target to the Makefile, a "Run tests" step to `sync-check.yml`, and a `hook-tests` pre-commit hook scoped to `hooks/`, `tests/`, `.claude/settings.json`, and `scripts/check_branch_name.py`.
- Added a README "Local checks" section listing the four make targets, a `tests/` bullet under "What's in it", and test coverage detail under Branch-name enforcement.
- Added an AGENTS.md paragraph requiring adopting repos to copy the hook's test suite and run it in CI and pre-commit.

### Changed
- Updated the README `hooks/` bullet and `check_branch_name.py` Checker reference row for the new hook, and corrected the claim that this repo has no `.claude/` directory.
- Synced the AGENTS.md branch-naming additions into all eight tool copies.

## [1.10.0] (2026-08-15)

### Added
- Added `CONTRIBUTING.md.example`, an opt-in, self-contained contribution guide for human contributors, covering setup, naming/comment conventions, security and review practices, code quality, and workflow, each item drawn from an explicit item-by-item review of AGENTS.md's rules.
- Added `.github/PULL_REQUEST_TEMPLATE.md` (live), formalizing the Summary/Test plan PR shape used throughout this project's history.
- Added `.github/ISSUE_TEMPLATE.md` (live), a single legacy-format template covering both bug reports and rule/template proposals.
- Added a README "Contributing guide example" section and Adopting step 9 documenting the new template.
- Extended `check_us_spelling.py`, `check_english_only.py`, `check_hedging.py`, and `check_ascii.py` in `sync-check.yml` to also scan all three new files.

## [1.9.0] (2026-08-15)

### Added
- Added `SECURITY.md.example`, an opt-in vulnerability-reporting policy template routing reports through GitHub's private vulnerability reporting, conforming to AGENTS.md's Style section throughout.
- Added a `## Security` line to AGENTS.md's commented-out orientation template, pointing at `SECURITY.md.example`.
- Added a README "Security policy example" section and Adopting step 8 documenting the new template.
- Extended `check_us_spelling.py`, `check_english_only.py`, `check_hedging.py`, and `check_ascii.py` in `sync-check.yml` to also scan `SECURITY.md.example`.

## [1.8.0] (2026-08-15)

### Added
- Added `plan/HANDOFF.md.example`, an opt-in per-repo handoff/progress template pairing every status claim with a command that verifies it, conforming to AGENTS.md's Style section throughout.
- Added a `## Handoff` line to AGENTS.md's commented-out orientation template, pointing at `plan/HANDOFF.md.example`.
- Added a README "Handoff file example" section and Adopting step 7 documenting the new template.
- Extended `check_us_spelling.py`, `check_english_only.py`, and `check_hedging.py` in `sync-check.yml` to also scan `plan/HANDOFF.md.example`.
- Added a `check_ascii.py` step to `sync-check.yml`'s `check-sync` job, covering `plan/HANDOFF.md.example`'s dash/ASCII conformance.

## [1.7.3] (2026-08-15)

### Added
- Added AgentLint (`0xmariowu/AgentLint@v1.1.13`) to `sync-check.yml`'s `check-sync` job, an advisory, third-party AI-agent-harness audit, pinned to an exact tag with `fail-below: '0'` so it never fails the job.
- Added a `pull-requests: write` permission and an `actions/github-script@v9.0.0` step posting AgentLint's score as an upserted PR comment (find-and-update via a marker HTML comment, not a new comment per push).
- Added a README bullet documenting AgentLint's integration, separate from the Checker reference table since it is a third-party action, not a portable `scripts/check_*.py` checker.
- Added `format: md`/`output-dir` to the AgentLint step and a report-reading step, embedding the full generated report in a collapsible section of the PR comment below the score table.

## [1.7.2] (2026-08-15)

### Added
- Added a Style rule banning hedging qualifiers, self-justification, self-narration, prompt/task/plan references, tutorial-mode narration, and justification theater in prose, documentation, CHANGELOG entries, and code comments.
- Extended the "Comment the why" rule to ban historical narration in comments (referencing removed code or prior implementations); git history covers that.
- Added `scripts/check_hedging.py`, a portable, warning-only heuristic checker backing both rules above, matching phrase lists plus generic filler comment openers (`# Note:`, `# This function`, `# Handle errors`, etc.).
- Added a `check_hedging.py` step to `sync-check.yml`'s existing `check-sync` job, with no new job or checkout/setup-python cost.
- Added a `check_hedging.py` row to the README Checker reference table.

### Fixed
- Synced all tool rule copies with `AGENTS.md`.

## [1.7.1] (2026-08-15)

### Added
- Added a Branch naming rule banning `claude/`-prefixed branches by name, so a model cannot rationalize past an implicit "match one of these five prefixes" statement.
- Added a Branch naming exemption for automated dependency-update tools (Dependabot): their branch and commit format is not configurable.
- Added `.github/workflows/agents-compliance.yml`, a reusable `workflow_call` workflow holding the `pr-checks` and `static-checks` jobs, as an opt-in path for downstream repos that want the compliance checks unmodified, alongside the existing copy-and-tailor adoption path.
- Added a Rule 9 note: pin any `uses:` reference to this repo's reusable workflow to a released tag, never `@main`.
- Added `concurrency: cancel-in-progress` groups to `sync-check.yml` and `agents-md-compliance.yml`, cancelling superseded runs on the same branch or PR.
- Added `ready_for_review` to `agents-md-compliance.yml`'s `pull_request` trigger types, so a PR leaving draft status re-runs its draft-skipped jobs instead of staying stuck at "skipped".

### Changed
- Consolidated `agents-md-compliance.yml` from 4 jobs to a thin caller of `agents-compliance.yml`'s 2 jobs, halving redundant checkout/setup-python overhead per PR run.
- Made `scripts/check_commit_message.py` warning-only (always exits 0), matching `check_us_spelling.py`/`check_english_only.py`, instead of blocking on subject-format violations.
- Exempted Dependabot PRs from the `branch-name` and `commit-message` checks, keyed on PR author (`github.event.pull_request.user.login`) rather than `github.actor`, since a human pushing to or rebasing a Dependabot branch changes the triggering actor but not the PR's author.
- Updated README's "Adopting"/"Banned agents" sections with the reusable-workflow option, a CI efficiency pattern for repos writing custom checker CI, and a new Versioning section.

### Fixed
- Synced all tool rule copies with `AGENTS.md`.

## [1.7.0] (2026-08-08)

### Added
- Added `scripts/` references to the dash/ASCII rule (`lint_style.py`/`check_ascii.py`) and the American spelling/English-only rules (`check_us_spelling.py`/`check_english_only.py`, marked warning only), completing the enforcement markers across every rule with a shipped checker.
- Added a Checker reference table to README, replacing the prose paragraphs Adopting step 5 had accumulated across three prior releases.
- Added `hooks/block_destructive_bash.py`, an opt-in Claude Code `PreToolUse` hook example blocking `rm -rf /`/`~`/`$HOME`, bare `git push --force`/`-f`, and `git reset --hard`.
- Added `hooks/claude-code-settings.example.json`, the wiring example for the hook above.
- Added a README "Claude Code hook example" section documenting both files; not referenced from AGENTS.md, which stays tool-agnostic.

### Changed
- Consolidated the per-PR checker bullets in README's "What's in it" into a single entry pointing at the Checker reference table.

### Fixed
- Synced all tool rule copies with `AGENTS.md`.

## [1.6.0] (2026-08-08)

### Added
- Added `scripts/check_branch_name.py`, backing Branch naming by validating `<type>/<kebab-description>` against the documented prefixes, exempting `main`, `master`, and detached HEAD.
- Added `scripts/check_commit_message.py`, backing the commit-message style bullet by validating `type: description` shape, 50-character length, and no trailing period, stripping a trailing GitHub squash-merge suffix first.
- Added `branch-name` and `commit-message` jobs to `agents-md-compliance.yml`, running on every pull request.
- Added a `check-branch-name` pre-commit hook at the `pre-push` stage.
- Added inline `scripts/` references to Branch naming and the commit-message style bullet.

### Fixed
- Synced all tool rule copies with `AGENTS.md`.

## [1.5.0] (2026-08-08)

### Added
- Added `scripts/check_persist_credentials.py`, backing rule 11 by scanning workflow files for `actions/checkout` steps missing `persist-credentials: false`.
- Added `scripts/check_weak_hashing.py`, backing rule 7 by flagging MD5/SHA-1 calls with no same-line justification comment.
- Added `scripts/check_dockerfile_root.py`, backing rule 12 by flagging Dockerfiles, compose files, and Kubernetes manifests with no non-root user configured.
- Added `scripts/check_secrets_heuristic.py`, backing rule 8 with a heuristic match on structured secret-token prefixes and a `.env`/`.env.local` filename block.
- Added a Rule 12 exception comment, `# runtime-root: this container <reason> (Rule 12 exception).`, mirroring rule 11's escape hatch.
- Added a `static-checks` job to `agents-md-compliance.yml`, running all four new checkers on every push and pull request to `main`.
- Added local pre-commit hooks for all four checkers, scoped to their relevant file globs.
- Added inline `scripts/` references to rules 7, 8, 11, and 12, and Adopting-step guidance for propagating them.

### Fixed
- Synced all tool rule copies with `AGENTS.md`.

## [1.4.0] (2026-08-08)

### Added
- Added rule 13, **Back enforcement claims with real checks**: no rule may claim CI or tooling enforcement it lacks; propose the check in the same change that adds an enforceable rule.
- Added `scripts/check_banned_agents.py`, matching commit author, committer, and `Co-authored-by` trailer fields, plus the PR author, against a banned-agent denylist.
- Added `.github/workflows/agents-md-compliance.yml`, running the check on every pull request.
- Added `README.md` Adopting step 6: adopting repos may prune rules and their checks that do not apply, with user approval, without violating rule 13.

### Changed
- Rewrote the Banned agents section's enforcement claim to name the real script and its limitation (cannot catch a banned agent committing under a human's own identity with no trailer).

### Fixed
- Synced all tool rule copies with `AGENTS.md`.

## [1.3.0] (2026-08-08)

### Added
- Added `**American English spelling**` rule banning British spelling variants (`-our`, `-ise`/`-isation`, `-re`, etc.) even though they are valid ASCII.
- Added `**English only**` rule requiring English in code, comments, commit messages, and documentation, with comments always English and no exception for Chinese, Japanese, or Korean, even in a codebase targeting those markets.
- Added `scripts/check_us_spelling.py`, a portable, warning-only checker for the American spelling rule, usable in any repo.
- Added `scripts/check_english_only.py`, a portable, warning-only stopword heuristic for the English-only rule, usable in any repo.
- Added `scripts/check_ascii.py`, a portable, blocking checker mirroring `lint_style.py`'s existing dash and ASCII checks for use outside this repo.
- Added the two new warning-only checks to `make lint` and to the CI style-lint step.
- Added `README.md` guidance for propagating all three new checkers into adopting repos, including each script's exit-code contract.

### Fixed
- Synced all tool rule copies with `AGENTS.md`.

## [1.2.0] (2026-07-19)

### Added
- Added rule requiring `persist-credentials: false` on `actions/checkout` steps that do not need the credential afterward.
- Added rule requiring non-root Docker containers by default, with explicit user consent required before configuring runtime root.

### Fixed
- Set `persist-credentials: false` on the `sync-check.yml` checkout step per the new rule.
- Synced all tool rule copies with `AGENTS.md`.

## [1.1.0] (2026-07-16)

### Added
- Added `**No suppressing checks**` rule banning `# noqa`, `type: ignore`, and disabling CI steps to force a pass.
- Added history-safety rule forbidding force-push, rebase, amend, or reset of pushed commits on shared branches without consent.
- Added `**No run-on sentences**` rule prohibiting clause-splicing.
- Added `scripts/lint_style.py`, a `make lint` target, and a CI style-lint step enforcing the dash and ASCII rules on `AGENTS.md`.

### Changed
- Strengthened the em/en dash rule to ban hyphen substitutes (`--`, `---`, spaced ` - `) and reframed it around run-on sentences.
- Closed self-attested loopholes: weak-hashing exception, always-draft PRs (removed the integration-tool exception), test-first mocking, retry discipline, and magic-number naming.
- Renamed `**No extended ASCII**` to `**No non-ASCII characters**` and restricted Unicode to string literals or data.
- Replaced incomplete-work rule to cover markers beyond `TODO`/`FIXME` (`XXX`, `HACK`, stubs, bare `pass`).
- Required commit detail in the body rather than truncating the subject.
- Tightened AGENTS.md prose throughout to cut needless words.

### Fixed
- Fixed `AGENTS.md` self-violations of its own dash and ASCII rules, and replaced emoji `Bad`/`Good` markers with ASCII.
- Synced all tool rule copies with `AGENTS.md`.

## [1.0.0] (2026-07-11)

### Added
- Added `**Documentation and versioning**` rule specifying target README/CHANGELOG updates and Semantic Versioning (SemVer 2.0.0) requirements.
- Added `**Imperative tone**` style rule.
- Added `**Path traversal**` correctness and safety rule.
- Added `.copilot-instructions` (root-level) and `.github/copilot-instructions.md` to rules sync script.
- Added local pre-commit hook (`.pre-commit-config.yaml`) and task runner (`Makefile`) for sync checks.
- Added GitHub Actions workflow (`.github/workflows/sync-check.yml`) running in CI with read-only permissions.
- Added **Roo Code** and **OpenHands** compatibility instructions to `README.md`.

### Changed
- Overhauled `AGENTS.md` prose to use imperative, professional, and terse tone.
- Excluded redundant rule copy files in `.claudeignore` to reduce context token waste.
- Formatted example lines with double-space markdown line breaks instead of bullet lists.
- Updated `Adopting` guidelines in `README.md` to prevent agent integration pitfalls (respecting custom rules, verifying commands, and preventing unauthorized changes).

### Fixed
- Synced all tool rule copies (`CLAUDE.md`, `GEMINI.md`, etc.) with `AGENTS.md`.
