# A change — rows exist, and something moved

Read by `/clio:ingest` for a new source, a spec file or keyword, a change in plain words, or a sweep
of hand edits. Specs move while code stands still: this file works out what the change invalidates
**before** writing it, then writes it. Then back to `SKILL.md` §§ 1–4.

## 1. The change, decision by decision

List every decision the source adds, alters, reverses or resolves — one line each, the old rule and
the new. Where the old rule comes from:
- a new source or a plain-words change → the current `memory/*.md`;
- a sweep → the hand edits since the last ingest, uncommitted and new files included:
  ```bash
  clio q spec-diff --stat  # which spec files moved since the last ingest
  clio q spec-diff         # the lines
  ```
  The baseline is clone-local (`refs/clio/*` is never pushed), so a fresh checkout has none. Then: a
  `requirements.md` written by an older Clio may carry a `Last ingest:` line naming a commit —
  `git diff -M <commit> -- .claude/`, spec files only; otherwise the dated notes ("Superseded
  YYYY-MM-DD", the row's status text) and what the task docs assumed. Still no before-state → the
  delta is new-rule-only; say so in the report.

## 2. Weigh it — before anything is written

For every decision on the list, what was built and planned against the old rule:
```bash
clio q built --req <row> --spec <file>    # task docs: read their ## Decisions, ## Side Effects, ## Follow-up
clio q owed --req <row> --spec <file>     # open debt on it
clio q plan --all                         # tasks whose req is the row: done ones were built on it, open ones planned on it
clio q cases <task>...                    # cases of those tasks whose expected rests on the old rule
clio q spec-grep '<the old value>'        # other decisions still in force that mention it; superseded bullets are history
```
A value one decision changes is often read by others: a width, a limit, a key, a name. `spec-grep` finds the
live ones across every area; so does grepping the code for the identifier (`clio:plan` does that per row).
Then show the user, **before writing any file**:
```text
This change reverses 4 decisions in 3 areas:
  ui      row 12 · `q` quits → no quit key       built: tasks 12.1, 12.3 (done) · 3 cases expect the old rule
  ui      row 14 · default theme → none           planned: 14.2 (open) — edited in place, nothing built
  search  row 20 · search bar bottom → top        built: 20.1 (done) · 2 task docs describe it
  brand   row 30 · logo → mascot                  nothing built yet
Spec-delta records: 3 · task docs to relabel: 4 · cases to re-design: 5 · areas to re-plan: ui, search
Write it all, or one area / one decision at a time?
```
**ASK** with that summary. The user may take all, some (one area, some decisions now, the rest
later), or none. A part left for later stays out of every file — write only what was agreed.

## 3. Write what was agreed

The spec files and `requirements.md` per `SKILL.md` §§ 1–2. Then, per decision:

| The change | Write |
|---|---|
| a done task was built on the old decision | a `spec-delta` (`SKILL.md` § 3); reuse an existing `id` for the same delta. `docs[]` = the task docs from § 2, `code[]` = the paths their sections name — that list is how `/clio:memo` later relabels them; without it `clio:context` keeps serving a doc the change made untrue. `blocked_by: null` once the new decision is settled — that is the work queue |
| only open tasks were planned on it | no delta — `/clio:plan` edits those drafts in place |
| nothing built or planned | no delta — `/clio:plan` reads the spec itself |
| it answers what an open `spec-blocked` waited on | a new line under that record's `id`, in full, `blocked_by: null`; never edit the old line or change its `kind` |

```bash
cat >> .claude/clio/database/debt.jsonl <<'EOF'
{"date":"YYYY-MM-DD","id":"<kebab-key>","kind":"spec-delta","status":"pending","domain":"checkout","what":["<old> → <new>"],"req":["18"],"specs":[".claude/clio/docs/specs/memory/<file>.md"],"docs":["<task docs built on the old decision>"],"code":["<paths they name>"],"action":"<the rework>","source":"<source §n, date>","blocked_by":null,"issue":null}
EOF
clio validate debt <N records appended>
```

**The row marker**, when the *decision* changed — decisions only, never build state:

| Marker now | The change | Do |
|---|---|---|
| ⚠️ / ❌ | the open point got decided | → ✅, reason = decision + date |
| ⚠️ / ❌ | a different part is still open | keep, rewrite the reason |
| ✅ | reopened or reversed | → ⚠️, say what reopened it |
| ✅ | refined | keep ✅, append the decision + date |

**Moving toward ✅ removes a stop, so it asks first**: every such row in one `AskUserQuestion` as
`row · old reason → new decision · deciding source`; write only the approved ones. The other moves
add or keep a stop — write them. Never flip on a low-priority source; the marker and `blocked_by`
must tell the same story. A change to row `0` (the stack) → [STACK.md](STACK.md).

## A change withdrawn

The user drops a change that was ingested earlier, the same day or later ("không muốn sửa nữa"). It is a
change like any other, weighed and shown first (§ 2), written the other way round:
- The decisions of the withdrawn change get `Superseded YYYY-MM-DD: withdrawn`. The decisions it had
  superseded get `Reinstated YYYY-MM-DD: <the change> was withdrawn`. One new decision says what holds
  again, in a line — a pointer to the reinstated bullets, not a copy of them.
- A ⚠️ the change had opened, which the withdrawal makes moot, leaves `## Open`; the new decision says
  so, so the question is not lost silently.
- Row markers go back to what the reinstated decisions say; moving toward ✅ asks first, as above.
- Debt: the records of the change close (`status` `done`, `action` says withdrawn). Work already built on
  it gets a new `spec-delta` (docs and code as usual), which `/clio:plan` turns into voided drafts,
  withdrawn tasks (work that never left the working tree) or revert tasks (work that is committed).
- Search with `clio q spec-grep`: it skips what is already `Superseded`, so the weighing sees only rules in force.

## Report

Besides `SKILL.md` § 4: each delta as `id` · `blocked_by` · row · action, queue first; rows moved
(old → new, and the source that decided it); records unblocked; any `index.jsonl` record the change
shows to be wrong — reported, never fixed, it is `/clio:memo`'s; the parts the user left for later.
Then the areas to re-plan, `infra` (row `0`) first — it invalidates the infra plan and the `rules/`
commands `/clio:test` runs:
```text
infra     row 0 · Go 1.22 → 1.23 · rules/go.md names `go test ./...`        →  /clio:plan infra
ui        row 12 · 12.1, 12.3 done on the old rule · spec-delta ui-no-quit
          · cases 12.1-a1, 12.3-u2 test the old rule                         →  /clio:plan ui
brand     row 30 · nothing built                                              →  /clio:plan brand
```
`/clio:plan` turns each delta into a sub-task and edits open drafts in place; `/clio:test`
re-designs the stale cases. This skill writes neither plans nor cases.
