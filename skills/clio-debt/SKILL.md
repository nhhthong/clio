---
name: clio-debt
description: Show what is still owed — open records in .claude/clio/debt.jsonl split into actionable-now vs blocked, optionally filtered by domain, requirement row number or keyword. Read-only.
argument-hint: "[domain | req row number | keyword, optional]"
---

Read-only. Never writes — `/clio-memo` and `/clio-update` are the writers.

Filter (may be empty): $ARGUMENTS

Last line per `id` is current state; earlier lines are that item's history, ignore them.

```bash
jq -s -c 'group_by(.id)[] | last | select(.status!="done")' .claude/clio/debt.jsonl
```

Narrow when `$ARGUMENTS` is given — a number is a `req` row, anything else matches `domain`,
`specs` or free text in `what`:

```bash
jq -s -c --arg q "<arg>" 'group_by(.id)[] | last | select(.status!="done")
  | select(.domain==$q or (.specs[]? | contains($q)) or (.what[]? | contains($q))
           or ((.req[]?|tostring) == $q))' .claude/clio/debt.jsonl
```

## Report

Two groups, in this order — `blocked_by` is the only field that decides which:

- **Actionable now** (`blocked_by: null`) — `id` · `kind` · what · first entry of `code`. This is
  the work queue.
- **Blocked** (`blocked_by` non-null) — `id` · what it is waiting on. Say plainly that these must
  not be started.

Then one line of coverage: `in-process` items that nothing has touched in a while, and any
`spec-blocked` record whose `blocked_by` names a `requirements.md` row that is now ✅ — that one is
stale and should be re-filed as `code-debt` by the next `/clio-memo`. Flag it, don't fix it.

Nothing open → say so in one line. No `.claude/clio/` in this project → say so in one line and
point at `/clio-setup`. Don't fall back to reading `index.jsonl` or the docs.
