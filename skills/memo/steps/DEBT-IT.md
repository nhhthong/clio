# Step 4 — Log open items: `debt.jsonl`

`index.jsonl` = what was built, `debt.jsonl` = what is owed. Keyed by `id`, append-only, last line per `id` wins. Write with `clio add debt`: a record names only what is its own or what changes, the rest is carried over, the lines are validated and removed again on a `FAIL`. Never edit a line by hand.

## 1. Close what this run finished
`clio q owed --req <req>` (and what `clio:context` flagged for the area, not only your diff). Resolved → `{"id":"<id>","status":"done","action":"…<commit hash>"}`. Partly → `{"id":"<id>","status":"in-process","what":["<what is left>"]}`. Unblocked but not finished → `{"id":"<id>","blocked_by":null}`.

**A `spec-delta` names the docs it invalidated in `docs[]`.** Closing or narrowing one, relabel the section the change made untrue in every doc of that list that this run did not write: `clio doc` with `"relabel":[…]` (`## [SUPERSEDED date] … — REVERTED, DO NOT RE-IMPLEMENT`; the body stays). Skip it and `clio:context` keeps serving a doc about code that is gone. Cannot tell which section went stale → file a `doc-stale` record naming the doc, and say so. A withdrawn task: `RARE.md`.

## 2. Was this run verified?
Verification is `/clio:test`'s evidence, never your account of it. For each id in `plan_tasks`: `clio test gate <id>`.
- `OK` → `clio test tick <id>` (+ `--commit <hash>` if step 1 found one): it gates again and records the task done, the only way a task becomes done. Put the `OK` line in `testing`.
- Anything else → leave it open, file an `unverified` record naming the FAIL lines, tell the user `/clio:test <id>` is owed. A `flaky —` line is `code-debt` with `what` starting `flaky:`.
- `plan_tasks` empty → no gate; `unverified` unless the user names the check that ran. Never tick a task step 1 was unsure about.

## 3. New records
One per `## Follow-up` bullet that outlives this session, grouped by problem, never mixing kinds. The same problem as an existing record → reuse its `id` (`clio q owed --all --id <id>`).

| `kind` | Meaning |
|---|---|
| `code-debt` | known-wrong code; `what` starts `perf:` or `flaky:` when that is the nature |
| `unverified` | shipped, never verified by a test, build or recorded manual run |
| `doc-stale` | a doc describes something untrue |
| `spec-delta` | spec moved, code hasn't (`/clio:ingest` writes these) |
| `spec-blocked` | waits on an outside answer; the filing record names it in `blocked_by`, a later line nulls it |

A **new** record names `id`, `kind`, `domain`, `what`, plus what it has: `req` (strings, `["7.10"]`), `specs`, `docs` (incl. this run's), `code`, `action` (best-guess fix), `source`, `blocked_by` (the concrete missing thing, or null), `issue` (a related `id`). `status` starts `pending`, `date` is today; the rest start empty.
Write the records with `clio add debt`, JSON objects on stdin, one per line. An update names the `id` and the changed fields, for example `id` plus `status` done.
Several records go in one call; one bad record refuses all. A `spec-blocked` must name its blocker when filed.

## 4. Ledger honesty, this area only
An open or blocked row you served with no open record: write one. A record whose `blocked_by` was answered long ago, or a reverted fix filed as `spec-blocked` → update it. Records outside this area: leave alone, mention in the report.

Next: `WRAP-UP.md`.
