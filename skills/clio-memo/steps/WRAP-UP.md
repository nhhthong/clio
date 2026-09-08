# Step 6 — Wrap up

## CONTEXT.md

**Condition:** this run introduced a new domain term, hit a landmine that cost real time, or the
`session-debt` hook reported CONTEXT.md falling behind the ledger. Draft the exact lines to add or
change, show them as a diff, and **wait for the user's yes before writing** — CONTEXT.md loads every
session, so a wrong line is paid on every future task. Stable facts only, no task history, no HTML
comments. Declined → say so in the report, don't ask again this session.

## ADR

**Condition:** a significant architectural decision was made this run. Check
`.claude/docs/decisions/` for an existing ADR first (same UPDATE-before-CREATE rule as
`RESOLVE-DOC.md`). Else create `.claude/docs/decisions/YYYY-MM-DD_<keywords>.md`; index it per `INDEX-IT.md` with
`"type":"adr"`; cross-link in the task doc's `## Related`.

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

No `## Change Log`/`## Related` needed on an ADR — `index.jsonl` carries links via
`specs`/`req`/`docs`. Add `Updated:` + a superseding section only if actually revised later. Try the
`manage_adr` tool first if codebase-memory-mcp is installed and this repo is indexed; otherwise write
the file directly.

## Confirm

Report: how this run was verified (or the `unverified` record written instead), UPDATE or CREATE,
doc path, sections touched, validated index.jsonl record(s), resolved
`specs`/`req` (explicit "no matching requirements.md row" if `[]`), debt.jsonl record(s) with
`id`·`kind`·`status`·`blocked_by` ("none" if none), stale records left alone (other area),
ADR/CONTEXT.md writes if any.
