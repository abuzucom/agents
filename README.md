# AGENTS.md template

A generic, terse instruction file for AI coding agents - see Tool
compatibility and Banned agents below. Copy into a repository and adapt.

## What's in it

- **Non-negotiable summary** - every critical rule in one line, at the
  top, where model attention is strongest.
- **Nine critical rules** - injection, destructive commands, test
  integrity, scope, draft-PR workflow, API contracts, hashing, secrets, dependencies.
- **Branch naming** - clean conventions for branch names.
- **Workflow** - test-first, lint-clean, safe editing, retry discipline.
- **Correctness & safety** - divisors, regex backtracking, collection
  mutation, unbounded recursion, log sanitization, idempotency.
- **Concurrency & shared state** - locks, task joining, lock ordering.
- **Code quality and style** - limits and conventions (magic numbers, change size, duplication, TODO/FIXME ban, comments, commit messages, extended ASCII ban) applicable without judgment calls.
- **Orientation template** (commented out, end of file) - Commands, Do not
  touch, Architecture, Gotchas, doc pointers. Per-repo; fill on adoption.
- **`.claudeignore`** - excludes noisy/generated paths (`node_modules/`,
  build output, lockfiles, `.env*`, etc.) from Claude Code's context. Part
  of the template, not optional tooling - see Adopting step 1.

## Adopting

1. Copy `AGENTS.md`, `.claudeignore`, `.gitattributes`, and `.editorconfig` to your repo root - all are
   part of this template. If the target repository already contains custom rules files
   (e.g., CLAUDE.md, .cursorrules), respect those custom rules: do not blindly overwrite them.
   Analyze their content, extract repository-specific guidelines, and merge them into AGENTS.md,
   or flag differences to the user for approval before syncing. Adjust `.claudeignore` patterns
   to the target repo's stack (build output dirs, dependency dirs, secrets globs).
2. Uncomment the orientation block (located directly below "Non-negotiable");
   fill Commands and Do not touch first; delete unused sections. Do not guess or hallucinate
   commands or paths; run static analysis of the repository (e.g., inspecting lockfiles or configuration
   files) to verify correct commands and directories first.
3. Swap code examples to your dominant language if it is not Python.
4. Tool files (`CLAUDE.md`, `GEMINI.md`, etc.) are real copies of
   AGENTS.md (Windows compatibility). After editing AGENTS.md, run
   `make sync` (or manually run `python scripts/sync.py`); `--check` in CI or
   `make check` catches drift. `.claudeignore`, `.gitattributes`, and `.editorconfig`
   are not part of this sync - they are single shared files, copied as-is.
5. Back lintable rules (nesting, function size, line length, empty
   catches, cond-assign, injection, MD5) with linter/semgrep config. If you (agent)
   are doing the integration, do not wire up lint CI, add files, or dependencies unprompted (Rule 4).
   Propose linter configuration and CI setup as a separate proposal for user approval.

## Banned agents

AGENTS.md contains a banned-agents section (currently xAI/Grok). Instructions
bind only compliant agents; pair with CI rejecting banned-agent fingerprints
(bot authors, `Co-authored-by` trailers) and platform-level bot blocks.

Do not create pointer or copy files for banned tools; do not add them to
`scripts/sync.py`.

## Tool compatibility

`AGENTS.md` is canonical; tool files are synced copies
(`make sync` or manually `python scripts/sync.py` after editing; `--check` in CI).

| Tool | Reads | How |
|---|---|---|
| ChatGPT / Codex | `AGENTS.md` | Native |
| Cursor | `AGENTS.md`, `.cursorrules` | Native + copy fallback |
| Claude (Claude Code) | `CLAUDE.md` | Synced copy |
| Gemini (CLI) | `GEMINI.md` | Synced copy (or set `contextFileName` to AGENTS.md) |
| Cline / Roo Code | `.clinerules` | Synced copy |
| Windsurf | `.windsurfrules` | Synced copy |
| Aider / OpenHands (local) | `CONVENTIONS.md` | Synced copy; load via `--read CONVENTIONS.md` |
| Other local agents (Zed, Continue, etc.) | `AGENTS.md` or config | Native or point config at it |
| GitHub/Microsoft Copilot | `.github/copilot-instructions.md`, `.copilot-instructions` | Synced copies |
| Mistral, Perplexity, DeepSeek, Lovable | N/A | No repo-file convention: paste AGENTS.md into system prompt / custom instructions / project knowledge |
| xAI/Grok | N/A | Banned - see Banned agents; no pointer files |

Verify against each tool's current docs; conventions shift.

## Maintaining

When an agent errs for lack of context, add the line that would have
prevented it. Prune as ruthlessly as you add.

This template repo is exempt from rule 5's branch requirement: maintainers
direct commits to `main` interactively. The exemption does not copy to
adopting repos.
