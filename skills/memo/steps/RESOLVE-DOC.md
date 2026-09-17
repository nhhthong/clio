# Step 1 — Resolve the target doc

Do this FIRST, before writing anything.

**Case A — a path was passed:** `test -f "<path>" && echo EXISTS || echo MISSING`
- `EXISTS` → UPDATE mode, go to `GATHER-FACTS.md`.
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
- None → CREATE. Go to `GATHER-FACTS.md`, then `WRITE-DOC.md` § CREATE.

**Same sub-task vs new:** same files ≠ same sub-task. Continuing/fixing/extending/reverting the work
a doc already describes → UPDATE that doc. A different observable behaviour, even in the same feature
directory → a new doc beside it.
