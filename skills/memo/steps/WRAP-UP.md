# Step 5 — Wrap up

## What must be remembered, and where

Most of what a run learns is already recorded: the task doc's `## Decisions` holds it, and
`clio:context` serves it to whoever works on that task again. Lift a lesson higher only when **both**
hold — it will come up again in a *different* task, and getting it wrong there costs real time.
Climb one rung at a time and stop at the first that fits:

| Where it recurs | Example | Home | Ask first? |
|---|---|---|---|
| only this sub-task | switching between sign-in and sign-up on the login page | the task doc's `## Decisions` — nothing more | – |
| any sub-task of this feature | "every auth endpoint builds its 429 body with `tooManyRequests()`" | `## General Memory` of `tasks/<feature>/summary.md` | no — report it |
| any task that touches certain paths | "Bucket4j buckets via `computeIfAbsent`, never get-then-put" | `.claude/rules/<topic>.md` with the narrowest `paths:` | **yes** |
| any task at all, no path to scope it | "query data through the `mysql-my` docker container" | `CONTEXT.md` (a fact) or `CLAUDE.md` (an instruction) | **yes** |
| this machine or this user, not the repo | a local tool path, a personal preference | Claude Code's auto memory or `CLAUDE.local.md` | **yes** |

- One bullet per lesson: the concrete trap and what to do instead, checkable against the repo.
  Append to an existing bullet or file that already covers it rather than adding a near-duplicate.
- `CLAUDE.md` and `CONTEXT.md` load every session: the bar there is "a future task in another area
  would go wrong without it". Show the current line count of both next to the diff — past ~200
  together, propose moving something out (to a rule or a summary) in the same ask.
- A path-scoped rule loads only when Claude reads a matching file; with no path to name, the rule
  would load every session, so it belongs in `CONTEXT.md` or a summary instead.
- Draft the exact lines as a diff and **wait for the user's yes** where the table says so. Declined
  → say so in the report, don't ask again this session.

## ADR

Condition: a significant architectural decision was made this run. Check `.claude/clio/docs/decisions/`
for an existing ADR first (UPDATE before CREATE, as in `RESOLVE-AND-GATHER.md`). Else create
`.claude/clio/docs/decisions/${ts}_<keywords>.md` with `ts=$(date +%s)`, index it per `INDEX-IT.md` with
`"type":"adr"` and that same `ts` as its `id`, and link it from the task doc's `## Related`.

ADRs stay in this one flat directory, never inside a feature's folder — an architectural decision is
read by the features it constrains, and `ls .claude/clio/docs/decisions/` has to keep answering "what has
this project already committed to?".

```markdown
# <Decision title>
Date: YYYY-MM-DD
Commit: <hash, or nothing until committed>

## Context
<The forces. What made the obvious choice wrong.>

## Decision
<What was chosen, stated so a future session applies it without re-deriving it.>

## Consequences
<What this makes easy, what it makes hard, what must never be done because of it.>
```

## Report

How this run was verified (or the `unverified` record written instead) · UPDATE or CREATE, doc path,
sections touched · the validated `index.jsonl` line · `req`/`specs` (say "no matching row" if `[]`)
· `debt.jsonl` lines as `id` · `kind` · `status` · `blocked_by` ("none" if none) · stale records
left alone · ADR · every memory write and where it went (summary, rule, CONTEXT.md, CLAUDE.md), and
any declined.
