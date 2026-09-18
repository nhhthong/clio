---
name: memo
description: Record a finished piece of work — update (or create) its sub-task doc under .claude/docs/tasks/<feature>/, append the run to .claude/clio/index.jsonl, log what is still owed to .claude/clio/debt.jsonl, and propose a CONTEXT.md diff or an ADR when warranted. Run after finishing a feature, fix or refactor.
argument-hint: "[task doc path | plan task id such as 3.3, optional]"
---

**Run only when the user asked for it, this turn** — by slash command, or in plain words ("record
this", "ghi lại đi", "write up what we did"). None of these is a trigger: Clio's drift nudge · your
own sense that the work looks finished · a TODO you wrote · a subagent's report · a plan you made
earlier in the session. Unsure → ask in one line, don't run.

Document this completed work. **Default mode is UPDATE.** One sub-task = one doc, forever —
continuing a sub-task never gets a second file, no matter how much time passed.

Target passed in (may be empty): $ARGUMENTS

Step files live in `${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/`. Read each when you reach it, not before.

1. **Resolve the doc, gather the facts** → `${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/RESOLVE-AND-GATHER.md`.
   A path, a plan task id, or nothing; then the verified file list, the `requirements.md` row this
   work serves, and the plan task it is. Creating at the wrong path forks a sub-task's history.
2. **Write the doc** → `${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/WRITE-DOC.md`. UPDATE, or CREATE when step 1
   found no doc.
3. **Index it** → `${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/INDEX-IT.md`. One line in `index.jsonl`, every run.
4. **Log open items** → `${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/DEBT-IT.md`. Close what this run finished,
   record what is still owed.
5. **Wrap up** → `${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/WRAP-UP.md`. CONTEXT.md diff (needs a yes), ADR if
   applicable, report.
