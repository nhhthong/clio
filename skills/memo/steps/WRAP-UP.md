# Step 5 — Wrap up

## What must be remembered, and where
Most of what a run learns is already in the task doc's `## Decisions`, which `clio:context` serves to whoever works on that task again. Lift a lesson higher only when **both** hold: it will come up again in a *different* task, and getting it wrong there costs real time. Climb one rung at a time, stop at the first that fits:

| Where it recurs | Home | Ask first? |
|---|---|---|
| only this sub-task | the doc's `## Decisions`, nothing more | – |
| any sub-task of this feature | `## General Memory` of `tasks/<feature>/summary.md` | no, report it |
| any task touching certain paths | `.claude/rules/<topic>.md` with the narrowest `paths:` | **yes** |
| any task, no path to scope it | `CONTEXT.md` (a fact) or `CLAUDE.md` (an instruction) | **yes** |
| this machine or user, not the repo | auto memory or `CLAUDE.local.md` | **yes** |

One bullet per lesson: the concrete trap and what to do instead, checkable against the repo; append to an existing bullet rather than add a near-duplicate. `CLAUDE.md` and `CONTEXT.md` load every session: the bar is "a task in another area would go wrong without it"; show the line count of both next to the diff, and past ~200 together propose moving something out. A path-scoped rule loads only when a matching file is read, so one with no path to name belongs in `CONTEXT.md` or a summary. Draft the exact lines as a diff and **wait for the user's yes** where the table says so; declined → say so in the report, don't ask again this session.

## Report
How this run was verified (or the `unverified` record) · UPDATE or CREATE, the doc, sections touched · the index record · `req`/`specs` (say "no matching row" if `[]`) · debt lines as `id` · `kind` · `status` · `blocked_by` · stale records left alone · every memory write and where it went, and any declined.
