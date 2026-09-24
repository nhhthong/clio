---
name: memo
description: Record a finished piece of work — update (or create) its sub-task doc under .claude/clio/docs/tasks/<feature>/, append the run to .claude/clio/database/index.jsonl, log what is still owed to .claude/clio/database/debt.jsonl, tick the plan task once /clio:test's gate passes, and propose a path-scoped .claude/rules/ entry or an ADR when warranted. Works on committed or uncommitted work, and backfills the commit hash later. Run after finishing a feature, fix or refactor.
argument-hint: "[task doc path | plan task id such as 3.3 — optional]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/skills/context/scripts/q.sh *) Bash(${CLAUDE_PLUGIN_ROOT}/skills/memo/scripts/validate.sh *) Bash(${CLAUDE_PLUGIN_ROOT}/skills/test/scripts/clio-test.sh gate *)
---

**Run only when the user asked for it, this turn** — by slash command, or in plain words ("record
this", "ghi lại đi", "write up what we did"). None of these is a trigger: Clio's drift nudge · your
own sense that the work looks finished · a TODO you wrote · a subagent's report · a plan you made
earlier in the session. Unsure → ask in one line, don't run.

Document this work. **Default mode is UPDATE.** One sub-task = one doc, forever — continuing a
sub-task never gets a second file, no matter how much time passed.

## Target

`$ARGUMENTS`

Classify it once, here; the step files refer to it as **the target** and never re-read it:
- a path (contains `/` or ends `.md`) → **path target**;
- matches `^[0-9]+(\.[0-9]+)*$` (`3.3`, `0.2`) → **task target**;
- empty → **no target**;
- anything else → ask what it names. Never guess.

## Scripts

The step files name these by basename only. Each Bash call is a fresh shell — no variable survives
to the next call — so always call them by the full path below, never through a variable:

| Name in the step files | Call it as |
|---|---|
| `q.sh` | `${CLAUDE_PLUGIN_ROOT}/skills/context/scripts/q.sh` |
| `validate.sh` | `${CLAUDE_PLUGIN_ROOT}/skills/memo/scripts/validate.sh` |
| `clio-test.sh` | `${CLAUDE_PLUGIN_ROOT}/skills/test/scripts/clio-test.sh` |

## Commits: record what exists, leave the rest empty

Uncommitted work is normal and is recorded the same way. The commit is simply not known yet:
- `q.sh commit <files of this run>` prints the commit holding them, or **nothing** — while any of the
  files is still uncommitted, in a repo with no commit yet, or outside git. Nothing is the answer to
  write: `commits` gains no entry, the doc's `Commit:` line and the plan's `Done` cell carry no hash.
- **Never write `HEAD`** as this run's commit because it exists — HEAD is whatever was committed last,
  usually not this work.
- The hash arrives later on its own: after the user commits, the drift hook notices the unrecorded
  commit, and the next `/clio:memo` backfills it (Case D in step 1) without touching anything else.

## Steps

Step files live in `${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/`. Read each when you reach it, not before.

1. **Resolve the doc, gather the facts** → `RESOLVE-AND-GATHER.md`. Which doc, which files, which
   commit (or none), which requirement row, which plan task. Creating at the wrong path forks a
   sub-task's history.
2. **Write the doc** → `WRITE-DOC.md`. UPDATE, or CREATE when step 1 found no doc.
3. **Index it** → `INDEX-IT.md`. One line in `index.jsonl`, every run.
4. **Log open items, tick the plan** → `DEBT-IT.md`. Close what this run finished, gate and tick its
   plan tasks, record what is still owed.
5. **Wrap up** → `WRAP-UP.md`. `.claude/rules/` entry (needs a yes), ADR if applicable, report.

A backfill run (Case D) does steps 2–3 and the plan-tick part of 4 only, and changes nothing but the
commit hash.
