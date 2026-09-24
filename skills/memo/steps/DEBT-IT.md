# Step 4 — Log open items: `.claude/clio/database/debt.jsonl`

`index.jsonl` = what was built, `debt.jsonl` = what is owed. Keyed by `id`, **append-only**: an
update is a new line under the same `id` restating the record **in full** (readers take the last
line per `id`, so a field you leave out is a field you erased). Never rewrite, reorder or delete a
line.

## 1. Close what this run finished

```bash
q.sh owed --req <req>
```
Fully resolved → append with `status:"done"`, and the commit hash, if any, in `action`. Partly → `status:"in-process"`,
narrow `what` to what is left. Unblocked but not finished → `blocked_by:null`, keep `status`. Include
the items `clio:context` flagged for this area, not only your diff.

**A `spec-delta` also names the docs it invalidated, in `docs[]`.** `/clio:ingest` put them there
because it read them to work out the delta. Closing or narrowing one, open every doc in that list
that is **not** the doc this run wrote, and relabel the section the change made untrue —
`## [SUPERSEDED YYYY-MM-DD] <heading>`, plus `— REVERTED, DO NOT RE-IMPLEMENT` when the code is gone
(`WRITE-DOC.md` § UPDATE). Keep the body; it is still the record of what was built and why.

Skip this and hop 2 keeps returning that doc as current state, because nothing in a ledger record
says its subject was replaced — a reader asking how the feature works opens a doc describing code
this run just removed. Cannot tell which section went stale → file a `doc-stale` record naming the
doc rather than guessing, and say so in the report.

## 2. Was this run verified?

Verification is `/clio:test`'s evidence, never your account of it. For each id in `plan_tasks`:
```bash
clio-test.sh gate <task-id>
```
- `OK` → tick `[x] YYYY-MM-DD` (+ ` <hash>` if any) on that exact row in `.claude/clio/docs/plans/<area>.md`, in
  place, and paste the `OK` line under `## Testing Done`.
- Anything else → leave `[ ]`, file an `unverified` record naming the gate's FAIL lines, and tell the
  user `/clio:test <task-id>` is owed. A failing case repeated-red-then-green is `code-debt` with
  `what` starting `flaky:`.
- `plan_tasks` empty (work outside any plan) → no gate to run; `unverified` unless the user names the
  check that ran. Never tick a row step 1 was unsure about.

## 3. New records

One per `## Follow-up` bullet that outlives this session. Existing `id` for the same problem →
reuse it (`q.sh owed --all --id <id>`); else pick a new one.
Group by problem, never mix kinds in one record.

| `kind` | Meaning |
|---|---|
| `code-debt` | known-wrong code; prefix `what` with `perf:` or `flaky:` when that is the nature |
| `unverified` | shipped, never verified by any test, build or recorded manual run |
| `doc-stale` | a doc describes something untrue |
| `spec-delta` | spec moved, code hasn't — `/clio:ingest` writes these |
| `spec-blocked` | waiting on an outside answer — the filing record names it in `blocked_by`; a later line nulls it once unblocked (§ 1) |

All 14 fields, always present (`null` / `[]`, never omitted):

| Field | Meaning |
|---|---|
| `date` | today |
| `id` | short kebab-case key, stable across updates |
| `kind` | one of the five above |
| `status` | `pending` / `in-process` / `done` |
| `domain` | same vocabulary as `index.jsonl` |
| `what` | array — what is actually wrong or unclear |
| `req` | `requirements.md` rows this blocks, as strings (`["7.10"]`), `[]` if none |
| `specs` | spec file paths this depends on |
| `docs` | task/decision docs where it was raised, incl. this run's |
| `code` | files/paths that must change, `[]` only if genuinely unknown |
| `action` | best-guess fix, 1–2 sentences |
| `source` | where it came from (thread, meeting, `<doc> #n`), `null` if own work |
| `blocked_by` | the concrete missing thing, or `null` |
| `issue` | related `id` in this file, else `null` |

```bash
cat >> .claude/clio/database/debt.jsonl <<'EOF'
{"date":"YYYY-MM-DD","id":"<kebab-key>","kind":"code-debt","status":"pending","domain":"cart","what":["<what is wrong>"],"req":["15"],"specs":[".claude/clio/docs/specs/memory/products-pricing.md"],"docs":[".claude/clio/docs/tasks/<feature>/<id>_<name>.md"],"code":["app/Services/CartService.php:52"],"action":"<fix>","source":null,"blocked_by":null,"issue":null}
EOF
validate.sh debt
```
`FAIL` → `sed -i.bak '$d' .claude/clio/database/debt.jsonl && rm .claude/clio/database/debt.jsonl.bak`, fix, re-append.

## 4. Ledger honesty, scoped to this area only

A ⚠️/❌ row you served with no open record tracking it → write one. A record in this area whose
`blocked_by` was answered long ago, or a reverted fix filed as `spec-blocked` → append a corrected
line under the same `id`. Records outside this area → leave alone, mention in the report.

Next: `WRAP-UP.md`.
