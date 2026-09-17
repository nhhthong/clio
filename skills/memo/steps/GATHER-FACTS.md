# Step 2 — Gather facts

- Today: `date +%Y-%m-%d`. Commit: `git log -1 --format=%h` if committed, else `null`.
- UPDATE → read the **entire** target doc first. Ask only what you cannot derive: sub-task name
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

## Which plan task this work is

Match on the plan table's **`req` column**, not on the task id. `/clio:plan` numbers its ids
`<row>.<n>`, but a plan `/clio:audit` lifted out of an old `requirements.md` keeps that project's own
numbering — phases, epics, whatever it used — so `1.14` can serve req `10`. The `req` column holds
the join either way, and it means you never have to guess the area:
```bash
awk -F'|' -v r="<req>" 'NF>5 && $4 ~ ("(^| )" r "( |,|$)") {gsub(/^ +| +$/,"",$2); print FILENAME": "$2}' \
  .claude/docs/plans/*.md
```
Plan still in its pre-split bullet form (`/clio:plan` has not re-laid it) → no `req` column to match;
say so and read the file.
- Each row this work actually implements goes in `plan_tasks` for step 4, and its **`Test` column
  is what `## Testing Done` must record**. `DEBT-IT.md` § 2 ticks each one or files it `unverified`.
- Unsure whether a row belongs → leave it out. `[]` is a correct answer; a wrong id makes step 5
  tick a task nobody tested.
- `grep` returns nothing at all → no plan file for this row; say so in the report and continue.

Next: `WRITE-DOC.md`.
