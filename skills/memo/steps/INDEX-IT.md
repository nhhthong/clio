# Step 3 — Index it: `.claude/clio/database/index.jsonl`

Append-only, one line per document **every run** — UPDATE runs too; a doc's lines are its timeline.
Never rewrite, reorder or delete an existing line, including this doc's own earlier runs.

**`id` is the key, not the path.** `id` is the Unix timestamp the doc was created at, and it is also
the doc's filename prefix (`1789430400_loyalty-lookup.md`). It never changes — not when the doc
moves, not when it is renamed. Readers take the last line per `id`.

**Every field restates the doc's full current state.** A field you leave out or leave short is a
field you erased. Start from the previous record and edit it:
```bash
clio q history <id> | tail -2    # the previous record, then what it last changed
```

Before picking `keywords`, read the vocabulary this repo already uses:
```bash
clio q keywords
```
A concept already in that list → **reuse that exact word**, never a variant (`loyalty` vs
`loyalty-program` vs `khach-hang-than-thiet` are three dead ends for the same search). Add a new word
only for a genuinely new concept, and say so in the report — same rule as `domain` below.

Append with a quoted heredoc — a `'` inside a value breaks `echo '…'`, a heredoc does not (paths and
domain below are placeholders — use this repo's real ones):
```bash
cat >> .claude/clio/database/index.jsonl <<'EOF'
{"date":"YYYY-MM-DD","id":"1789430400","type":"task","doc":".claude/clio/docs/tasks/orders/1789430400_order-list.md","domain":"account","plan_tasks":["3.1"],"files":["src/orders/order-service.ts","src/orders/order-repo.ts"],"commits":["3f2a1c","9b0e77"],"keywords":["orders","pagination"],"specs":[".claude/clio/docs/specs/memory/ui-design.md"],"req":["2"]}
EOF
```

| Field | Rule |
|---|---|
| `date` | today |
| `id` | the doc's creation timestamp (`date +%s` at CREATE), as a string. Same value as the filename prefix. **Never changes** |
| `type` | `task` or `adr` |
| `doc` | the doc's current path. A moved or renamed doc keeps its `id` and gets a new `doc` here |
| `domain` | one term from the `Domains:` line of `.claude/clio/docs/specs/requirements.md` — by business area served, not directory. New term needed → ask, add it there on a yes, say so in the report |
| `plan_tasks` | the plan task ids this doc implements (`["3.1"]`), `[]` for work outside any plan. An array for the same reason `req` is: one doc can carry several. Unsure whether an id belongs → write `[]`, never guess one in; a wrong id makes `/clio:memo` tick a task nobody tested, and `clio validate` rejects an id no plan holds |
| `files` | every source file the doc still covers: previous list + this run's, minus what was reverted. Repo-relative, build output excluded |
| `commits` | previous list + this run's hash, if step 1 found one (`SKILL.md` § Commits) |
| `keywords` | previous list + new ones, from the vocabulary above |
| `fp` | `clio test fp` at the moment of this run (12 characters), so the next `clio q changed` can say nothing moved since. Optional: records from before 5.0 have none, and a backfill run copies the previous one |
| `req`, `specs` | the doc's full current claim, `req` as strings (`["7.10"]`); `specs` only what `requirements.md` maps `req` to, never a plausible-looking spec |

Validate — never declare done on a line it rejects:
```bash
clio validate index
```
Appended several (a backfill) → `clio validate index <N>`. `FAIL` → remove exactly the lines you
appended (`sed -i.bak '$d'` once per line, then `rm` the `.bak`), fix, re-append.

## Chore

A commit the user says is no task's work — CI config, tooling, a hand-made dependency bump — gets
one record instead of a doc, so `clio q unrecorded` and the drift hook stop naming it. It is only
skipped, never a stopping point: work older than it is still reported.
```bash
cat >> .claude/clio/database/index.jsonl <<'EOF'
{"date":"YYYY-MM-DD","id":"<full hash>","type":"chore","commits":["<hash>"],"note":"<why no task owns it, in the user's words>"}
EOF
clio validate index
```
Only on the user's word, one commit at a time — never to quiet the hook.

Next: `DEBT-IT.md`.
