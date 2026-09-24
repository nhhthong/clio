# Hop 2 — what was already built (`.claude/clio/database/index.jsonl`)

Append-only, written by `/clio:memo`. Every record is a document record (`type` `task`/`adr`)
carrying `id`, `doc`, `domain`, `keywords`, `files`, `commits`, `specs`, `req`, `plan_tasks`. Open
items aren't here — see [HOP3.md](HOP3.md).

**One record per run; the last record per `id` is the doc's full current state.** `id` is the doc's
creation timestamp and its filename prefix — it never changes, so a moved or renamed doc is still
the same `id` with a new `doc` path. Every field is restated in full each run: `files` is every
source file the doc covers, `req`/`specs` its full current claim (retractable to `[]`). Earlier
records are the timeline — read them for "what changed when", never merge them.

All reads go through `q.sh` — one line per doc, its current state:

```bash
q.sh built                          # current state, one line per doc
q.sh built --req 5                  # by requirement row (from hop 1)
q.sh built --spec order-flow        # by spec file
q.sh built --file ProductRepo       # by source file
q.sh built --area account --keyword i18n   # filters are OR'd; a doc prints once
q.sh built --task 3.3               # by plan task
q.sh history <id>                   # a doc's timeline, and what its last run added/removed
```
A `WARN: … malformed line(s)` on stderr means the ledger is broken, not empty: say so, point at
`validate.sh all` (it names the line), and never report "nothing on record" off a partial read.

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

`ls` is free context: `ls .claude/clio/docs/tasks/` names the features, `ls .claude/clio/docs/tasks/<feature>/`
names its sub-tasks. Use it before opening anything.

**The feature's memory.** Every feature directory the matching docs live in (or the one this task
will write into) has a `summary.md`; read its shared sections — what every sub-task there must know:
```bash
awk '/^## /{p = /^## (General Memory|Cross-cutting side effects)/} p' .claude/clio/docs/tasks/<feature>/summary.md
```
Its bullets bind this task like a path-scoped rule does; quote the ones that apply.

A `doc` path missing on disk → `q.sh history <id>` before concluding anything; a moved doc's current
path is in its last record.

Next: [HOP3.md](HOP3.md).
