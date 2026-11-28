# CodeQL Triage

CodeQL default setup reports nine alerts in template files on a fresh
adoption (#190). Each row below traces one alert to the code it flags.
No alert marks a real defect. A future alert in these files still needs its
own trace.

CodeQL default setup reads no repository configuration file. A query filter
in the template therefore cannot hide these alerts. AGENTS.md also bans
suppression comments. A maintainer dismisses each alert in the code scanning
view with the reason "False positive" and a link to this file.

## Clear-text logging (`py/clear-text-logging-sensitive-data`)

The query treats names such as `token` as sensitive. In the gates `token`
names a shell word from the parsed command. It never names a credential.

| File | Sink | Evidence |
| --- | --- | --- |
| `hooks/enforce_branch_name.py` | `_deny()` prints the native denial JSON or stderr text | Each reason is a fixed string. A reason names at most the program, sanitized through `core.sanitize()`. |
| `hooks/enforce_branch_name.py` | `_deny()` second print of the same message | Same message as the row above. |
| `hooks/enforce_branch_name.py` | `_request_authorization()` prints the ask JSON | `recovery_authorization_reason()` builds the text from the current branch name and a fixed example. |
| `hooks/_gate_core.py` | `emit()` prints the decision JSON | Callers pass fixed reasons or sanitized program and variable names. `_command_execution_gate.py` names only the program in `rejected: <program>`. `block_destructive_powershell.py` names an environment variable. It omits the value. |
| `hooks/_gate_core.py` | `emit()` prints the deny message to stderr | Same message as the row above. |
| `scripts/check_compliance_tree.py` | `_report()` prints each violation | `_sanitize()` bounds each line to printable ASCII. `check_secrets_heuristic.py` reports only a path and a line number. `_local_path_violations()` calls `message(reveal=False)` and prints `<redacted>` for a matched name. |

## Clear-text storage (`py/clear-text-storage-sensitive-data`)

| File | Write | Evidence |
| --- | --- | --- |
| `tests/test_trusted_test_runners.py` | `_write_owner_list()` writes a trusted owner list fixture | The fixture holds owner names from the test cases. It holds no credential. |
| `tests/test_trusted_gh_api_read_gate.py` | The fixture setup writes `.git/config`, `.git/HEAD`, and a copy of `scripts/trusted_gh.py` | The config names `https://github.com/example-owner/example-repo.git`. HEAD holds a branch reference or zeros. The script copy matches the repository file. |

## Untrusted checkout (`actions/untrusted-checkout/medium`)

`.github/workflows/immutable-conflict-check.yml` runs on
`pull_request_target` and checks out the pull request head into `pr-head`.
No code from that checkout runs:

- The workflow and every action come from the base branch. Each action
  pins a full commit SHA.
- `actions/setup-python` takes a literal version. The head checkout sits
  in a subdirectory. No head file selects the interpreter.
- `pip` installs from `trusted-base/requirements-checkers.txt` with
  `--only-binary :all:`. No head file reaches the install.
- Python runs `trusted-base/scripts/check_compliance_tree.py`. The checker
  loads its sibling checkers from exact trusted paths.
- The checker reads head content through Git object reads only. Its Git
  environment sets `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` to the null
  device. It drops `GIT_DIR`, `GIT_WORK_TREE`, `GIT_CONFIG`, and the other
  Git directory and configuration overrides. `actions/checkout` writes the
  local `.git` directory. No head file supplies a Git hook or the
  configuration that a filter driver needs.
- Both checkouts set `persist-credentials: false`. The job grants
  `contents: read`. `GH_TOKEN` reaches only the checker step.

The checker reads no head working tree file. A checkout without a working
tree would remove the pattern entirely. That change touches the workflow
and the step schema in `_trusted_steps()` of `check_compliance_tree.py`
together. Both files sit on the protected path list.
