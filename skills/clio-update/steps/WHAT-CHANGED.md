# Step 1 — What changed, who's affected

## What changed

- Argument given → that spec file (or the `requirements.md` row matching the keyword).
- Nothing given → sweep `.claude/docs/specs/memory/*.md` + `requirements.md`.

Establish the *delta*, not just the current text — "what is different now". Work through the source
priority list `requirements.md` declares, highest first — the live decision channel outranks every
distilled spec file, and its open items can re-open a point another file calls settled.

Old wording gone (specs get pruned) → reconstruct from the spec's own dated notes ("supersedes …",
"reversed YYYY-MM-DD", `requirements.md` status text) and what the task docs assumed at the time. Can't
state the before-state → say so, write the delta as new-rule-only, flag it in the final report.

## Who is affected — join through the index

```bash
jq -c 'select((.req[]? == <N>) or (.specs[]? | contains("<spec>")))' .claude/clio/index.jsonl
jq -s -c 'group_by(.id)[] | last
  | select(.status!="done" and ((.req[]? == <N>) or (.specs[]? | contains("<spec>"))))' \
  .claude/clio/debt.jsonl
```
`index.jsonl` array fields are per-run deltas — union across records, never take `last` (see
`clio-context` skill). Open the matching docs, read `## Decisions` / `## Side Effects` /
`## Follow-up` — that's what a spec change invalidates. Note the concrete code paths named there →
`code[]`.

Next: `DECIDE-STATUS.md`.
