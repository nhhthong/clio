# Step 2 — Gather facts

- Today: `date +%Y-%m-%d`. Commit: `git log -1 --format=%h` if committed, else `null`.
- UPDATE → read the **entire** target doc first. Ask only what you cannot derive: feature name
  (CREATE only), intent behind a non-obvious change.

## Files changed

1. List the files you edited this run, then verify each on disk: `git status --porcelain <file>`
   or `git show --name-only --format= <hash>`. Reverted mid-session → drop it.
2. Anything in `git status --porcelain` that is not on your list → show the user, ask.
3. No session memory (compacted or fresh session) → `git status --porcelain` (uncommitted, incl. untracked) or
   `git show --name-only --format= <hash>` (committed), and say in the report that the list came
   from git rather than the run itself.
4. Files a subagent edited never appear in your tool calls — take them from its report, verify the
   same way.

**Drop build output.** The generated-vs-source map is `.claude/CONTEXT.md` § Source of truth; record
the source, never the generated copy. If a generated path is the *only* thing that changed, you
edited the copy — stop and tell the user. A scaffold run (`flutter create`, `npx create-*`,
`composer create-project`…) is recorded as the command in `## Decisions` and one `files` entry
`scaffold:<command>`; list only what was hand-edited afterwards.

## Which requirement this work serves

```bash
grep -in "<feature keyword>" .claude/docs/specs/requirements.md
```
- `req` = matching row number(s), can be several. `specs` = the `memory/*.md` file(s) the row maps to.
- No match → `"req":[]`, never invent one; keep `specs` only if a spec file still governs the area,
  and say so in the report. Don't tag on keyword resemblance — a wrong `req` misdirects future
  sessions worse than `[]`.
- Row marked ⚠️/❌ → note it, DEBT-IT.md may need a record. ✅ means decided, not built — still write
  the record.
- `.claude/docs/plans/<area>.md` has a task for this work → note its id; its `Test` column is what
  `## Testing Done` must record. DEBT-IT.md § 2 ticks it or files it `unverified`.

Next: `WRITE-DOC.md`.
