# A change — rows exist, and something moved

For a new source, a spec file or keyword, a change in plain words, or a sweep of hand edits. Specs move while code stands still: work out what the change invalidates **before** writing it. Then `SKILL.md` §§ 1–4.

## 1. The change, decision by decision
Start with one `clio q spec-grep '<key word>'` per word the change turns on (not `cat`/`grep` over `memory/`): it lists the decisions in force that mention it, across areas.
List every decision added, altered, reversed or resolved: the old rule and the new. The old rule comes from the current `memory/*.md`, or for a sweep from the hand edits since the last ingest (uncommitted and new files included):
```bash
clio q spec-diff --stat   # which spec files moved
clio q spec-diff          # the lines
```
The baseline is clone-local (`refs/clio/*` is never pushed), so a fresh checkout has none: try `git diff -M <commit> -- .claude/` from a `Last ingest:` line in an older `requirements.md`, else the dated notes and what the task docs assumed. Still no before-state → the delta is new-rule-only; say so.

## 2. Weigh it — before anything is written
```bash
clio q context <row> [<row>...]     # rows, what was built on them (docs' Decisions / Side Effects / Follow-up), open debt, plan tasks (done = built on it, open = drafts)
clio q cases <task>...              # cases whose expected rests on the old rule
clio q spec-grep '<the old value>'  # other decisions in force that mention it (superseded bullets are history)
```
One `context` call covers every decision (rows are merged). A value one decision changes is often read by others (a width, a limit, a key, a name): `spec-grep` finds the live ones across areas, and `clio:plan` greps the code per row. Then show the user, **before writing any file**:
```text
This change reverses 4 decisions in 3 areas:
  ui      row 12 · `q` quits → no quit key       built: tasks 12.1, 12.3 (done) · 3 cases expect the old rule
  ui      row 14 · default theme → none           planned: 14.2 (open) — edited in place, nothing built
  search  row 20 · search bar bottom → top        built: 20.1 (done) · 2 task docs describe it
  brand   row 30 · logo → mascot                  nothing built yet
Spec-delta records: 3 · task docs to relabel: 4 · cases to re-design: 5 · areas to re-plan: ui, search
Write it all, or one area / one decision at a time?
```
**ASK** with that summary. The user may take all, some, or none; a part left for later stays out of every file.

## 3. Write what was agreed
The spec files and `requirements.md` per `SKILL.md` §§ 1–2. Then, per decision:

| The change | Write |
|---|---|
| a done task was built on the old decision | a `spec-delta` (reuse the `id` for the same delta): `docs[]` = the task docs from § 2, `code[]` = the paths they name — how `/clio:memo` later relabels them. `blocked_by: null` once the new decision is settled: that is the work queue |
| only open tasks were planned on it | no delta: `/clio:plan` edits those drafts in place |
| nothing built or planned | no delta |
| it answers an open `spec-blocked` | `{"id":"<that id>","blocked_by":null}` — never change its `kind` |
```bash
clio add debt <<'EOF'
{"id":"<kebab-key>","kind":"spec-delta","domain":"checkout","what":["<old> → <new>"],"req":["18"],"specs":[".claude/clio/docs/specs/memory/<file>.md"],"docs":["<task docs built on the old decision>"],"code":["<paths they name>"],"action":"<the rework>","source":"<source §n, date>"}
EOF
```
**Row marker** when the *decision* changed (never build state): ⚠️/❌ → ✅ when the open point got decided (reason = decision + date); ⚠️/❌ stays, reason rewritten, when another part is still open; ✅ → ⚠️ when reopened or reversed; ✅ stays, decision + date appended, when refined. **Moving toward ✅ removes a stop, so it asks first**: every such row in one `AskUserQuestion` as `row · old reason → new decision · deciding source`; write only the approved. Never flip on a low-priority source; the marker and `blocked_by` must tell the same story. Row `0` (the stack) → [STACK.md](STACK.md).

## A change withdrawn
The user drops a change ingested earlier ("không muốn sửa nữa"): written the other way round, after the same weighing.
- The change's decisions get `Superseded YYYY-MM-DD: withdrawn`; the ones it had superseded get `Reinstated YYYY-MM-DD: <the change> was withdrawn`; one new decision says what holds again, as a pointer, not a copy.
- A ⚠️ the change opened and the withdrawal makes moot leaves `## Open` (the new decision says so). Row markers go back to what the reinstated decisions say (toward ✅ asks first).
- Debt: the change's records close (`status` `done`, `action` says withdrawn). Work already built on it gets a new `spec-delta`, which `/clio:plan` turns into voided drafts, withdrawn tasks (never left the working tree) or revert tasks (committed).

## Report
Besides `SKILL.md` § 4: each delta as `id` · `blocked_by` · row · action, queue first; rows moved (old → new, deciding source); records unblocked; any `index.jsonl` record the change shows to be wrong (reported, never fixed: `/clio:memo`'s); what the user left for later. Then the areas to re-plan, `infra` (row `0`) first:
```text
infra     row 0 · Go 1.22 → 1.23 · rules/go.md names `go test ./...`        →  /clio:plan infra
ui        row 12 · 12.1, 12.3 done on the old rule · spec-delta ui-no-quit   →  /clio:plan ui
brand     row 30 · nothing built                                              →  /clio:plan brand
```
`/clio:plan` turns each delta into a sub-task and edits open drafts in place; `/clio:test` re-designs the stale cases. This skill writes neither.
