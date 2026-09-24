# Step 2 — Write the doc

## Where docs live

One directory per feature, one file per sub-task:
```
.claude/clio/docs/tasks/order-page/
├── summary.md                     # the feature, ~20 lines, does not grow per run
├── 1789430400_order-fetch.md
└── 1789516800_loyalty-lookup.md
```
Feature directory: kebab-case, the business area a task would be scoped to — never a directory name
from the source tree, never prefixed `task_`. `ls` on either level is a free table of contents, so
keep both levels small and the filenames descriptive.

## CREATE — only when step 1 found nothing

```bash
ts=$(date +%s)          # this is the doc's id, forever: filename prefix and index.jsonl .id
```
Filename: `.claude/clio/docs/tasks/<feature>/${ts}_<name>.md`, `<name>` = 2–4 lowercase hyphenated words
naming the sub-task (`loyalty-lookup`, `order-bulk-create`). Working from a plan task → use that
task's wording; the plan ids themselves go in the ledger's `plan_tasks`, not in the filename.

```markdown
# <Sub-task Name>
Date: YYYY-MM-DD
Updated: YYYY-MM-DD
Commit: <hash, or empty>
Plan tasks: <3.1, or "none">

## Summary
One sentence.

## Files Changed
- `path/to/file` — reason

## Decisions
- Why non-obvious choice X was made instead of Y

## Side Effects
- Anything that could affect other features

## Testing Done
- YYYY-MM-DD — the `clio-test.sh gate` OK line, or "unverified" and why

## Related
- Prior task docs / ADRs this builds on. "none" if genuinely none.

## Follow-up
- Open questions or next steps

## Change Log
- YYYY-MM-DD — initial
```

New feature directory → also write `summary.md`, and only what `ls` cannot say:
```markdown
# <Feature>
Domain: <domain> · Plan: `.claude/clio/docs/plans/<area>.md` · Spec: `memory/<area>.md`

## What this is
One or two sentences.

## Cross-cutting side effects
- What breaks elsewhere when any sub-task here changes. Empty is fine.

## General Memory
- What every sub-task of this feature must know and would otherwise re-learn: a helper to reuse,
  a trap in this area, a local command. Written by `WRAP-UP.md`; `clio:context` loads it with the
  feature. Empty is fine.
```
An existing `summary.md` without `## General Memory` → add the heading when it first gets a bullet.
**Never list the sub-tasks in it.** `ls` and `plans/<area>.md` already answer that; a hand-kept list
is one more thing to drift.

## UPDATE — the default

Never rename the file — its prefix is its `id` and the ledger keys on it. Never delete or rewrite an
existing bullet except under `## Follow-up`. A missing section → add it in the order above. A section
the code no longer matches → relabel it in place, `## [SUPERSEDED YYYY-MM-DD] <heading>`, add
`— REVERTED, DO NOT RE-IMPLEMENT` when the code is gone, keep the body.

Header: keep `Date:`, refresh `Updated:` to today, append this run's hash to `Commit:` if there is one.

| Section | Do |
|---|---|
| `## Summary` | Leave alone; rewrite only if scope genuinely changed. |
| `## Files Changed` | Merge — new paths only; new reason for an existing file → append `; <reason> (date)`. |
| `## Decisions` | Append. Reversed → append `Superseded YYYY-MM-DD: now Y instead of X, because …`. |
| `## Side Effects` / `## Testing Done` / `## Related` | Append, dated. |
| `## Follow-up` | The only destructive section — delete completed, add new open. Empty → `none`. |
| `## Change Log` | Append `- YYYY-MM-DD — <summary>` (+ ` (commit <hash>)` if any). Backfill: `- YYYY-MM-DD — committed as <hash>`. |

**Split gate.** This doc is over ~200 non-blank lines, **or** its `req` now holds more than one row
→ ask the user once whether the next piece of work should start its own sub-task doc in the same
feature directory. Split only on a yes, don't ask again this session, and never move content out of
an existing doc — the old doc keeps its history, the new one starts at today.

Moving a doc (into a feature directory, or to a different one) keeps its filename and its `id`;
`INDEX-IT.md` records the new `doc` path under the same `id`.

Next: `INDEX-IT.md`.
