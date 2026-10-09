---
name: setup
description: Set up Clio in the current project — create .claude/clio/docs/ and .claude/clio/database/, asking the user only what nothing on disk can tell. Never touches CLAUDE.md, CONTEXT.md, .claude/rules/ or the stack. Run once per repository, before any other clio:* skill.
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio setup *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio validate all)
---

Run only when the user asked this turn, by slash command or in plain words ("set Clio up here", "cài clio vào repo này"). A drift nudge, a TODO or a subagent report is not a request. Unsure: ask in one line.

Everything Clio owns lives in `.claude/clio/`. Setup writes nothing outside it.

## 1. Check
Run `${CLAUDE_PLUGIN_ROOT}/bin/clio setup check`.
- `MISSING` or `ALREADY SET UP`: tell the user, stop.
- `PARTLY SET UP`: ask only what step 2 still needs. Setup skips what exists.

## 2. Ask once
One `AskUserQuestion`, only what applies:
- `NOT A GIT REPO`: run `git init`? Never without a yes.
- Mode: Full (a requirement document exists; which file?) or Lite (none).
- Domains: business areas that work is filed under, for example `account checkout admin`. Offer what the top-level directories or the document suggest. `infra` and `all` are always added.
- Commit `.claude/clio/` (recommended, the ledgers are history) or ignore it? If ignored, a dropped branch leaves its tasks and runs behind. Say so.

## 3. Scaffold
Run `${CLAUDE_PLUGIN_ROOT}/bin/clio setup run --domains "<domains>"`. Add `--lite` for Lite, `--ignore` if not committed, `--git-init` if the user said yes.

- Committed: the script writes `.gitattributes` so the append-only ledgers merge by union. Union keeps both sides but does not order them, and readers take the last line per key. Two branches that restate one `id` need a human. Say this once. `git add .claude/clio` is the user's move.
- Ignored: tell the user to add `.claude/clio/` to `.gitignore`.

## 4. Verify, then point to the next step
Run `${CLAUDE_PLUGIN_ROOT}/bin/clio validate all`. Then:
- Full: `/clio:ingest <file>`, then `/clio:plan infra`, then `/clio:plan <area>` per area.
- Lite: `/clio:plan infra`. With no spec and an empty repo, `/clio:ingest` a short brief or the user's stack first.
- Per task after that: `/clio:context`, `/clio:test <task>`, `/clio:memo`.
