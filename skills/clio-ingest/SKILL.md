---
name: clio-ingest
description: Turn a long requirement document (contract, PRD, spec.md, ticket export) into the distilled spec layer — one .claude/docs/specs/memory/*.md per domain area plus the requirements.md row table — marking every undecided point ⚠️ instead of inventing an answer. Run once after /clio-setup when the project has a requirement source, and again whenever a new source arrives.
argument-hint: "[path to the source requirement doc, or a keyword to re-ingest one area]"
disable-model-invocation: true
---

The source document is written for humans and is far too long to load every session. This skill
distils it once into short per-domain files an agent can actually read, and an index that maps
requirement rows onto them.

**It never invents a decision.** A point the source leaves open becomes ⚠️ with the name of whoever
owes the answer — never a plausible-sounding guess.

Source (may be empty — then ask): $ARGUMENTS

Step files live in `${CLAUDE_SKILL_DIR}/steps/`. Read each one when you reach it, not before.

## Walk the steps, in order

1. **Read the source, agree the split** → `${CLAUDE_SKILL_DIR}/steps/GATHER-SOURCE.md`. Establish
   source priority and the domain areas before writing anything.
2. **Write the memory files** → `${CLAUDE_SKILL_DIR}/steps/WRITE-MEMORY.md`. One short file per
   domain, decisions only, each quoting its origin verbatim.
3. **Write the index** → `${CLAUDE_SKILL_DIR}/steps/WRITE-INDEX.md`. The row table, the keyword
   table and the source-priority list in `requirements.md`; then file every ⚠️/❌ row as debt.

Re-running on a source that already has memory files is an **update**: keep existing decisions,
append new ones, and never silently drop a ⚠️ that is still open.
