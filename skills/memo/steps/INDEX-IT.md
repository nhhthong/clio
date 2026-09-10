# Step 4 — Index it: `.claude/clio/index.jsonl`

Append-only, one line per document **every run** — UPDATE runs too; a doc's lines are its timeline.
Never rewrite, reorder or delete an existing line, including this doc's own earlier runs.

**Every field restates the doc's full current state.** Readers take the last line per `doc` and
nothing else, so a field you leave out or leave short is a field you erased. Start from the
previous record and edit it:
```bash
jq -s -c --arg d "<doc path>" 'map(select(.doc==$d)) | last' .claude/clio/index.jsonl
```

Append (paths and domain below are placeholders — use this repo's real ones):
```bash
echo '{"date":"YYYY-MM-DD","type":"task","update":true,"doc":".claude/docs/tasks/2026-07-15_account-two-factor.md","domain":"account","files":["src/orders/order-service.ts","src/orders/order-repo.ts"],"commits":["3f2a1c","9b0e77"],"keywords":["orders","pagination"],"specs":[".claude/docs/specs/memory/ui-design.md"],"req":[2]}' >> .claude/clio/index.jsonl
```

| Field | Rule |
|---|---|
| `date` | today |
| `type` | `task` or `adr` |
| `update` | `true` after the first run; omit on CREATE |
| `doc` | the doc's path, unchanged across runs |
| `domain` | one term from `.claude/CLAUDE.md` § Project memory — by business area served, not directory. New term needed → add it there, say so in the report |
| `files` | every source file the doc still covers: previous list + this run's, minus what was reverted. Repo-relative, build output excluded |
| `commits` | previous list + this run's hash; `[]` if never committed |
| `keywords` | previous list + new ones |
| `req`, `specs` | the doc's full current claim; `specs` only what `requirements.md` maps `req` to, never a plausible-looking spec |

Renamed or deleted doc → never rewrite old lines; append a new-path record with
`"supersedes":"<old path>"`.

Validate — never declare done on a line it rejects:
```bash
"${CLAUDE_PLUGIN_ROOT}"/skills/memo/scripts/validate.sh index
```
`FAIL` → `sed -i.bak '$d' .claude/clio/index.jsonl && rm .claude/clio/index.jsonl.bak`, fix, re-append.

Next: `DEBT-IT.md`.
