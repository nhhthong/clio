# Red — for tasks that must be seen failing

Read by `/clio:test` § 4 only when the batch holds a `regression` case or a `critical` task.

**Tasks that need red.** Write the tests first, then:
- **The code does not exist yet** → add the bare seam (the signature, a route returning 501, a stub
  returning the zero value), run the build, `run-task` → every case fails **on its assertion**. Then
  implement and `run-task` again.
- **The code exists, or the fix is written** → `clio test red <task>`: it runs those cases on the
  code of the base commit (default `HEAD`, i.e. before your uncommitted change) in a worktree
  holding today's test files, and records the red. The worktree is kept at `.git/clio-red` and
  reused, so the next `red` rebuilds only what changed; `--fresh` starts it over. Nobody edits code to break it. Already
  committed the change → `--base <the commit before it>`. Then `run-task` on today's code.

Read every red's output: a red counts only if it failed **on its assertion** — a build error, a
missing fixture or a wrong path is a red for the wrong reason; fix the test and redo it. Under a
`Batch:` line the script checks part of this itself: a test the runner's report does not show (the
base did not compile) is `NOT RED … did not run`, and the gate never counts it. When the base cannot
compile the tests at all (they call code the base lacks), `red` cannot help — use the stub route
above on today's code instead, and say so. A `red` run is never read as today's result: the gate's
"last run" is the last run on this code, so run `run-task` after `red`, not the other way round. A case the
script reports `NOT RED` passed on the old code. Two different reasons, two different answers —
**never break code by hand to get a red**:
- **The test is weak** — the bug was there and the case did not see it: strengthen the case (show
  the user `clio test diff`, approve again) and run `red` again.
- **The behaviour was always right** — a hardening task: the base never had the bug, so no red
  exists to find. This exit is for `critical` tasks only; a `regression` case that will not go red
  does not reproduce its bug — rewrite it until it does. If the task names `mutation`, a passing
  mutation case stands in for red on its other cases (the gate prints a `NOTE`). If it does not and many cases come back `NOT RED`, propose
  `mutation` for the task to the user (`/clio:plan` adds it) — unless the project's `mutation`
  record says tool `none`. Otherwise, one case at a time, propose a waiver in the task's test meta:
  ```json
  {"type":"meta","id":"3.4","waived":{"3.4-u2":"correct since before a1b2c3d; red --base a1b2c3d passed"}}
  ```
  It is part of what the user approves, so they say yes to it like to a case. The gate accepts it
  only if a `red` run of that case with these test files **passed** on a base commit — a waiver
  stands on a tried red, never instead of one.
