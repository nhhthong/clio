# Step 5 — Wrap up

## `.claude/rules/`

Condition: this run hit a landmine that cost real time, or found a convention a new file in these
paths must follow — and it is **true of a path, not of this task**. Task history stays in the doc.

- Scope it: `paths:` frontmatter naming the narrowest globs the lesson applies to (`src/billing/**`),
  so it loads only when Claude reads a matching file. A lesson with no path is a doc `## Decisions`
  bullet or an ADR, never an unscoped rule — that would load every session.
- Append to the existing `rules/<topic>.md` whose `paths:` already covers it; else a new file named
  by topic. One bullet, the concrete trap and the fix, verifiable from the repo.
- Never write `CLAUDE.md` or `CONTEXT.md`; they are the user's.
- Draft the exact lines as a diff, **wait for the user's yes before writing**. Declined → say so in
  the report, don't ask again this session.

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
left alone · ADR / `.claude/rules/` writes, if any.
