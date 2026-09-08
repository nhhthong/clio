# Step 1 — Resolve the target doc

Do this FIRST, before writing anything.

**Case A — path passed:** `test -f "<path>" && echo EXISTS || echo MISSING`
- `EXISTS` → UPDATE mode, go to `GATHER-FACTS.md` (same dir).
- `MISSING` → stop, ask. Don't create at that path — likely a typo, and creating it forks the
  feature's history.

**Case B — nothing passed:** find the existing doc before assuming there isn't one.
```bash
git diff --name-only | while read -r f; do
  jq -c --arg f "$f" 'select(.files[]? | contains($f))' .claude/clio/index.jsonl
done | sort -u
ls -1t .claude/docs/tasks/ | head -20
grep -i "<feature keyword>" .claude/clio/index.jsonl
```
- One plausible match, same feature → UPDATE.
- Several/ambiguous → show candidates, ask.
- None → CREATE. Go to `GATHER-FACTS.md`, then `CREATE-MODE.md` (both same dir).

**Same feature vs new:** same files ≠ same feature. Continuing/fixing/extending/reverting existing
work → UPDATE. Genuinely different work in same domain → new doc.
