# Step 3 — Write the doc

## CREATE — only when step 1 found nothing

Filename: `.claude/docs/tasks/YYYY-MM-DD_<keywords>.md`, keywords = 2–4 lowercase hyphenated words,
domain first (`account-two-factor`).

```markdown
# <Feature Name>
Date: YYYY-MM-DD
Updated: YYYY-MM-DD
Commit: <hash or "not committed">

## Summary
One sentence.

## Files Changed
- `path/to/file` — reason

## Decisions
- Why non-obvious choice X was made instead of Y

## Side Effects
- Anything that could affect other features

## Testing Done
- YYYY-MM-DD — how it was verified

## Related
- Prior task docs / ADRs this builds on or supersedes. "none" if genuinely none.

## Follow-up
- Open questions or next steps

## Change Log
- YYYY-MM-DD — initial
```

## UPDATE — the default

Never rename the file (its date is the creation date). Never delete or rewrite an existing bullet
except under `## Follow-up`. A missing section → add it in the order above. A section the code no
longer matches → relabel it in place, `## [SUPERSEDED YYYY-MM-DD] <heading>`, add `— REVERTED, DO
NOT RE-IMPLEMENT` when the code is gone, keep the body.

Header: keep `Date:`, refresh `Updated:` to today, append (don't replace) `Commit:`.

| Section | Do |
|---|---|
| `## Summary` | Leave alone; rewrite only if scope genuinely changed. |
| `## Files Changed` | Merge — new paths only; new reason for an existing file → append `; <reason> (date)`. |
| `## Decisions` | Append. Reversed → append `Superseded YYYY-MM-DD: now Y instead of X, because …`. |
| `## Side Effects` / `## Testing Done` / `## Related` | Append, dated. |
| `## Follow-up` | The only destructive section — delete completed, add new open. Empty → `none`. |
| `## Change Log` | Append `- YYYY-MM-DD — <summary> (commit <hash>)`. |

A doc whose Summary now needs "and" three times to say what it covers → ask the user once whether
to split it into a new doc; split only on a yes, and don't ask again this session.

Next: `INDEX-IT.md`.
