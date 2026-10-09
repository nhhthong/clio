---
name: memo
description: Record a finished piece of work as a sub-task doc, an index line and debt records, and tick the plan task once the test gate passes. Use when the user says a feature, fix or refactor is done.
argument-hint: "[task doc path | plan task id such as 3.3 — optional]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio q *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio validate *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test gate *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test tick *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test fp) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio add index *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio add debt *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio doc)
---

Run only when the user asked this turn, by slash command or in plain words ("record this", "ghi lại đi", "write up what we did"). A drift nudge, a TODO or a subagent report is not a request. Unsure: ask in one line.

Document this work. **Default mode is UPDATE**: one sub-task = one doc, forever; continuing it never gets a second file. `clio` = `${CLAUDE_PLUGIN_ROOT}/bin/clio`, full path every call (a fresh shell each time).

**Target** `$ARGUMENTS`, classified once: contains `/` or ends `.md` → path target; matches `^[0-9]+(\.[0-9]+)*$` → task target; empty → none; anything else → ask what it names, never guess.

**Commits.** Uncommitted work is normal: the commit is simply not known yet, so write none (`commits` gains no entry, `Commit:` stays empty). **Never write `HEAD`** as this run's commit: it is whatever was committed last. The hash arrives later: the drift hook notices the unrecorded commit and the next `/clio:memo` backfills it.

## Steps
Read each step file when you reach it, not before (`${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/`).
1. **Resolve and gather** → `RESOLVE-AND-GATHER.md`: `clio q gather` says which doc, which files, which commit, which rows and tasks.
2. **Write the doc** → `WRITE-DOC.md`: `clio doc` creates or updates it.
3. **Index it** → `INDEX-IT.md`: `clio add index`, every run.
4. **Log open items, tick the plan** → `DEBT-IT.md`: close what this run finished, gate and tick its tasks, record what is owed.
5. **Wrap up** → `WRAP-UP.md`: a rules/memory entry (needs a yes), the report.

The uncommon paths are in `steps/RARE.md`, read only when the case calls for it: **backfill** (Case D), a **chore** commit, a **withdrawn** task's docs, an **ADR**, **light** work (every task of the run is `"tier":"light"`; the gate is never skipped).
