# Change

The area already has tasks, and a spec moved, the user changed their mind, a task must go, or a done task's tests fall short. Then show, ask and write as in `SKILL.md` step 4.

## One rule: a task is a draft until it is done
`clio q plan <area> --all` shows each status.
- Open: edit in place. Send one record with only the fields that change, and keep the id. The store keeps the old record. The approved cases go stale, and `/clio:test` shows what changed and asks again.
- Done: never edited, and `clio add` refuses. Later work is a new task `<id>.<n>` with `needs` holding the done id. The exception is work that never left the working tree (see withdraw below).
- Superseded or void: history.

| Asked | Do |
|---|---|
| Change an open task (wording, levels, touches, tier) | A record with the id and the new fields |
| Drop an open task | A record with `status` void. `/clio:test` removes its cases, its runs stay, and the gate refuses a void task. If code was already written for it, list its `touches` and ask before reverting anything, because the files may hold other work |
| Replace an open task | The new task, then a record on the old id with `status` superseded and `by` set to the new id, in the same call |
| Change what a done task does (a `spec-delta`, or a built decision reversed) | A sub-task `5.2.1` with the new behaviour, its levels, `needs` holding `5.2`, and `delta` holding the delta id. A built decision that `/clio:ingest` never recorded is a spec change: say so, and that skill files the delta |
| Take a done task's behaviour out, work committed | `git revert`, plus a sub-task stating the behaviour now, with level `regression` (the route returns 404, the control is gone) |
| Drop done tasks whose work never left the working tree (`clio q built --task <id>` shows no commit) | Withdraw: no revert task, because git already holds the old state. Show the tasks and the `git status` of their `touches`, and ask. Restore the files (`git restore`, delete the new ones), then run `clio test withdraw <ids>`, all tasks of one abandoned change in one call. It is left out of `allowed-tools` on purpose, so the permission prompt is the user's yes. It refuses while a touched file still differs from git, a done task still needs one of them, or a commit is recorded. It voids the tasks, removes their cases and lists the docs `/clio:memo` relabels |
| A done task's tests fall short (`clio test coverage <id>` shows `no cases`, a missing level, or a last run `fail`) | One "Harden" sub-task per task doc (`clio q built --task <id>`, type `task`). Its id is the highest id it covers plus `.<n>`, its `needs` lists every task it covers, and its `levels` are the missing ones plus `regression` for a failing case |
| Try something, keep it if it works | Suggest a branch first (`git switch -c try/<name>`). This works only if `.claude/clio/` is committed |

Check both causes before deciding nothing is needed. `clio q owed --req <req>` shows whether the spec moved. `clio test coverage <id>` shows whether the tests are enough. A `spec-delta` is carried by its `id` in a task's `delta`; an open delta named in no task is a `clio validate all` warning. A revert or a hardening is a task like any other: its cases must fail while the gap exists. Many small changes to one draft still edit in place.

## Report
Add to the report in `SKILL.md`: every task edited (field, old to new), voided or superseded, and every sub-task added and why.
