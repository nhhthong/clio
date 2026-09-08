---
name: clio-ask
description: Explain Clio — what each clio-* command does, when to run it, which files it reads and writes, and how the three ledgers work. Use when the user asks "what does /clio-memo do", "how does Clio work", "which clio command should I run", or anything about the Clio plugin.
argument-hint: "[command name or question, optional]"
---

Read-only. Answer from the plugin's own files; never invent behaviour a SKILL.md does not describe.

Question (may be empty): $ARGUMENTS

## No argument → the overview

Print this table, then one line on the loop: *`clio-context` runs before work, the Stop hook nags
after, `/clio-memo` is the only command a developer must remember.*

| Command | Does | Run when |
|---|---|---|
| `/clio-setup` | scaffold `.claude/` and fill CLAUDE.md / CONTEXT.md by asking | once per repo |
| `/clio-ingest <doc>` | distil a requirement document into `docs/specs/memory/*.md` + `requirements.md` | once, and when a new source arrives |
| `clio-context` (auto) | before coding: the spec that governs the area, what was built, what is owed | Claude triggers it |
| `/clio-memo` | record finished work: task doc, `index.jsonl`, `debt.jsonl` | after each feature / fix |
| `/clio-update` | a spec changed: record the delta vs. existing code, move the row marker | when requirements change |
| `/clio-debt [filter]` | list what is still owed, actionable vs. blocked | any time |
| `/clio-ask [x]` | this | when unsure |

Three ledgers, three questions: decided? → `.claude/docs/specs/requirements.md` status column ·
built? → `.claude/clio/index.jsonl` · owed? → `.claude/clio/debt.jsonl`. Both `.jsonl` files are
append-only; the last line per `id` / `doc` is current state.

## Argument names a command

Read `${CLAUDE_PLUGIN_ROOT}/skills/clio-<name>/SKILL.md` (and its `steps/` or `HOP*.md` files only
if the question needs them). Answer in ≤ 15 lines: purpose · inputs · files read · files written ·
one concrete example invocation · the one mistake it exists to prevent.

## Argument is a question

Find the answer in the plugin files — ledger schema and `kind`s in
`${CLAUDE_PLUGIN_ROOT}/skills/clio-memo/steps/DEBT-IT.md` and `INDEX-IT.md`, read-side queries in
`${CLAUDE_PLUGIN_ROOT}/skills/clio-context/HOP*.md`, status semantics in
`${CLAUDE_PLUGIN_ROOT}/skills/clio-update/steps/DECIDE-STATUS.md`. Quote the file you answered
from. Not covered anywhere → say so; do not guess.

If the current project has no `.claude/clio/`, say so in one line first and point at `/clio-setup`.
