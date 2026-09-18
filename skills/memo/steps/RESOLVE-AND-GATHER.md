# Step 1 — Resolve the doc and gather the facts

Which doc, then what goes in it. Both run every time and the second needs the first's answer,
so they are one step.

## Which doc

Do this FIRST, before writing anything.

**Case A — a path was passed:** `test -f "<path>" && echo EXISTS || echo MISSING`
- `EXISTS` → UPDATE mode, go to `RESOLVE-AND-GATHER.md`.
- `MISSING` → stop, ask. Don't create at that path — likely a typo, and creating it forks the
  sub-task's history.

**Case A2 — a plan task id was passed** (`$ARGUMENTS` matches `^[0-9]+(\.[0-9]+)*$`, e.g. `3.3`).
The id lives in the ledger, not in the filename, so look it up there:
```bash
jq -s -r --arg t "$ARGUMENTS" '(map(select(.id)|{key:.doc,value:.id})
   + map(select(.supersedes)|{key:.supersedes,value:.id}) | from_entries) as $m
  | group_by(.id // $m[.doc] // .doc)[] | last | select(.plan_tasks[]? == $t) | .doc' \
  .claude/clio/index.jsonl
grep -n "^| $ARGUMENTS " .claude/docs/plans/*.md      # the task, its Test and its Done column
```
- A doc came back → UPDATE mode.
- Nothing came back, but the plan row exists → CREATE, and record it in `plan_tasks` at step 4.
- Neither → stop, ask. Don't invent a plan id.

**Case B — nothing passed:** find the existing doc before assuming there isn't one.
Query current state, not every line: an unbridged scan returns a migrated doc's old path too, and
offering a file that no longer exists as a candidate is how memo ends up asking you to choose
between a doc and its own ghost.
```bash
G='(map(select(.id)|{key:.doc,value:.id}) + map(select(.supersedes)|{key:.supersedes,value:.id})
    | from_entries) as $m | group_by(.id // $m[.doc] // .doc)'
git diff --name-only HEAD | while read -r f; do    # HEAD: staged edits count too
  jq -s -r --arg f "$f" "$G"'[] | last | select(.files[]? | contains($f)) | .doc' .claude/clio/index.jsonl
done | sort -u
ls -1t .claude/docs/tasks/                         # feature directories, most recent first
jq -s -r "$G"'[] | last | select(.keywords[]? | contains("<feature keyword>")) | .doc' .claude/clio/index.jsonl
```
- One plausible match, same sub-task → UPDATE.
- Several/ambiguous → show candidates, ask.
- None → CREATE. Go to `RESOLVE-AND-GATHER.md`, then `WRITE-DOC.md` § CREATE.

**Same sub-task vs new:** same files ≠ same sub-task. Continuing/fixing/extending/reverting the work
a doc already describes → UPDATE that doc. A different observable behaviour, even in the same feature
directory → a new doc beside it.

## The facts

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
`<row>.<n>`, but a plan lifted out of an old `requirements.md` keeps that project's own
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
