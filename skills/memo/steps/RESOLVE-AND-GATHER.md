# Step 1 — Resolve the doc and gather the facts

Which doc, then what goes in it. Both run every time and the second needs the first's answer, so
they are one step. Scripts are named by basename; call them by the full path `SKILL.md` § Scripts
gives, in the same Bash command.

## What changed

Start from git, whatever the target:
```bash
q.sh changed        # uncommitted + untracked files of this work, .claude/ excluded; renames by new path
q.sh unrecorded     # commits since the last one any index record names: <hash><TAB><docs covering it | ->
```

| `changed` | `unrecorded` | Situation | Go to |
|---|---|---|---|
| files | anything | work in progress or just finished, not (fully) committed | the target's case below |
| empty | lines | work committed, never recorded — or recorded before it was committed | Case D if every line names docs; else the target's case, files from `git show --name-only --format= <hash>` |
| empty | empty | nothing new since the last memo | stop: say "nothing to record", unless the user names work outside git |
| "not a git repository" | – | no git | the target's case; files come from the session only, commit stays empty |

## Which doc

Do this FIRST, before writing anything.

**Case A — path target:** `test -f "<path>" && echo EXISTS || echo MISSING`
- `EXISTS` → UPDATE mode.
- `MISSING` → stop, ask. Don't create at that path — likely a typo, and creating it forks the
  sub-task's history.

**Case B — task target** (a plan task id such as `3.3`). The id lives in the ledger, not in the
filename:
```bash
q.sh built --task <task>
grep -n "^| <task> " .claude/clio/docs/plans/*.md      # the row: its Levels and Done cells
```
- A doc came back → UPDATE mode.
- No doc, and the task is a re-plan sub-task (`3.1.1` under `3.1`) → `q.sh built --task <parent id>`.
  A doc came back → UPDATE it: a sub-task changes or hardens what its parent's doc describes.
- No doc, but the plan row exists → CREATE, with the id in `plan_tasks` at step 3.
- Neither → stop, ask. Don't invent a plan id.

**Case C — no target:** find the existing doc before assuming there isn't one. `q.sh` returns
current state only, so a moved doc's old path never shows up as a candidate.
```bash
q.sh built --file <each path from q.sh changed>
q.sh built --keyword "<feature keyword>"
ls -1t .claude/clio/docs/tasks/                       # feature directories, most recent first
```
- One plausible match, same sub-task → UPDATE.
- Several or ambiguous → show candidates, ask.
- None → CREATE (`WRITE-DOC.md` § CREATE).

**Case D — backfill.** Nothing uncommitted, and every `unrecorded` line names the docs that cover its
files: the work was recorded while uncommitted and has since been committed. For each such doc,
UPDATE with the hash only — `Commit:` line, `## Change Log`, `commits` in its index record, and the
hash appended to its ticked plan rows. Nothing else is re-derived or rewritten; say "backfill" in the
report. A line ending `-` is work nobody recorded → Case C for those files.

**Same sub-task vs new:** same files ≠ same sub-task. Continuing, fixing, extending or reverting the
work a doc already describes → UPDATE that doc. A different observable behaviour, even in the same
feature directory → a new doc beside it.

## The facts

- Today: `date +%Y-%m-%d`.
- UPDATE → read the **entire** target doc first. Ask only what you cannot derive: the sub-task name
  (CREATE only), the intent behind a non-obvious change.

## Files changed

1. Start from your own edits this run; check each against `q.sh changed` (or the commit's file list).
   Reverted mid-session → drop it.
2. In `q.sh changed` but not in your edits → show the user, ask. It may be their work, not this task's.
3. No session memory (compacted or fresh session) → the `q.sh changed` list, or the unrecorded
   commit's files; say in the report the list came from git, not the run.
4. Files a subagent edited never appear in your tool calls — take them from its report, check them
   the same way.

**Drop build output.** The generated-vs-source map is the `.claude/rules/*.md` bullets `/clio:plan
infra` wrote; record the source, never the generated copy. A generated path the *only* thing that
changed → you edited the copy; stop and tell the user. A scaffold run (`flutter create`, `npx
create-*`, `composer create-project`…) is recorded as the command in `## Decisions` and one `files`
entry `scaffold:<command>`; list only what was hand-edited afterwards.

## The commit

```bash
q.sh commit <every file from the list above>
```
A hash → this run's commit. Empty → none (`SKILL.md` § Commits).

## Which requirement this work serves

```bash
grep -in "<feature keyword>" .claude/clio/docs/specs/requirements.md
```
- `req` = the matching row numbers, as strings (`["7.10"]`), can be several. `specs` = the
  `memory/*.md` files the row maps to.
- No match → `"req":[]`, never invent one; keep `specs` only if a spec file still governs the area,
  and say so in the report. Don't tag on keyword resemblance — a wrong `req` misdirects future
  sessions worse than `[]`.
- Row marked ⚠️/❌ → note it; `DEBT-IT.md` may need a record. ✅ means decided, not built — still
  write the record.

## Which plan task this work is

Match on the plan table's **`req` column**, not on the task id. `/clio:plan` numbers its ids
`<row>.<n>`, but a plan lifted out of an old `requirements.md` keeps that project's own numbering,
so `1.14` can serve req `10`:
```bash
awk -F'|' -v r="<req>" 'NF>5 && $4 ~ ("(^| )" r "( |,|$)") {gsub(/^ +| +$/,"",$2); print FILENAME": "$2}' \
  .claude/clio/docs/plans/*.md
```
Plan still in its pre-split bullet form → no `req` column to match; say so and read the file.
- Each row this work actually implements goes in `plan_tasks` for step 3; step 4 gates and ticks it.
- Unsure whether a row belongs → leave it out. `[]` is a correct answer; a wrong id makes step 4
  gate and tick a task nobody meant.
- Nothing at all → no plan file for this row; say so in the report and continue.

Next: `WRITE-DOC.md`.
