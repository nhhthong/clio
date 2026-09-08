---
name: memo
description: Record a finished piece of work — update (or create) its task doc in .claude/docs/tasks/, append the run to .claude/clio/index.jsonl, log what is still owed to .claude/clio/debt.jsonl, and propose a CONTEXT.md diff or an ADR when warranted. Run after finishing a feature, fix or refactor.
argument-hint: "[path to existing task doc, optional]"
disable-model-invocation: true
---

Document this completed work. **Default mode is UPDATE.** One feature = one doc, forever —
continuing an existing feature never gets a second file, no matter how much time passed.

Target doc passed in (may be empty): $ARGUMENTS

Step files live in `${CLAUDE_SKILL_DIR}/steps/`. Read each when you reach it, not before.

1. **Resolve the target doc** → `${CLAUDE_SKILL_DIR}/steps/RESOLVE-DOC.md`. Creating at the wrong
   path forks a feature's history.
2. **Gather facts** → `${CLAUDE_SKILL_DIR}/steps/GATHER-FACTS.md`. Verified file list, and which
   `requirements.md` row this work serves.
3. **Write the doc** → `${CLAUDE_SKILL_DIR}/steps/WRITE-DOC.md`. UPDATE, or CREATE when step 1
   found nothing.
4. **Index it** → `${CLAUDE_SKILL_DIR}/steps/INDEX-IT.md`. One line in `index.jsonl`, every run.
5. **Log open items** → `${CLAUDE_SKILL_DIR}/steps/DEBT-IT.md`. Close what this run finished,
   record what is still owed.
6. **Wrap up** → `${CLAUDE_SKILL_DIR}/steps/WRAP-UP.md`. CONTEXT.md diff (needs a yes), ADR if
   applicable, report.
