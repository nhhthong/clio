# Change — the area already has tasks

For a spec that moved, a changed mind, a task to drop, or a done task whose tests fall short. Then `SKILL.md` § 4 (show, ask, write).

## One rule: a task is a draft until it is done
`clio q plan <area> --all` gives each status.
- **open** → **edit in place**: one `clio add` record with only the fields that change. No new id, no history section; the store keeps the old record. Its approved cases go stale: `/clio:test` shows what changed and asks again.
- **done** → never edited (`clio add` refuses). Later work is a new task `<id>.<n>` with `"needs":["<id>"]` — except work that never left the working tree (withdraw, below).
- **superseded / void** → history.

| Asked | Do |
|---|---|
| change an open task (wording, levels, touches, tier) | `{"type":"task","id":"5.2","task":"<new>"}` |
| drop an open task | `{"type":"task","id":"5.2","status":"void"}`. `/clio:test` removes its cases; its runs stay; the gate refuses a void task. Code already written for it → list its `touches`, **ASK** before reverting anything (the files may hold other work) |
| replace an open task | the new task, then `{"type":"task","id":"5.2","status":"superseded","by":"5.2.1"}` in the same call |
| change what a done task does (a `spec-delta`, or a built decision reversed) | a sub-task `5.2.1`: the new behaviour, its levels, `"needs":["5.2"]`, `"delta":"<id>"`. A built decision that `/clio:ingest` has not recorded is a spec change: say so, it files the delta |
| take a done task's behaviour out, **work committed** | `git revert`, plus a sub-task stating the behaviour now, `levels` with `regression` (the route 404s, the control is gone) |
| drop done tasks whose work **never left the working tree** (`clio q built --task <id>` shows no commit) | **withdraw**: no revert task, git already holds the old state. Show the tasks and the `git status` of their `touches`, **ASK**, restore the files (`git restore`, delete the new ones), then `clio test withdraw <ids>` (all tasks of one abandoned change in one call). It is left out of `allowed-tools` on purpose: the prompt is the user's yes. It refuses while a touched file still differs from git, a done task still needs one of them, or a commit is recorded. It voids them, removes their cases, and lists the docs `/clio:memo` relabels |
| a done task's tests fall short (`clio test coverage <id>`: `no cases`, a missing level, a last run `fail`) | one "Harden" sub-task **per task doc** (`clio q built --task <id>`, type `task`): id `<highest id it covers>.<n>`, `needs` every task it covers, `levels` the missing ones plus `regression` for a failing case |
| try something, keep it if it works | suggest a branch first (`git switch -c try/<name>`); works only if `.claude/clio/` is committed |

Check both causes before deciding nothing is needed: `clio q owed --req <req>` (spec moved?) and `clio test coverage <id>` (tests enough?). A `spec-delta` is carried by `id` in a task's `delta` (an open delta named in no task is a `clio validate all` warning). A revert or hardening is a task like any other: its cases must fail while the gap is there. Many small changes to one draft: still edit in place.

Report, besides `SKILL.md` § 5: every task edited (field: old → new), voided or superseded, every sub-task added and why.
