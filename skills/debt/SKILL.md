---
name: debt
description: Show what is still owed — open records in .claude/clio/debt.jsonl split into actionable-now vs blocked, optionally filtered by domain, requirement row number or keyword. Read-only.
argument-hint: "[domain | req row number | keyword, optional]"
---

Read-only. `/clio:memo` and `/clio:update` are the writers. No `.claude/clio/` here → say so, point
at `/clio:setup`.

Filter (may be empty): $ARGUMENTS

Last line per `id` is current state; earlier lines are history.
```bash
jq -s -c --arg q "$ARGUMENTS" 'group_by(.id)[] | last | select(.status!="done")
  | select($q=="" or .domain==$q or (.specs[]? | contains($q)) or (.what[]? | contains($q))
           or ((.req[]?|tostring) == $q))' .claude/clio/debt.jsonl
```

Report two groups, in this order; `blocked_by` alone decides which:
- **Actionable now** (`blocked_by: null`) — `id` · `kind` · what · first entry of `code`. The work queue.
- **Blocked** — `id` · what it is waiting on. Say plainly these must not be started.

Then one line: `in-process` items nothing has touched in a while, and any `spec-blocked` record whose
`blocked_by` names a `requirements.md` row that is now ✅ — stale, for the next `/clio:memo` to
re-file. Flag, don't fix. Nothing open → one line.
