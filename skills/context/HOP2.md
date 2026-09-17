# Hop 2 — what was already built (`.claude/clio/index.jsonl`)

Append-only, written by `/clio:memo`. Every record is a document record (`type` `task`/`adr`)
carrying `id`, `doc`, `domain`, `keywords`, `files`, `commits`, `specs`, `req`, `plan_tasks`. Open
items aren't here — see [HOP3.md](HOP3.md).

**One record per run; the last record per `id` is the doc's full current state.** `id` is the doc's
creation timestamp and its filename prefix — it never changes, so a moved or renamed doc is still
the same `id` with a new `doc` path. Every field is restated in full each run: `files` is every
source file the doc covers, `req`/`specs` its full current claim (retractable to `[]`). Earlier
records are the timeline — read them for "what changed when", never merge them.

**Group with the bridge, never on `.id` alone.** Pre-3.0 records carry no `id` and key on their path.
`group_by(.id)` drops every one of them into a single `null` bucket whose `last` is an arbitrary old
record — on a migrated repo that answers "which doc touched X?" with a path that no longer exists.
The bridge maps a path to the id that later claimed it, by `doc` (the doc stayed put) or by
`supersedes` (it moved), so each document is one group either way:

```bash
G='(map(select(.id)|{key:.doc,value:.id}) + map(select(.supersedes)|{key:.supersedes,value:.id})
    | from_entries) as $m | group_by(.id // $m[.doc] // .doc)'

# current state, one line per doc
jq -s -c "$G"'[] | last' .claude/clio/index.jsonl

# by requirement (from hop 1) / spec / file / area / keyword / plan task — always on current state
jq -s -c "$G"'[] | last | select(.req[]? == 5)' .claude/clio/index.jsonl
jq -s -c "$G"'[] | last | select(.specs[]? | contains("order-flow"))' .claude/clio/index.jsonl
jq -s -c "$G"'[] | last | select(.files[]? | contains("ProductRepo"))' .claude/clio/index.jsonl
jq -s -c "$G"'[] | last | select(.domain=="account" or (.keywords[]? == "i18n"))' .claude/clio/index.jsonl
jq -s -c "$G"'[] | last | select(.plan_tasks[]? == "3.3")' .claude/clio/index.jsonl

# what one run changed: diff a doc's last two records
jq -s -c --arg i "<id>" 'map(select(.id==$i)) | {date:.[-1].date, added:(.[-1].files - (.[-2].files // [])), removed:((.[-2].files // []) - .[-1].files)}' .claude/clio/index.jsonl
```
`jq: error … Invalid …` on either ledger → a malformed line, not an empty ledger. Say so, point at
`validate.sh all` (it names the line), and never report "nothing on record" off a query that errored.

`req`/`specs` are the join to the requirement but not infallible — `req` the weaker of the two:
inherited bugs, RBAC, infra structurally map to no requirement row, so `req:[]` can be legitimate.
Prefer `specs`, fall back to `domain`/`keywords`/`files`.

**Then read the load-bearing sections, not the whole doc.** `## Summary` hides what matters, and a
long-lived doc costs a lot to open whole:
```bash
awk '/^## /{p = /^## (Decisions|Side Effects|Follow-up)/} p' <doc>
```
`## Decisions` holds the constraints, `## Side Effects` what you can break, `## Follow-up` what was
knowingly left unfinished — a doc's most expensive-to-rediscover content is at the bottom. Open the
file whole only when those sections point you at something they don't contain.

`ls` is free context: `ls .claude/docs/tasks/` names the features, `ls .claude/docs/tasks/<feature>/`
names its sub-tasks. Use it before opening anything.

**If a query hits a record that looks off** — a `doc` path missing on disk, an unfamiliar `domain`,
or a file not on disk: for a moved doc, the current path is in that `id`'s **last** record, so
re-run the query with `group_by(.id) | last` before concluding anything. Records written before
Clio 3.0 have no `id` and key on `doc`; pre-2.0 ones hold only that run's delta in `files`/`keywords`
and a scalar `commit`. `validate.sh all` names both — `/clio:migrate` migrates them.

Next: [HOP3.md](HOP3.md).
