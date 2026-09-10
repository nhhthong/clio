# Hop 2 — what was already built (`.claude/clio/index.jsonl`)

Append-only, written by `/clio:memo`. Every record is a document record (`type` `task`/`adr`)
carrying `domain`, `keywords`, `files`, `commits`, `specs`, `req`. Open items aren't here — see [HOP3.md](HOP3.md).

**One record per run; the last record per `doc` is the doc's full current state.** Every field is
restated in full each run: `files` is every source file the doc covers, `req`/`specs` its full
current claim (retractable to `[]`). Earlier records are the timeline — read them for "what changed
when", never merge them.

```bash
# current state, one line per doc
jq -s -c 'group_by(.doc)[] | last' .claude/clio/index.jsonl

# by requirement (from hop 1) / spec / file / area / keyword — always on current state
jq -s -c 'group_by(.doc)[] | last | select(.req[]? == 5)' .claude/clio/index.jsonl
jq -s -c 'group_by(.doc)[] | last | select(.specs[]? | contains("order-flow"))' .claude/clio/index.jsonl
jq -s -c 'group_by(.doc)[] | last | select(.files[]? | contains("ProductRepo"))' .claude/clio/index.jsonl
jq -s -c 'group_by(.doc)[] | last | select(.domain=="account" or (.keywords[]? == "i18n"))' .claude/clio/index.jsonl

# what one run changed: diff a doc's last two records
jq -s -c 'map(select(.doc=="<doc>")) | {date:.[-1].date, added:(.[-1].files - (.[-2].files // [])), removed:((.[-2].files // []) - .[-1].files)}' .claude/clio/index.jsonl
```
`req`/`specs` are the join to the requirement but not infallible — `req` the weaker of the two:
inherited bugs, RBAC, infra structurally map to no requirement row, so `req:[]` can be legitimate.
Prefer `specs`, fall back to `domain`/`keywords`/`files`.

**Then read the matching docs' load-bearing sections, not the summary.** `## Summary` hides what
matters. Go to `## Decisions` (constraints), `## Side Effects` (what you can break), `## Follow-up`
(knowingly left unfinished) — a doc's most expensive-to-rediscover content is at the bottom.

**If a query hits a record that looks off** — missing `doc`, unfamiliar `domain`, or pointing at a
file not on disk: a `doc` path missing on disk means the doc was renamed; look for a later record
carrying `"supersedes":"<the old path>"`, which names the current file. Records written before
Clio 2.0 hold only that run's delta in `files`/`keywords` and a scalar `commit` — `validate.sh all`
warns; migrate per CHANGELOG 2.0.0 rather than reading them as current state.

Next: [HOP3.md](HOP3.md).
