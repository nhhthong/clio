# Hop 2 — what was already built (`.claude/clio/index.jsonl`)

Append-only, written by `/clio-memo`. Every record is a document record (`type` `task`/`adr`)
carrying `domain`, `keywords`, `files`, `specs`, `req`. Open items aren't here — see [HOP3.md](HOP3.md).

**A doc gets one record per run; most array fields are that run's *delta*, not current state.**
`files`/`keywords`/`commit` — union across records (a doc's last record may list 4 files of its
real 30+).

**`req`/`specs` are the exception — take last, never union.** They're the doc's full current claim,
restated every run (`[2,3]` later restated as `[2,3,8]`, never the delta `[8]`), and therefore
retractable to `[]` + a `note`. Unioning defeats a retraction.

| Field | Rule | Why |
|---|---|---|
| `files`, `keywords`, `commit` | union across all of a doc's records | genuine per-run deltas |
| `req`, `specs` | last non-null | full restatement each run, retractable to `[]` |
| `domain`, `update` | last | status-like scalars |

```bash
# current state per doc
jq -s -c 'group_by(.doc)[]
  | {doc:.[0].doc, domain:(map(.domain)|last), updated:(map(.date)|max),
     req:([map(.req)[]|select(.!=null)]|last // []),
     specs:([map(.specs)[]|select(.!=null)]|last // []),
     keywords:(map(.keywords[]?)|unique), files:(map(.files[]?)|unique),
     commits:(map(.commit|values)|unique)}' .claude/clio/index.jsonl

# by requirement (from hop 1) — a hit is a candidate; confirm against the rollup above,
# superseded tags still match a raw scan
jq -c 'select(.req[]? == 5)' .claude/clio/index.jsonl
jq -c 'select(.specs[]? | contains("order-flow"))' .claude/clio/index.jsonl

# by file / area / keyword
jq -c 'select(.files[]? | contains("ProductRepo"))' .claude/clio/index.jsonl
jq -c 'select(.domain=="account" or (.keywords[]? == "i18n"))' .claude/clio/index.jsonl
```
`req`/`specs` are the join to the requirement but not infallible — `req` the weaker of the two:
inherited bugs, RBAC, infra structurally map to no requirement row, so `req:[]` can be legitimate.
Prefer `specs`, fall back to `domain`/`keywords`/`files`.

**Then read the matching docs' load-bearing sections, not the summary.** `## Summary` hides what
matters. Go to `## Decisions` (constraints), `## Side Effects` (what you can break), `## Follow-up`
(knowingly left unfinished) — a doc's most expensive-to-rediscover content is at the bottom.


**If a query hits a record that looks off** — missing `doc`, unfamiliar `domain`, or pointing at a
file not on disk: a `doc` path missing on disk means the doc was renamed; look for a later record
carrying `"supersedes":"<the old path>"`, which names the current file. Records written before this
system was introduced may lack `specs`/`req` — fall back to `domain`/`keywords`/`files` and mention
the gap if a doc should plausibly have matched.

Next: [HOP3.md](HOP3.md).
