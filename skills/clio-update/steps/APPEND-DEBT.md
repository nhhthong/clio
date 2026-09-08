# Step 3 — Update `.claude/clio/debt.jsonl`

Same ledger `/clio-memo` writes to — one JSON object per line, **APPEND ONLY**: updating an
existing `id` means appending a new line stating the record in full, and readers take the last line
per `id`. `kind` here always `"spec-delta"`. Full 14-field schema + validation →
`${CLAUDE_PLUGIN_ROOT}/skills/clio-memo/steps/DEBT-IT.md` § Fields table.

Check for an existing `id` on the same delta first, reuse it:
```bash
jq -c --arg i "<id>" 'select(.id==$i)' .claude/clio/debt.jsonl
```

One append, all 14 fields — no read-modify-write, so concurrent sessions can't clobber each other:
```bash
echo '{"date":"YYYY-MM-DD","id":"<kebab-key>","kind":"spec-delta","status":"pending","domain":"checkout","what":["…"],"req":[18],"specs":[".claude/docs/specs/memory/<file>.md"],"docs":["…"],"code":["…"],"action":"…","source":"…","blocked_by":null,"issue":null}' >> .claude/clio/debt.jsonl
```
Verify the line parses and carries the required fields:
```bash
tail -1 .claude/clio/debt.jsonl | jq -e '.id and .kind and .status and (.what|length>0)
  and (has("blocked_by"))' >/dev/null && echo OK || echo BAD
```

---

# Step 3b — Move the `requirements.md` row if the delta changed the *decision*

You're the only writer of `.claude/docs/specs/` — stale marker is yours to fix. Left alone,
`clio-context` keeps stopping future sessions to "ask the customer" about a point already settled.

For each row in this delta's `req`, compare marker vs what the spec now says:

| Marker now | Delta means | Do |
|---|---|---|
| ⚠️ / ❌ | the open point got decided | flip to ✅, replace reason text with decision + date |
| ⚠️ / ❌ | a *different* part of the row is still open | keep marker, rewrite reason to name what's actually open |
| ✅ | a settled point was re-opened/reversed | flip to ⚠️, say what re-opened it and where |
| ✅ | refinement of an already-decided point | keep ✅, append new decision + date |

Two hard rules: **decisions only, never build state** (code blockers, "implemented but pending
review" belong in `debt.jsonl`, joined via `req`). **Never flip ⚠️→✅ off a low-priority source** —
apply § Source priority; a point confirmed only second-hand, or carrying a "re-verify"
note, stays ⚠️, `debt.jsonl` record keeps non-null `blocked_by`. Marker and `blocked_by` must tell
same story — say so in final report if you can't reconcile them.

Next: `WRAP-UP.md`.
