---
name: ask
description: Explain Clio — what each clio:* command does, when to run it, which files it reads and writes, and how the three ledgers work. Use when the user asks "what does /clio:memo do", "how does Clio work", "which clio command should I run", or anything about the Clio plugin.
argument-hint: "[command name or question, optional]"
---

Read-only. Answer from the plugin's own files; never invent behaviour a SKILL.md does not describe.
No `.claude/clio/` in this project → say so first, point at `/clio:setup`.

Question (may be empty): $ARGUMENTS

**No argument** → print this, then one line: *`clio:context` runs before work; `/clio:memo` after is
the one command to remember, nothing reminds you.*

| Command | Does | Run when |
|---|---|---|
| `/clio:setup` | scaffold `.claude/`, fill CLAUDE.md / CONTEXT.md by asking | once per repo |
| `/clio:ingest <doc>` | distil a requirement document into `docs/specs/memory/*.md` + `requirements.md` | once, and when a new source arrives |
| `clio:context` (auto) | before coding: the governing spec, what was built, what is owed | Claude triggers it |
| `/clio:memo` | record finished work: task doc, `index.jsonl`, `debt.jsonl` | after each feature / fix |
| `/clio:update` | a spec changed: record the delta vs. existing code, move the row marker | when requirements change |
| `/clio:debt [filter]` | what is still owed, actionable vs. blocked | any time |
| `/clio:ask [x]` | this | when unsure |

Three questions, three files: decided? → `.claude/docs/specs/requirements.md` · built? →
`.claude/clio/index.jsonl` · owed? → `.claude/clio/debt.jsonl`. The `.jsonl` files are append-only;
the last line per `id` / `doc` is current state.

**Argument names a command** → read `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md` (its
`steps/` or `HOP*.md` only if needed). ≤ 15 lines: purpose · files read · files written · one
example invocation · the mistake it exists to prevent.

**Argument is a question** → ledger schema and `kind`s are in
`${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/DEBT-IT.md` and `INDEX-IT.md`, read-side queries in
`${CLAUDE_PLUGIN_ROOT}/skills/context/HOP*.md`, status semantics in
`${CLAUDE_PLUGIN_ROOT}/skills/update/SKILL.md` § 2. Quote the file you answered from. Not
covered → say so.
