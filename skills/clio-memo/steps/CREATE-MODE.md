# Step 3b — CREATE mode

Only when `RESOLVE-DOC.md` found no existing doc.

Filename (both `.claude/docs/tasks/` and `.claude/docs/decisions/`): `YYYY-MM-DD_<keywords>.md`,
keywords = 2–4 lowercase hyphenated words, domain first (`account`, `checkout`, `billing`, `all`).
E.g. `account-two-factor`.

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
