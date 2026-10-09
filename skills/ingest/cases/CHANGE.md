# A change

Rows exist and something moved: a new source, a spec file or keyword, a change in plain words, or a sweep of hand edits. Specs move while code stands still, so work out what the change invalidates before writing it.

## 1. List the change decision by decision
For each word the change turns on, run `clio q spec-grep '<word>'`. It lists the decisions in force that mention the word, across areas, which is better than reading `memory/` by hand.

List every decision added, altered, reversed or resolved, as old rule and new rule. The old rule comes from the current `memory/*.md`. For a sweep it comes from the hand edits since the last ingest, uncommitted and new files included: `clio q spec-diff --stat` shows which files moved, `clio q spec-diff` shows the lines.

The baseline is clone-local (`refs/clio/*` is never pushed), so a fresh checkout has none. Try `git diff -M <commit> -- .claude/` from a `Last ingest:` line in an older `requirements.md`, else the dated notes and what the task docs assumed. With no before-state, the delta has the new rule only. Say so.

## 2. Weigh it before writing anything
Run `clio q context <row> [<row>...]` for the rows involved. It merges rows and shows what was built on them, open debt and plan tasks. Run `clio q cases <task>...` for the cases whose expected value rests on the old rule. A value one decision changes (a width, a limit, a key, a name) is often read by others, so run `clio q spec-grep '<old value>'` again.

Show the user a summary before touching any file: per decision, the area, row, old rule and new rule, plus what is built on it (done tasks, cases that expect the old rule, task docs that describe it) or planned on it (open drafts) or nothing. End with the counts: spec-delta records, task docs to relabel, cases to re-design, areas to re-plan. Ask whether to write all of it, or one area or decision at a time. The user may take all, some or none. A part left for later stays out of every file.

## 3. Write what was agreed
Write the spec files and `requirements.md` as in `SKILL.md`. Then per decision:

| The change | Write |
|---|---|
| A done task was built on the old decision | A `spec-delta` record (reuse the `id` for the same delta). `docs[]` lists the task docs from step 2, `code[]` the paths they name; `/clio:memo` later uses them to relabel. Set `blocked_by` to null once the new decision is settled: that is the work queue |
| Only open tasks were planned on it | No delta. `/clio:plan` edits those drafts in place |
| Nothing built or planned | No delta |
| It answers an open `spec-blocked` record | Update that record with `blocked_by` null. Never change its `kind` |

Write records with `clio add debt` (JSON on stdin; fields in `memo/steps/DEBT-IT.md`). A spec-delta needs `id`, `kind`, `domain`, `what` as "old to new", `req`, `specs`, `docs`, `code`, `action` and `source`.

Row markers follow the decision, never the build state. An open or blocked row becomes decided when the point got decided (reason: decision and date). It stays open or blocked, with the reason rewritten, when another part is still open. A decided row becomes open when reversed or reopened. A decided row stays decided, with decision and date appended, when only refined.

A move toward decided removes a stop, so ask first. Put every such row in one question as `row, old reason, new decision, deciding source`, and write only the approved ones. Never move a row on a low-priority source. The marker and `blocked_by` must tell the same story. Row `0` (the stack) follows [STACK.md](STACK.md).

## A change withdrawn
The user drops a change ingested earlier ("không muốn sửa nữa"). Write it the other way round, after the same weighing.
- Mark the change's decisions `Superseded YYYY-MM-DD: withdrawn`. Mark the ones it had superseded `Reinstated YYYY-MM-DD: <the change> was withdrawn`. Add one decision that says what holds again, as a pointer and not a copy.
- An open point the change created, now moot, leaves `## Open`; the new decision says so. Row markers go back to what the reinstated decisions say. A move toward decided asks first.
- Close the change's debt records (`status` done, `action` says withdrawn). Work already built on it gets a new `spec-delta`. `/clio:plan` turns it into voided drafts, withdrawn tasks (never committed) or revert tasks (committed).

## Report
Add to the report in `SKILL.md`: each delta as `id`, `blocked_by`, row, action, work queue first; rows moved (old to new, deciding source); records unblocked; any `index.jsonl` record the change shows to be wrong (report it, never fix it: that is `/clio:memo`'s job); what the user left for later. Then list the areas to re-plan, `infra` first, each with its row, what moved and the `/clio:plan <area>` to run.

`/clio:plan` turns each delta into a sub-task and edits open drafts in place. `/clio:test` re-designs the stale cases. This skill writes neither.
