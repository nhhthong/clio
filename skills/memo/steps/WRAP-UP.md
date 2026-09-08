# Step 6 — Wrap up

## CONTEXT.md

Condition: this run introduced a new domain term, or hit a landmine that cost real time. Draft the
exact lines, show them as a diff, and **wait for the user's yes before writing** — CONTEXT.md loads
every session, so a wrong line is paid on every future task. Stable facts only, no task history, no
HTML comments. Declined → say so in the report, don't ask again this session.

## ADR

Condition: a significant architectural decision was made this run. Check `.claude/docs/decisions/`
for an existing ADR first (UPDATE before CREATE, as in `RESOLVE-DOC.md`). Else create
`.claude/docs/decisions/YYYY-MM-DD_<keywords>.md`, index it per `INDEX-IT.md` with `"type":"adr"`,
and link it from the task doc's `## Related`.

```markdown
# <Decision title>
Date: YYYY-MM-DD
Commit: <hash or "not committed">

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
left alone · ADR / CONTEXT.md writes, if any.
