# Hop 3: what is still open

Ledger: `.claude/clio/database/debt.jsonl`. Every open item lives here. `/clio:ingest` writes spec-moved-code-has-not deltas, and `/clio:memo` writes leftover business from a completed run. Keyed by `id`, one line per `id`.

## Queries
- `clio q owed --req 18` for the row hop 1 gave you. Start here; the work queue comes first.
- `clio q owed --area account --spec order-flow --req 20` widens the search: pair domain with specs and req.
- `clio q owed --q "<word>"` answers "what do I owe?". Omit `--q` for everything open.

## Read two fields first
- `blocked_by` is the only field that decides whether you may act. Null means actionable now. Anything else means something external is missing (an answer from the customer or PO, an upstream field, a sample file). Do not start the item, and say what it waits on.
- `kind`: `spec-delta` (spec moved, code has not), `spec-blocked` (waiting on an outside answer), `code-debt` (known-wrong code; a `perf:` or `flaky:` prefix in `what`), `unverified` (shipped, never verified by a test, build or recorded manual run), `doc-stale` (a doc describes something untrue).

A `code-debt` or `spec-delta` with `blocked_by: null` in your area is a live landmine and your work queue at once. Surface it before you start.

`docs` on a `spec-delta` names the task docs the change invalidated. Hop 2 hands you those same docs as current state, and until the rework lands they are current, because the code they describe is still there. Say which docs a delta targets, so nobody reads a doc's `## Decisions` as the pattern to follow when a plan task exists to undo it.

## Report what is owed
When asked plainly, report two groups in this order, with `blocked_by` alone deciding which:
- Actionable now (`blocked_by` null): `id`, `kind`, what, and the first entry of `code`. This is the work queue.
- Blocked, with what each waits on, said plainly as must-not-start.

Close with one line on `in-process` records nothing has touched in a while, and on any `spec-blocked` whose `blocked_by` names a row that hop 1 now shows as decided. Flag those; `/clio:memo` and `/clio:ingest` re-file them.

Then continue with the report in `SKILL.md`.
