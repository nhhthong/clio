# Step 3 — Index it: `index.jsonl`

One line per document **every run**, UPDATE runs too; the last line per `id` is the doc's current state, earlier ones its history. `id` is the doc's creation timestamp and filename prefix (`1789430400_loyalty-lookup.md`); it never changes, not when the doc moves.

```bash
clio add index <<'EOF'
{"id":"1789430400","type":"task","doc":".claude/clio/docs/tasks/orders/1789430400_order-list.md","domain":"account","plan_tasks":["3.1"],"files":["src/orders/order-service.ts"],"keywords":["orders","pagination"],"specs":[".claude/clio/docs/specs/memory/ui-design.md"],"req":["2"],"fp":"<clio test fp>"}
EOF
```
- **A record names only what is its own.** A new doc names `type`, `doc`, `domain`, `keywords` and what it claims (`date` is today; `commits`, `plan_tasks`, `files`, `req`, `specs` start empty). An **update** names the `id` and what changed; the rest is carried over. A list is replaced whole: give the full new `files` or `commits`.
- **It checks before it keeps**: the lines are appended, `clio validate` runs on exactly them, a `FAIL` removes them again (`nothing written`). Several docs in one call are validated together; one bad record refuses all. A `'` in a value is fine in a quoted heredoc.

| Field | Rule |
|---|---|
| `id` | the doc's creation timestamp as a string, equal to the filename prefix. Left out → taken from `doc`'s filename |
| `type` | `task` or `adr` |
| `doc` | the doc's current path (a moved doc keeps its `id` and gets a new `doc`) |
| `domain` | one term of the report's `domains:` line (from `requirements.md`; never grep for it), by business area, not directory. A new term → ask, add it there on a yes, say so in the report |
| `plan_tasks` | the plan task ids this doc implements, `[]` outside any plan. Unsure → `[]`, never guess: a wrong id makes memo tick a task nobody tested, and `clio validate` rejects an id no plan holds |
| `files` | every source file the doc still covers: previous + this run's, minus what was reverted; repo-relative, no build output |
| `commits` | previous + this run's hash, if step 1 found one |
| `keywords` | previous + new, **from the report's vocabulary**: reuse the exact word, never a variant (`loyalty` vs `loyalty-program` are two dead ends for one search); a new word only for a new concept, said in the report |
| `fp` | `clio test fp` now (12 chars): the next `q changed` / `q gather` can say nothing moved since. Optional; a backfill leaves the previous one |
| `req`, `specs` | the doc's full current claim, `req` as strings (`["7.10"]`); `specs` left out → filled from what `requirements.md` maps `req` to |

Next: `DEBT-IT.md`.
