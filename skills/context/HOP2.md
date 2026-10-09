# Hop 2: what was already built

Ledger: `.claude/clio/database/index.jsonl`. Append-only, written by `/clio:memo`. Every record is a document record (`type` `task` or `adr`) carrying `id`, `doc`, `domain`, `keywords`, `files`, `commits`, `specs`, `req`, `plan_tasks`. Open items are not here; see [HOP3.md](HOP3.md).

One record per run, and the last record per `id` is the doc's full current state. `id` is the doc's creation timestamp and its filename prefix. It never changes, so a moved or renamed doc keeps its `id` with a new `doc` path. Every field is restated in full each run: `files` is every source file the doc covers, and `req` and `specs` are its full current claim (retractable to `[]`). Earlier records are the timeline. Read them for "what changed when", and never merge them.

## Queries
All reads go through `clio q`, one line per doc:
- `clio q built` gives the current state of every doc.
- Filters: `--req 5` (a requirement row from hop 1), `--spec order-flow`, `--file ProductRepo`, `--task 3.3`, and `--area account --keyword i18n`. Filters are OR'd, and a doc prints once.
- `clio q history <id>` gives a doc's timeline and what its last run added or removed.

A `WARN: ... malformed line(s)` on stderr means the ledger is broken, not empty. Say so, point at `clio validate all` (it names the line), and never report "nothing on record" from a partial read.

`req` and `specs` join a doc to the requirement, but not reliably, and `req` is the weaker. Inherited bugs, RBAC and infra structurally map to no requirement row, so `req: []` can be legitimate. Prefer `specs`, and fall back to `domain`, `keywords` and `files`.

## Read the load-bearing sections, not the whole doc
`## Summary` hides what matters, and a long-lived doc costs a lot to open whole. Read only `## Decisions` (the constraints), `## Side Effects` (what you can break) and `## Follow-up` (what was knowingly left unfinished). A doc's most expensive content to rediscover is at the bottom. Open the file whole only when those sections point you at something they do not contain.

Listing the directories is free context: `.claude/clio/docs/tasks/` names the features, and `.claude/clio/docs/tasks/<feature>/` names its sub-tasks. Do that before opening anything.

## The feature's memory
Every feature directory the matching docs live in (or the one this task will write into) has a `summary.md`. Read its shared sections, `## General Memory` and `## Cross-cutting side effects`, which hold what every sub-task there must know. Its bullets bind this task like a path-scoped rule, so quote the ones that apply.

If a `doc` path is missing on disk, run `clio q history <id>` before concluding anything. A moved doc's current path is in its last record.

Next: [HOP3.md](HOP3.md).
