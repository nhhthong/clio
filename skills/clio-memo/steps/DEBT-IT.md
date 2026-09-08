# Step 5 — Log open items: `.claude/clio/debt.jsonl`

`index.jsonl` = what built, `debt.jsonl` = what's owed — share `req`/`specs`/`domain`, one query
returns both. `/clio-update` also writes here — keyed by `id`. **APPEND ONLY**, same as
`index.jsonl`: updating an existing `id` means appending a new line, never rewriting one. Readers
take the last line per `id` (`group_by(.id) | last`), so the newest line is current state and the
older lines are that item's history. Never rewrite, reorder or delete existing lines.

**First, close what this run finished** (before logging new):
```bash
jq -s -c --argjson n <req> 'group_by(.id)[] | last
  | select((.req[]? == $n) and .status!="done") | {id, kind, status, what, code}' \
  .claude/clio/debt.jsonl
```
Fully resolved → append a line with `status:"done"`, commit hash in `action`. Partly resolved →
`status:"in-process"`, narrow `what` to what's left. Unblocked not finished → `blocked_by:null`, keep
`status`. **Every append restates the record in full** — readers only ever read the last line, so a
field you leave out is a field you erased. Check `clio-context`-flagged items too, not just your
diff.

**Verification is not optional.** Before logging anything else: did this run's work actually run —
test, build, or a manual check recorded in `## Testing Done` with today's date? If not, write an
`unverified` record for it. An `index.jsonl` line says what was claimed; only a dated `## Testing
Done` entry or an `unverified` record says whether anyone looked.

**New record:** each `## Follow-up` bullet outliving this session. Check existing first — found →
reuse that `id` (your append *is* its update), not found → pick a new `id`:
```bash
jq -c --arg i "<id>" 'select(.id==$i)' .claude/clio/debt.jsonl
```
Five `kind`s: `code-debt` (wrong code), `unverified` (shipped, never verified — no test, no build,
no recorded manual run; whatever "verified" means in this project: unit/integration test, a device
run, a playtest, a load test), `doc-stale` (doc≠reality), `spec-delta` (spec moved, code hasn't —
`/clio-update`'s job), `spec-blocked` (waiting on outside answer, only one with non-null
`blocked_by`). Group by problem not bullet — never mix `kind`s.

**Performance and flakiness are `code-debt`**, prefixed in `what` so a query can find them:
`"perf: frame time 22ms over the 16ms budget"`, `"flaky: integration suite fails ~1 run in 8"`.
A sixth `kind` would buy nothing a prefix doesn't.

**Fields** (all 14, always present — `null`/`[]` not omission):

| Field | Meaning |
|---|---|
| `date` | today |
| `id` | short kebab-case key, stable across updates (join key) |
| `kind` | `spec-delta` / `spec-blocked` / `code-debt` / `unverified` / `doc-stale` |
| `status` | `pending` / `in-process` / `done` |
| `domain` | same controlled vocabulary as index records |
| `what` | array — what's actually wrong/unclear |
| `req` | requirements.md row numbers this blocks, `[]` if none |
| `specs` | `.claude/docs/specs/memory/*.md` (or requirements.md) paths this depends on |
| `docs` | task/decision doc paths where it was raised, incl. this run's target |
| `code` | concrete files/paths that must change, `[]` only if genuinely unknown |
| `action` | best-guess fix, 1-2 sentences |
| `source` | where it came from (meeting recording, chat thread, `<source doc> #n`), `null` if own work |
| `blocked_by` | concrete external blocker, or `null` |
| `issue` | related `id` in this file, else `null` |

**One append, all 14 fields** — the paths and domain in the example are placeholders, use this
repo's real ones:
```bash
echo '{"date":"YYYY-MM-DD","id":"<kebab-key>","kind":"spec-blocked","status":"pending","domain":"cart","what":["<what is actually wrong or unclear>"],"req":[15],"specs":[".claude/docs/specs/memory/products-pricing.md"],"docs":[".claude/docs/tasks/YYYY-MM-DD_<doc>.md"],"code":["app/Services/CartService.php:52"],"action":"<1-2 sentence best-guess fix>","source":null,"blocked_by":"<the concrete missing thing>","issue":null}' >> .claude/clio/debt.jsonl
```
A single `>>` of one line is atomic enough for concurrent sessions — nothing is read-modify-written,
so nobody clobbers anybody. Old lines for the same `id` stay: they are the history, and `git log`
still recovers a detail you narrowed away.

**Validate the appended line:**
```bash
tail -1 .claude/clio/debt.jsonl | jq -e '.id and .kind and .status and (.what|length>0)
  and (.req|type=="array") and (.specs|type=="array") and (.code|type=="array")
  and (has("blocked_by"))' >/dev/null && echo OK || echo BAD
```
`BAD` or a parse error → `sed -i '$d'` to drop the line, re-append correctly.

Current state per item:
```bash
jq -s -c 'group_by(.id)[] | last | select(.status!="done")' .claude/clio/debt.jsonl
```

## Ledger honesty check

**Condition:** an `req` row served (`GATHER-FACTS.md`) is ⚠️/❌, or area has known open debt. Never
sweep the whole project — scope to what you worked on.

**1. ⚠️/❌ row with nothing tracking it** → write a new debt record (`kind` per table above):
```bash
jq -s -c --argjson n <req> 'group_by(.id)[] | last
  | select((.req[]? == $n) and .status!="done")' .claude/clio/debt.jsonl
```

**2. Record in this area is stale** — re-read its `specs` files, then append a fresh line under the
**same `id`** with corrected `status`/`blocked_by`/`action` (full restatement, per above):
```bash
jq -s -c 'group_by(.id)[] | last | select(.domain=="<domain>" and .status!="done")' \
  .claude/clio/debt.jsonl
```
Two traps: `blocked_by` already answered (nobody re-read) — clear it, re-file `code-debt`/`done`;
reverted fix filed as `spec-blocked` — nothing external missing, re-file `code-debt`.

Records outside this area → leave alone, mention in final report.

Next: `WRAP-UP.md`.
