# Change — the area already has tasks

Read by `/clio:plan` when the target's tasks exist: the spec moved, the user changed their mind, a
task is to be dropped, or a done task's tests fall short. Then back to `SKILL.md` § 4 to show, ask
and write.

## The one rule: a task is a draft until it is done

`clio q plan <area> --all` gives each task's status.

| Status | What a change may do |
|---|---|
| `open` — nobody ticked it | **edit it in place**: one `clio add` record with the fields that change. No new id, no history section. Its approved cases go stale with it: `/clio:test` shows what changed and asks again |
| `done` — the gate passed and it was ticked | **never edited** — `clio add` refuses. Later work is a new task `<id>.<n>` with `"needs":["<id>"]`. The one exception is work that never left the working tree: it can be withdrawn (below) |
| `superseded` / `void` | history; nothing to change |

The store keeps every earlier record, so editing a draft loses nothing: the old wording is still in
the file, and the report says what moved.

## What the user or the spec asks for

| Asked | Do |
|---|---|
| change what an open task does — wording, levels, touches, tier | `{"type":"task","id":"5.2","task":"<new>",…}` — only the fields that change |
| drop an open task ("bỏ 5.2", the user tried it and does not want it) | `{"type":"task","id":"5.2","status":"void"}`. Its cases are dropped by `/clio:test` (`status: removed`); its runs stay in `runs.jsonl` and the gate refuses a void task. Code already written for it → list its `touches` and **ASK** before reverting anything — the files may hold other work |
| replace an open task by a different one | the new task, then `{"type":"task","id":"5.2","status":"superseded","by":"5.2.1"}` in the same call |
| change what a done task does (a `spec-delta`, or the user reverses a decision that was built) | a sub-task `5.2.1`: the new behaviour, its levels, `"needs":["5.2"]`, `"delta":"<delta id>"` when a delta exists. A decision that was built is a spec change: if `/clio:ingest` has not recorded it, say so — it files the delta and marks the spec |
| take a done task's behaviour out, and the work **is committed** | `git revert`, plus a sub-task that states the behaviour now: `levels` with `regression` — the route 404s, the control is gone |
| drop a done task whose work **never left the working tree** (tried, then abandoned; `clio q built --task <id>` shows no commit) | **withdraw** it: no revert task, because git already holds the old state. Show the user the tasks and `git status` of their `touches`, **ASK**, restore the files (`git restore <paths>`, delete the new ones), then run `clio test withdraw <ids>` — it is left out of this skill's `allowed-tools` on purpose, the permission prompt is the user's yes. It refuses while a touched file still differs from git, while a done task still needs one of them, or when a commit is recorded. It voids the tasks, removes their cases from the store, and lists the docs `/clio:memo` must relabel. Every task of one abandoned change goes in one call |
| a done task's tests fall short — `clio test coverage <id>` says `no cases`, lacks a level § 3 requires today, or shows a last run `fail` | one "Harden" sub-task **per task doc**, not per task (`clio q built --task <id>`, type `task` only): id `<highest id it covers>.<n>`, `needs` every task it covers, `levels` the missing ones plus `regression` for a failing case |
| try something out, keep it only if it works | suggest a git branch first (`git switch -c try/<name>`): planned, tested and dropped there, nothing reaches the main line's plan. Works only if `.claude/clio/` is committed |

For each task, check both causes before deciding nothing is needed:
```bash
clio q owed --req <task's req>   # spec moved?
clio test coverage <id>          # tests enough?
```

- A `spec-delta` is carried by `id` in the task's `delta`: an open delta named in no task is what
  `clio validate all` warns about.
- A revert or a hardening is a task like any other. Its cases must fail while the gap is there, or
  nobody can tell a fix from a claim of one.
- Many small changes in a row on the same draft: still edit in place. The plan shows the current
  intent; the store file is the log.

Report, besides `SKILL.md` § 5: every task edited (field: old → new), voided or superseded, every
sub-task added and why (spec, change of mind, tests).
