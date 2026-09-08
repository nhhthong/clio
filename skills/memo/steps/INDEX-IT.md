# Step 4 — Index it: `.claude/clio/index.jsonl`

Append-only, one line per document **every run** — UPDATE runs too; a doc's lines are its timeline.
Never rewrite, reorder or delete an existing line, including this doc's own earlier runs.

Reuse the doc's existing keywords first:
```bash
jq -r --arg d "<doc path>" 'select(.doc==$d) | .keywords[]?' .claude/clio/index.jsonl | sort -u
```

Append (paths and domain below are placeholders — use this repo's real ones):
```bash
echo '{"date":"YYYY-MM-DD","type":"task","update":true,"doc":".claude/docs/tasks/2026-07-15_account-two-factor.md","domain":"account","files":["src/orders/order-service.ts"],"commit":"<hash or null>","keywords":["<kw1>","<kw2>"],"specs":[".claude/docs/specs/memory/ui-design.md"],"req":[2]}' >> .claude/clio/index.jsonl
```

| Field | Rule |
|---|---|
| `date` | today |
| `type` | `task` or `adr` |
| `update` | `true` after the first run; omit on CREATE |
| `doc` | the doc's path, unchanged across runs |
| `domain` | one term from `.claude/CLAUDE.md` § Project memory — by business area served, not directory. New term needed → add it there, say so in the report |
| `files`, `keywords`, `commit` | **this run's delta only**, repo-relative, build output excluded. Readers union across records, so never leave one empty because a prior line has it |
| `req`, `specs` | **not deltas** — restate the doc's full current claim every run; readers take the last value. `specs` only what `requirements.md` maps `req` to, never a plausible-looking spec |

Renamed or deleted doc → never rewrite old lines; append a new-path record with
`"supersedes":"<old path>"`.

Validate — never declare done on a line it rejects:
```bash
"${CLAUDE_PLUGIN_ROOT}"/skills/memo/scripts/validate.sh index
```
`FAIL` → `sed -i '$d' .claude/clio/index.jsonl`, fix, re-append.

Next: `DEBT-IT.md`.
