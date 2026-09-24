# Hop 3 — what is still open (`.claude/clio/database/debt.jsonl`)

Every open item lives here: `/clio:ingest` writes spec-moved-code-hasn't deltas, `/clio:memo`
writes leftover business from a completed run. Keyed by `id`, one line per `id`.

```bash
q.sh owed --req 18                  # the row hop 1 gave you — start here; queue first
q.sh owed --area account --spec order-flow --req 20   # widen: pair domain with specs/req
q.sh owed --q "<word>"              # "what do I owe?" — omit --q for everything open
```

Read two fields first:
- **`blocked_by`** — the only thing deciding whether you may act. `null` = actionable now. Non-null
  = something external missing (an answer from the customer/PO, an upstream field, a sample file) —
  don't start it, say what it's waiting on.
- **`kind`** — `spec-delta` (spec moved, code hasn't), `spec-blocked` (waiting on an outside answer),
  `code-debt` (known-wrong code; `perf:`/`flaky:` prefix in `what`), `unverified` (shipped, never
  verified by any test, build or recorded manual run), `doc-stale` (doc describes
  something untrue).

`code-debt` or `spec-delta` with `blocked_by: null` in your area is a live landmine and your work
queue simultaneously — surface it before you start.

`docs` on a `spec-delta` names the task docs the change invalidated. Hop 2 will hand you those same
docs as current state, and until the rework lands they *are* current — the code they describe is
still there. Say which ones a delta targets, so nobody reads a doc's `## Decisions` as the pattern to
follow when a plan task exists to undo it.

Asked plainly for what is owed, report two groups in this order, `blocked_by` alone deciding which:
**actionable now** (`blocked_by: null`) — `id` · `kind` · what · first entry of `code`, the work
queue — then **blocked**, with what each waits on, said plainly as must-not-start. Close with one
line on `in-process` records nothing has touched in a while, and any `spec-blocked` whose
`blocked_by` names a row hop 1 now shows ✅. Flag those; `/clio:memo` and `/clio:ingest` re-file them.

Then hops 4–5 and Report, back in `SKILL.md`.
