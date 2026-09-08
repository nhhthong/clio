# Hop 3 — what is still open (`.claude/clio/debt.jsonl`)

Every open item lives here: `/clio-update` writes spec-moved-code-hasn't deltas, `/clio-memo`
writes leftover business from a completed run. Keyed by `id`, one line per `id`.

```bash
# the row hop 1 gave you — start here
N=18
jq -s -c --argjson n $N 'group_by(.id)[] | last
  | select((.req[]?==$n) and .status!="done")
  | {id, kind, blocked:(.blocked_by!=null), action}' .claude/clio/debt.jsonl

# widen by area — pair domain with specs/req, never filter on domain alone (some records lack it)
jq -s -c 'group_by(.id)[] | last | select(.status!="done")
  | select(.domain=="account" or (.specs[]? | contains("order-flow")) or (.req[]? == 20))' \
  .claude/clio/debt.jsonl
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

Then hop 4 (coverage) and Report, back in `SKILL.md`.
