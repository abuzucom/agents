# AGENTS.md template

A generic, terse instruction file for AI coding agents — see Tool
compatibility and Banned agents below. Copy into a repository and adapt.

## What's in it

- **Non-negotiable summary** — every critical rule in one line, at the
  top, where model attention is strongest.
- **Seven critical rules** — injection, destructive commands, test
  integrity, scope, draft-PR workflow, API contracts, hashing.
- **Workflow** — test-first, lint-clean, safe editing, retry discipline.
- **Correctness & safety** — divisors, regex backtracking, collection
  mutation, unbounded recursion.
- **Code quality and style** — limits and conventions applicable without
  judgment calls.
- **Orientation template** (commented out, end of file) — Commands, Do not
  touch, Architecture, Gotchas, doc pointers. Per-repo; fill on adoption.
- **`.claudeignore`** — excludes noisy/generated paths (`node_modules/`,
  build output, lockfiles, `.env*`, etc.) from Claude Code's context. Part
  of the template, not optional tooling — see Adopting step 1.

## Adopting

1. Copy `AGENTS.md` **and** `.claudeignore` to your repo root — both are
   part of this template. If you (human or agent) are asked to add this
   AGENTS.md setup to another repository, `.claudeignore` is in scope by
   default; do not drop it just because it wasn't named explicitly.
   Adjust its patterns to the target repo's stack (build output dirs,
   dependency dirs, secrets globs).
2. Uncomment the orientation block; fill Commands and Do not touch first;
   delete unused sections. Move filled sections up, after "Non-negotiable".
3. Swap code examples to your dominant language if it isn't Python.
4. Tool files (`CLAUDE.md`, `GEMINI.md`, etc.) are real copies of
   AGENTS.md (Windows compatibility). After editing AGENTS.md, run
   `python scripts/sync.py`; `--check` in CI catches drift. `.claudeignore`
   is not part of this sync — it's a single shared file, copied as-is.
5. Back lintable rules (nesting, function size, line length, empty
   catches, cond-assign, injection, MD5) with linter/semgrep config —
   instructions guide, enforcement guarantees.

## Banned agents

AGENTS.md contains a banned-agents section (currently xAI/Grok). Instructions
bind only compliant agents; pair with CI rejecting banned-agent fingerprints
(bot authors, `Co-authored-by` trailers) and platform-level bot blocks.

Do not create pointer or copy files for banned tools; do not add them to
`scripts/sync.py`.

## Tool compatibility

`AGENTS.md` is canonical; tool files are synced copies
(`python scripts/sync.py` after editing; `--check` in CI).

| Tool | Reads | How |
|---|---|---|
| ChatGPT / Codex | `AGENTS.md` | Native |
| Cursor | `AGENTS.md`, `.cursorrules` | Native + copy fallback |
| Claude (Claude Code) | `CLAUDE.md` | Synced copy |
| Gemini (CLI) | `GEMINI.md` | Synced copy (or set `contextFileName` to AGENTS.md) |
| Cline | `.clinerules` | Synced copy |
| Windsurf | `.windsurfrules` | Synced copy |
| Aider (local) | `CONVENTIONS.md` | Synced copy; load via `--read CONVENTIONS.md` |
| Other local agents (Zed, Continue, etc.) | `AGENTS.md` or config | Native or point config at it |
| GitHub Copilot | `AGENTS.md`, `.github/copilot-instructions.md` | Native (verify version) or pointer file |
| Mistral, Perplexity, DeepSeek, Lovable | — | No repo-file convention: paste AGENTS.md into system prompt / custom instructions / project knowledge |
| xAI/Grok | — | Banned — see Banned agents; no pointer files |

Verify against each tool's current docs; conventions shift.

## Maintaining

When an agent errs for lack of context, add the line that would have
prevented it. Prune as ruthlessly as you add.

This template repo is exempt from rule 5's branch requirement: maintainers
direct commits to `main` interactively. The exemption does not copy to
adopting repos.
