---
name: test
description: Design, write, run and gate the tests for plan tasks, in batches — cases per level the plan named, expected values from the spec, approved in one question, evidence recorded by a script that only passes a task whose every case passed on the current code. Use when the user asks to test, design test cases or run tests.
argument-hint: "[task id such as 3.3 | several ids | area | gate <task-id>]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test run *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test run-task *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test red *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test gate *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test diff *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test history *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test coverage *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test fp) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio q *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio add test *)
---

**Run only when the user asked for it, this turn** — by slash command, or in plain words ("test task 3.3", "viết test case", "chạy test"). None of these is a trigger: Clio's drift nudge · your own sense that the work looks finished · a TODO you wrote · a subagent's report. Unsure → ask in one line, don't run.

`/clio:plan` said *which* levels a task needs. This skill says *what* each level tests, proves it, and
refuses a task whose proof is missing. It writes the tests, and only the least code that turns each
approved case pass — nothing the case list does not ask for. It never ticks a task: `/clio:memo`
does, and only after the gate passes.

Target: $ARGUMENTS

```bash
clio test run-task <task-id>...            # every case of each task, repeat times each, one runs.jsonl line per case
clio test red <task-id>... [--base <rev>]  # the cases that need red, on the base commit's code with today's tests
clio test run <case-id>                    # one case on its own
clio test gate <task-id>                   # exit 0 only when every case has fresh, complete, passing evidence
clio test diff <task-id>...                # what changed in the cases since their last approval
clio test history <case-id>                # every recorded run of one case, red runs marked
```
`clio` is `${CLAUDE_PLUGIN_ROOT}/bin/clio`; each Bash call is a fresh shell, so write the full path
every time, never a variable. Run cases **only through the script** — a pass it did not record does
not exist. The repo's own build command (from `.claude/rules/*.md`) you may run directly. **Never
write `runs.jsonl` or a store file yourself** (a hook refuses it), **and never report a pass the
script did not print.** Evidence is bound to a fingerprint of the working tree: edit any code after
a pass and that pass stops counting.

## 1. Load — and pick the batch

Run the `clio:context` skill for the target. Read each task with `clio q plan --id <id>` — `levels`,
`tier`, `touches` — the spec's `## Decisions`, the code in `touches`, and `.claude/rules/*.md` for the
repo's test commands. Existing cases → `clio q cases <task|area>`; this is a re-design.

An area → the batch is its open tasks whose `needs` are all done (`clio q summary` names the first;
`clio q plan <area>` lists the rest), in plan order. Cap a batch at **5 tasks or ~30 cases** — past
that the user skims, and a skimmed yes is not an approval. Say which tasks wait for the next batch.

A task that is `void` or `superseded`: its cases go — `{"type":"case","id":"<case>","status":"removed"}`
each, in the same `clio add` call as the batch. Nothing to approve or run for it.

## 1b. The fastest way to run — found once per stack

Before the first run on a stack, look for a `Batch:` line in `.claude/rules/*.md` covering it. Found
→ each case's `command` is that template with `{tests}` replaced by its one test id, word for word.
None → read [BATCH.md](BATCH.md) and do what it says before running anything: one runner start for
many cases is the largest saving here (Maven + Spring, 8 cases: 72 s → 11 s).

## 2. Seams

The **seams** are the public boundaries the tests observe: a function's signature, a route, a CLI
command, a message on a queue, a page. They go in the task's test meta (`seams`) and are shown in the
same question as the cases. Tests go only through agreed seams: no private methods, no internal
collaborators mocked, no side channel the user never sees. Mock only what the task does not own — a
third-party API, the clock, randomness. A test that breaks on a refactor that kept behaviour is wrong.

## 3. Design the cases

Per level the task names, the cases [LEVELS.md](LEVELS.md) lists for it — read the section of each
level you design, not the whole file. Every level gets at least one runnable case; a level that truly
cannot apply goes back to `/clio:plan`, never silently dropped. Each numbered bullet (`level.n`) of a
level's section that applies is a case — its id goes in the case's `covers`. One that does not apply
→ an `na` entry in the task's test meta with the reason. The gate holds every id of a named level to
one or the other. A risk LEVELS.md § Choosing would flag and the plan lacks → say so in the report;
do not add the level yourself.

- **Expected values come from outside the code**: a number from `## Decisions`, a worked example, a
  known-good literal — `expected` holds it, `source` names where it came from. Re-computing it with
  the code's own logic passes by construction. No source → ⚠️, not a case.
- **Perf, load, stress need a number from the spec**; **resilience needs the behaviour the spec
  names**. None stated → no case; file `spec-blocked` via `/clio:memo`. Never invent a threshold.
- **Mutation** (only where the plan names it) → one case whose command exits non-zero below the
  threshold (Stryker `--thresholds.break`, PIT `mutationThreshold`, go-mutesting score); 80 % unless
  the spec or the project's `mutation` record sets one.
- A tool the level needs and the repo lacks (Playwright, k6, Pact, a mutation tester) → propose it
  from its current docs (Context7), **ASK**, record the choice as an ADR per
  `${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/WRAP-UP.md` § ADR.
- **One case, one command, one behaviour.** The command runs exactly that case (`-run TestX$`,
  `-t "name"`, `-k name`), on one line, and exits non-zero on failure. Pipes and quotes are fine.
  With a `Batch:` line the script still starts the runner once for many such commands. Two cases of a
  task never share a command — the gate refuses it; write the second test.
- `repeat` ≥ 20 for `concurrency` (the gate refuses less), and every concurrency case forces the
  interleaving (barrier, latch, `-race`) rather than hoping for it.

**A `light` task** (LEVELS.md § Tier): one case for its one level, no `na` bookkeeping beyond what
the gate asks, and several light tasks shown as one short table.

**One question for the whole batch — seams, cases, `na` lines — and ASK before writing.** The case
list is the definition of done. Lay it out so the risky part is read first: the seams; **critical
tasks first**, each under its own heading with what must be seen red (§ 4); the other tasks, one
table each; levels you would send back to `/clio:plan`, and ⚠️ values that blocked a case. A
re-design shows `clio test diff <tasks>` instead of the whole table — one line per kind of edit.

On a yes, write what was accepted, one call per area:
```bash
clio add test <area> <<'EOF'
{"type":"case","id":"3.3-u1","task":"3.3","level":"unit","covers":["unit.1"],"behaviour":"page 2 of 120 items has 50","expected":"50 items","source":"spec: \"50 per page\"","command":"go test ./orders -run 'TestPage2$'","repeat":1}
{"type":"meta","id":"3.3","seams":["GET /orders"],"na":{"security.2":"the route is public; no owner to check"}}
EOF
```
A record names only what it sets; an edit is a record with the id and the changed fields. Then record
the yes, for exactly the accepted tasks — nothing else runs `approve`, and it is left out of this
skill's `allowed-tools` on purpose: the permission prompt it raises is the user's own yes, not yours.
If the user runs Claude Code with prompts turned off, say so: then only their word in this
conversation stands behind the approval, and they may prefer to type it themselves (`! clio test approve 3.1 3.3`).
```bash
clio test approve 3.1 3.3 3.4      # one record and hash per task; the gate fails a task whose cases change after
```
Any later change to a task's cases or `na` lines — a looser expected, a lower repeat, a removed case
— voids that task's approval only: show `clio test diff`, ASK, approve it again.

## 4. Write, run once — red only where it proves something

**Only two kinds of case need to be seen red**, and the gate asks for no other: every `regression`
case — it must reproduce the bug — and every case of a `critical` task except `mutation`.

**Tasks with neither** (most of them): write the tests and the least code that makes them pass, run
the build, then one call — `clio test run-task 3.1 3.3 3.4`. Failures → fix the code (never loosen a
test) and re-run. Refactor, re-run once. `run-task` names other tasks whose `touches` overlap: run
them too before reporting, so a change here that broke them is seen now, not in a later session. That
list only sees shared files, not a shared constant or a value another module reads: so after the batch
also run the repo's whole test suite directly (the command in `.claude/rules/*.md`; it records nothing,
it only looks). A test that fails there and belongs to a done task is a gap in the plan — report it, and
`/clio:plan` adds the task; never loosen or delete the test.

**Tasks that need red**: read [RED.md](RED.md) first. In short: tests first; code that does not
exist yet → a bare stub and `run-task`; code that exists → `clio test red <task>` on the base commit,
then `run-task`. A red counts only if it failed on its assertion — **never break code by hand**.

- Test files are recognised by path (`_test.`, `.test.`, `.spec.`, `test_*.py`, `tests/`, `spec/`,
  `src/test/`, `__tests__/`…); a test named otherwise counts as code — name it the usual way.
- Long levels (`load`, `stress`, `perf`, `mutation`, e2e with a UI, a big-repeat `concurrency`): a
  Bash timeout that covers them (up to 600000 ms) or `run_in_background`; each command is capped at
  `CLIO_TIMEOUT` seconds (default 600) and says it is still running every minute. Under a `Batch:`
  line the cap covers the whole runner start. A fast suite that hangs → a low `CLIO_TIMEOUT` (60) shows
  it in a minute instead of ten. Never start infra (docker, a staging target), use a secret or hit a
  paid or shared service on your own: say what is needed and ask.
- **One runner at a time per build** — Maven, Gradle, cargo and most bundlers share one output
  directory, and a second writer corrupts it. Create no new file while a run is going: an untracked
  file that appears during a run is recorded as its artifact and left out of the fingerprint.

## 5. Gate

```bash
clio test gate 3.1       # one call per task — it reads runs.jsonl, it runs no test
```
`OK` is the only pass; every other line names what is missing, and is the task's to fix. **Flaky is
failed**: one red run in `repeat` fails the case, and so does a fail on this code after it once passed
— re-running until green does not clear it, only a code change does; `/clio:memo` files it as
`code-debt` with `what` starting `flaky:`. A stale incremental build can fake one (a file restored by
git keeps its old mtime): rebuild clean and look at the failure before calling a case flaky.

## 6. Report

Batch: tasks approved, sent back, left for the next batch · seams agreed · cases per level and levels
sent back to `/clio:plan` · the `na` ids written and why · reds seen (and any `NOT RED`) · the gate
output of each task, verbatim · other tasks `run-task` named and their result · ⚠️ values that
blocked a case · tools proposed. Then: `/clio:memo <task>` records the work and ticks the task,
which it does only on a passing gate.
