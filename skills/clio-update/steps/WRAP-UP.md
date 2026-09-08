# Step 4 — Unblock what this delta just answered

A delta you just recorded may be the missing answer another open record was waiting on. Check open
items on the same rows (`WHAT-CHANGED.md` query); for each one this delta resolves, **append a new line under the
same `id`** restating the record in full with `blocked_by: null` (append-only, per
`APPEND-DEBT.md`) — never edit or delete the earlier line.

Two boundaries: don't change a record's `kind` (`spec-blocked` stays `spec-blocked` — re-filing as
`code-debt` is `/clio-memo`'s call). `index.jsonl` isn't yours — `req`/`specs` looks wrong in
light of this delta → report it, don't touch the file.

# Step 5 — Report

List each delta: id · status · `blocked_by` · row · one-line action. Group `blocked_by: null` first
(the queue). Then state plainly:
- deltas you couldn't date (no before-state recoverable);
- what's blocked, on exactly what;
- records you unblocked above;
- every `requirements.md` row moved, old → new + source that justified it, plus any row deliberately left
  ⚠️ because only a low-priority source backs the change;
- any `index.jsonl` record whose `req`/`specs` this delta shows wrong (report only — not your file).
