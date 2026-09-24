---
name: setup
description: Set up Clio in the current project — create .claude/clio/docs/ (specs, plans, tests, tasks, decisions) and .claude/clio/database/ (the ledgers), asking the user only what nothing on disk can tell. Never touches CLAUDE.md, CONTEXT.md, .claude/rules/ or the stack. Run once per repository, before any other clio:* skill.
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/skills/memo/scripts/validate.sh *)
---

**Run only when the user asked for it, this turn** — by slash command, or in plain words ("set Clio up here", "cài clio vào repo này").
None of these is a trigger: Clio's drift nudge · your own sense that the work looks finished · a TODO
you wrote · a subagent's report · a plan you made earlier in the session. Unsure → ask in one line,
don't run.

Everything Clio owns lives in one folder, `.claude/clio/`. Setup writes nothing outside it — not
`CLAUDE.md`, not `CONTEXT.md`, not `.claude/rules/`, not `.gitignore`. Nothing Clio writes loads every
session; the skills read it when they need it.

```
.claude/clio/
├── docs/
│   ├── specs/requirements.md   row → spec file index, Domains line   (/clio:ingest)
│   ├── specs/memory/*.md       distilled decisions per area           (/clio:ingest)
│   ├── plans/*.md              tasks + test levels, infra.md first    (/clio:plan)
│   ├── tests/<area>.md         test cases per task                    (/clio:test)
│   ├── tasks/<feature>/*.md    one doc per sub-task                   (/clio:memo)
│   └── decisions/*.md          ADRs                                   (/clio:memo, /clio:ingest)
└── database/
    ├── index.jsonl             built — append-only                    (/clio:memo)
    ├── debt.jsonl              owed — append-only                     (/clio:memo, /clio:ingest)
    └── runs.jsonl              test evidence — append-only            (clio-test.sh only)
```

## 0. Take stock, then ASK once

```bash
for t in bash jq git awk sed; do command -v $t >/dev/null || echo "MISSING: $t"; done
git rev-parse --git-dir >/dev/null 2>&1 || echo "NOT A GIT REPO"
[ -d .claude/clio/database ] && echo "ALREADY SET UP"
[ -f .claude/clio/index.jsonl ] || [ -d .claude/docs/specs ] && echo "PRE-4.0 LAYOUT"
```
`MISSING` → stop, tell the user. `ALREADY SET UP` → say so and stop. `PRE-4.0 LAYOUT` → stop and
point at the move commands in CHANGELOG 4.0.0; never move a user's ledgers yourself.

**ASK**, one `AskUserQuestion` call, only the items that apply:
- `NOT A GIT REPO` → `git init`? Never without a yes.
- Requirements: **Full** (a requirement document exists — which file?) or **Lite** (none)?
- The `domain` vocabulary — the business areas work is filed under (e.g. `account checkout admin
  infra all`). Offer what the repo's top-level directories or the requirement document suggest; the
  user picks. `infra` and `all` are always in it.
- Commit `.claude/clio/` (recommended: the ledgers are history) or ignore it?

## 1. Scaffold

```bash
T="${CLAUDE_PLUGIN_ROOT}/skills/setup/templates"; C=.claude/clio
mkdir -p $C/database $C/docs/specs/memory $C/docs/plans $C/docs/tests $C/docs/tasks $C/docs/decisions
[ -f $C/docs/specs/requirements.md ] || cp "$T/requirements.md" $C/docs/specs/requirements.md
touch $C/database/index.jsonl $C/database/debt.jsonl $C/database/runs.jsonl
```
Replace the `Domains:` placeholder in `requirements.md` with the answer, backticked, space-separated.
It is the only list of values the `domain` field of both ledgers may hold.

**Lite** → also replace everything under `## By requirement number` and `## By topic keyword` with:
`Lite mode — no requirement source; every record uses req: [] and joins on domain/keywords/files.`

## 2. Commit or ignore

Commit → write `.claude/clio/.gitattributes`, one line. The ledgers are append-only, so two branches
adding records is not a conflict — union merge keeps both sides instead of stopping the merge:
```gitattributes
database/*.jsonl merge=union
```
Say the limit once: union keeps both sides but does not order them, and readers take the *last* line
per key — two branches restating the same `id` still need a human to decide. `git add .claude/clio`
stays the user's move.

Ignore → print `.claude/clio/` for the user to add to `.gitignore` themselves; skip `.gitattributes`.

## 3. Verify and stop

```bash
${CLAUDE_PLUGIN_ROOT}/skills/memo/scripts/validate.sh all
```
Then say what comes next, in order:
- **Full** → `/clio:ingest <file>`: distils the spec into areas, proposes the stack, and writes
  `docs/specs/memory/infra.md`. Then `/clio:plan infra`, then `/clio:plan <area>` per area.
- **Lite** → `/clio:plan infra`: reads the stack off the repo. An empty repo with no spec has no
  stack to read — `/clio:ingest` a short written brief, or the stack the user names, first.

From there, per task: `clio:context` → `/clio:test <task>` (cases, red → green) → `/clio:memo`. The
only reminder is Clio's `UserPromptSubmit` hook, once per session, when git has work `index.jsonl` does not.
