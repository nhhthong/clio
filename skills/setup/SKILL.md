---
name: setup
description: Set up Clio in the current project — create .claude/clio/docs/ (specs, plans, tests, tasks, decisions) and .claude/clio/database/ (the ledgers), asking the user only what nothing on disk can tell. Never touches CLAUDE.md, CONTEXT.md, .claude/rules/ or the stack. Run once per repository, before any other clio:* skill.
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio validate *)
---

**Run only when the user asked, this turn** — by slash command or in plain words ("set Clio up here", "cài clio vào repo này"). Not triggers: the drift nudge, your sense that work looks finished, a TODO, a subagent's report. Unsure → ask in one line, don't run.

Everything Clio owns lives in `.claude/clio/`; setup writes nothing outside it (not `CLAUDE.md`, `CONTEXT.md`, `.claude/rules/`, `.gitignore`), and nothing Clio writes loads every session.
```
.claude/clio/docs/  specs/requirements.md (row → spec index, Domains) · specs/memory/*.md (decisions per area, /clio:ingest)
                    tasks/<feature>/*.md (one doc per sub-task, /clio:memo) · decisions/*.md (ADRs)
.claude/clio/database/  plan/<area>.jsonl · test/<area>.jsonl (written by their skills' script, never by hand)
                        index.jsonl (built) · debt.jsonl (owed) · runs.jsonl (test evidence; the test script only)
```

## 0. Take stock, then ASK once
```bash
for t in bash python3 git awk sed; do command -v $t >/dev/null || echo "MISSING: $t"; done
python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null || echo "MISSING: python3 >= 3.9"
git rev-parse --git-dir >/dev/null 2>&1 || echo "NOT A GIT REPO"
C=.claude/clio
[ -f $C/docs/specs/requirements.md ] && [ -f $C/database/index.jsonl ] && [ -f $C/database/debt.jsonl ] && echo "ALREADY SET UP"
[ -d $C ] && ! [ -f $C/docs/specs/requirements.md ] && echo "PARTLY SET UP"
```
`MISSING` → stop, tell the user. `ALREADY SET UP` → say so, stop. `PARTLY SET UP` → ask only what § 1 still needs, then run § 1 (each step skips what exists).

**ASK**, one `AskUserQuestion`, only what applies:
- `NOT A GIT REPO` → `git init`? Never without a yes.
- **Full** (a requirement document exists: which file?) or **Lite** (none)?
- The `domain` vocabulary: the business areas work is filed under (e.g. `account checkout admin infra all`); offer what the top-level directories or the document suggest. `infra` and `all` are always in it.
- Commit `.claude/clio/` (recommended: the ledgers are history) or ignore it? Ignored, the plan and evidence do not follow a git branch, so a dropped experiment leaves its tasks and runs behind: say so.

## 1. Scaffold
```bash
T="${CLAUDE_PLUGIN_ROOT}/skills/setup/templates"; C=.claude/clio
mkdir -p $C/database/plan $C/database/test $C/docs/specs/memory $C/docs/tasks $C/docs/decisions
[ -f $C/docs/specs/requirements.md ] || cp "$T/requirements.md" $C/docs/specs/requirements.md
touch $C/database/index.jsonl $C/database/debt.jsonl $C/database/runs.jsonl
```
Replace the `Domains:` placeholder in `requirements.md` with the answer, backticked, space-separated: the only values the ledgers' `domain` may hold. **Lite** → also replace everything under `## By requirement number` and `## By topic keyword` with `Lite mode — no requirement source; every record uses req: [] and joins on domain/keywords/files.`

## 2. Commit or ignore
Commit → write `.claude/clio/.gitattributes`, one line (the ledgers are append-only, so two branches adding records merge by keeping both sides):
```gitattributes
database/*.jsonl merge=union
```
Say the limit once: union keeps both sides but does not order them, readers take the *last* line per key, so two branches restating the same `id` need a human. `git add .claude/clio` stays the user's move. Ignore → print `.claude/clio/` for the user to add to `.gitignore`; skip `.gitattributes`.

## 3. Verify, say what comes next
`${CLAUDE_PLUGIN_ROOT}/bin/clio validate all`. Then: **Full** → `/clio:ingest <file>` (distils the spec, proposes the stack, writes `memory/infra.md`), then `/clio:plan infra`, then `/clio:plan <area>` per area. **Lite** → `/clio:plan infra` (reads the stack off the repo; an empty repo with no spec has none to read: `/clio:ingest` a short brief or the stack the user names first). Per task from there: `/clio:context` → `/clio:test <task>` → `/clio:memo`. The only reminder is the `UserPromptSubmit` hook, once per session, when git has work `index.jsonl` does not.
