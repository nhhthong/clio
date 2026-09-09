# Step 5 — Log open items: `.claude/clio/debt.jsonl`

`index.jsonl` = what was built, `debt.jsonl` = what is owed. Keyed by `id`, **append-only**: an
update is a new line under the same `id` restating the record **in full** (readers take the last
line per `id`, so a field you leave out is a field you erased). Never rewrite, reorder or delete a
line.

## 1. Close what this run finished

```bash
jq -s -c --argjson n <req> 'group_by(.id)[] | last
  | select((.req[]? == $n) and .status!="done") | {id, kind, status, what, code}' .claude/clio/debt.jsonl
```
Fully resolved → append with `status:"done"`, commit hash in `action`. Partly → `status:"in-process"`,
narrow `what` to what is left. Unblocked but not finished → `blocked_by:null`, keep `status`. Include
the items `clio:context` flagged for this area, not only your diff.

## 2. Was this run verified?

A test, a build, or a manual check recorded with today's date in `## Testing Done`. None of those →
write an `unverified` record for it before anything else. `index.jsonl` says what was claimed; only
a dated `## Testing Done` entry or an `unverified` record says whether anyone looked.

Plan task noted in step 2 → its `Test` ran and is in `## Testing Done` → tick `[x] YYYY-MM-DD
<commit>` in `.claude/docs/plans/<area>.md`, in place. Did not run → leave `[ ]`; the `unverified`
record above covers it. Never tick on the strength of the code alone.

## 3. New records

One per `## Follow-up` bullet that outlives this session. Existing `id` for the same problem →
reuse it (`jq -c --arg i "<id>" 'select(.id==$i)' .claude/clio/debt.jsonl`); else pick a new one.
Group by problem, never mix kinds in one record.

| `kind` | Meaning |
|---|---|
| `code-debt` | known-wrong code; prefix `what` with `perf:` or `flaky:` when that is the nature |
| `unverified` | shipped, never verified by any test, build or recorded manual run |
| `doc-stale` | a doc describes something untrue |
| `spec-delta` | spec moved, code hasn't — `/clio:update` writes these |
| `spec-blocked` | waiting on an outside answer — the only kind with a non-null `blocked_by` |

All 14 fields, always present (`null` / `[]`, never omitted):

| Field | Meaning |
|---|---|
| `date` | today |
| `id` | short kebab-case key, stable across updates |
| `kind` | one of the five above |
| `status` | `pending` / `in-process` / `done` |
| `domain` | same vocabulary as `index.jsonl` |
| `what` | array — what is actually wrong or unclear |
| `req` | `requirements.md` rows this blocks, `[]` if none |
| `specs` | spec file paths this depends on |
| `docs` | task/decision docs where it was raised, incl. this run's |
| `code` | files/paths that must change, `[]` only if genuinely unknown |
| `action` | best-guess fix, 1–2 sentences |
| `source` | where it came from (thread, meeting, `<doc> #n`), `null` if own work |
| `blocked_by` | the concrete missing thing, or `null` |
| `issue` | related `id` in this file, else `null` |

```bash
echo '{"date":"YYYY-MM-DD","id":"<kebab-key>","kind":"code-debt","status":"pending","domain":"cart","what":["<what is wrong>"],"req":[15],"specs":[".claude/docs/specs/memory/products-pricing.md"],"docs":[".claude/docs/tasks/YYYY-MM-DD_<doc>.md"],"code":["app/Services/CartService.php:52"],"action":"<fix>","source":null,"blocked_by":null,"issue":null}' >> .claude/clio/debt.jsonl
"${CLAUDE_PLUGIN_ROOT}"/skills/memo/scripts/validate.sh debt
```
`FAIL` → `sed -i.bak '$d' .claude/clio/debt.jsonl && rm .claude/clio/debt.jsonl.bak`, fix, re-append.

## 4. Ledger honesty, scoped to this area only

A ⚠️/❌ row you served with no open record tracking it → write one. A record in this area whose
`blocked_by` was answered long ago, or a reverted fix filed as `spec-blocked` → append a corrected
line under the same `id`. Records outside this area → leave alone, mention in the report.

Next: `WRAP-UP.md`.
