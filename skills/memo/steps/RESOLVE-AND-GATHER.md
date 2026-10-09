# Step 1 — Resolve the doc, gather the facts

Run `clio q gather [target]`. One report: today · the uncommitted and untracked files (`.claude/` excluded) and whether the code is the one the last memo recorded · the commits no record names, with the docs that cover each · **`case:`, computed** · the rows near the target (no target: matched on the words the changed files share) and their plan tasks · the commit holding the files (none while any is uncommitted) · the rules that bind them · the open debt that mentions the work (read it here, not from `debt.jsonl`) · the `domains:` a record may use · the keyword vocabulary · the feature directories. Check `case:` against what you did this session; `clio q built --file …` / `history <id>` only to dig past it.

| The report says | Do |
|---|---|
| `UNCHANGED since the last memo` | stop: "nothing new to record" |
| files changed | work in progress or just finished: the target's case |
| nothing changed, commits unrecorded | `RARE.md` (backfill, or a chore) |
| nothing changed, nothing unrecorded | stop: "nothing to record", unless the user names work outside git |
| not a git repository | the target's case; files from the session, no commit |

## Which doc — before writing anything
- **A, a path:** exists → UPDATE. Missing → stop and ask (creating it forks the sub-task's history).
- **B, a task id:** a doc owns it → UPDATE. None, but it is a sub-task `3.1.1` of an owned `3.1` → UPDATE the **parent's** doc (a sub-task changes what its parent describes); never a second doc for one piece of work. The plan task exists, no doc → CREATE. In no plan → stop and ask; never invent an id.
- **C, no target:** the docs already covering the changed files are listed. One, same sub-task → UPDATE; several → show them, ask; none → CREATE.

Same files ≠ same sub-task. Continuing, fixing, extending or reverting what a doc describes → UPDATE it; a different observable behaviour, even in the same feature → a new doc beside it.

## The facts
- **Files.** Your own edits this run, checked against `changed` (a reverted one drops out). In `changed` but not yours → show the user, it may be their work. No session memory → take the list from git and say so. A subagent's files never show in your tool calls: take them from its report.
- **Build output is dropped**: `.claude/rules/*.md` hold the generated-vs-source map; record the source. A generated path the *only* change → you edited the copy: stop and tell the user. A scaffold run (`flutter create`, `npx create-*`…) is the command in `## Decisions` plus one `files` entry `scaffold:<command>`.
- **`req`/`specs`** from the report's rows. No match → `"req":[]`, never invented (a wrong `req` misleads later sessions worse than `[]`); keep `specs` only if a spec still governs the area. An open or blocked row: note it, since `DEBT-IT.md` may need a record. A decided row means decided, not built.
- **`plan_tasks`** match on a task's `req`, not its id (a migrated plan keeps its own numbering); the report lists them. Each task this work implements goes in, and step 4 gates and ticks it. Unsure → leave it out: `[]` is correct, a wrong id ticks a task nobody meant.

Next: `WRITE-DOC.md`.
