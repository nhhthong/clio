---
name: test
description: Design, write, run and gate the tests for plan tasks, in batches — cases per level the plan named, expected values from the spec, approved in one question, evidence recorded by a script that only passes a task whose every case passed on the current code. Use when the user asks to test, design test cases or run tests.
argument-hint: "[task id such as 3.3 | several ids | area | gate <task-id>]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test run *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test run-task *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test red *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test gate *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test diff *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test history *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test coverage *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test fp) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio q *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio add test *)
---

**Run only when the user asked, this turn** — by slash command or in plain words ("test task 3.3", "viết test case", "chạy test"). Not triggers: the drift nudge, your sense that work looks finished, a TODO, a subagent's report. Unsure → ask in one line, don't run.

`/clio:plan` said *which* levels a task needs; this skill says *what* each tests, proves it, and refuses a task whose proof is missing. It writes the tests and the least code that makes each approved case pass. It never ticks a task: `/clio:memo` does, after the gate. Target: $ARGUMENTS

`clio` = `${CLAUDE_PLUGIN_ROOT}/bin/clio`, by full path every call. Run cases **only through the script**; a pass it did not record does not exist. **Never write `runs.jsonl` or a store file yourself** (a hook refuses), **never report a pass the script did not print.** Evidence is bound to a fingerprint of the working tree: edit code after a pass and it stops counting. The repo's own build command you may run directly.
```bash
clio test run-task <id>...             # every case of each task, repeat times, one runs.jsonl line per case
clio test red <id>... [--base <rev>]   # cases that need red, on the base commit's code with today's tests
clio test run <case-id> | gate <id> | diff <id>... | history <case-id>
```

## 1. Load, pick the batch
`clio q context <ids|area>` (rows, spec, built, owed, rules, open tasks `ready`/`waits on`), then the spec's `## Decisions`, the code in `touches`, `.claude/rules/*.md` for test commands. A task's `levels`, `tier`, `touches`: `clio q plan --id <id>`. Existing cases: `clio q cases <task|area>` (a re-design). An area → its open tasks whose `needs` are done, in plan order; cap **5 tasks or ~30 cases** (past that a yes is skimmed); say what waits. A `void`/`superseded` task: remove its cases (`{"type":"case","id":"…","status":"removed"}`), nothing to run.

**Fast runs.** A `Batch:` line in `.claude/rules/*.md` covers the stack → each case's `command` is its template with `{tests}` = that case's one test id. None → read [BATCH.md](BATCH.md) before the first run.

## 2. Seams
The public boundaries tests observe (a signature, route, CLI command, queue message, page); they go in the task's meta `seams`, shown in the same question as the cases. Tests go only through them: no private methods, no mocking the task's own collaborators; mock only what it does not own (third-party API, clock, randomness). A test that breaks on a behaviour-preserving refactor is wrong.

## 3. Design the cases
`clio q levels <the task's levels>` prints what each must cover (the catalog is [LEVELS.md](LEVELS.md); never read it whole). Every named level gets ≥ 1 runnable case; a level that cannot apply goes back to `/clio:plan`. Each `level.n` id that applies is a case (its id in `covers`); one that does not → an `na` entry in the meta, with the reason. The gate holds every id of a named level to one or the other. A risk `q levels choosing` would flag that the plan lacks → say so, don't add the level.
- **Expected values come from outside the code** (a number in `## Decisions`, a worked example, a literal): `expected` holds it, `source` says where. Re-computing it with the code's logic passes by construction. No source → ⚠️, not a case.
- **perf / load / stress need a number from the spec; resilience needs the behaviour it names.** None → no case; file `spec-blocked` via `/clio:memo`. Never invent a threshold.
- **mutation** (only where the plan names it): one case whose command exits non-zero below the threshold (80 %, or the project's); the tool is settled once, in `/clio:plan`.
- A tool the level needs and the repo lacks (Playwright, k6, Pact, a mutation tester) → propose it from its current docs (Context7), **ASK**, record an ADR (`memo/steps/RARE.md`).
- **One case, one command, one behaviour**: it runs exactly that case, on one line, and exits non-zero on failure; two cases of a task never share a command. `repeat` ≥ 20 for `concurrency`, interleaving forced (barrier, latch, `-race`). A **light** task: one case for its one level; several light tasks in one short table.

**One question for the whole batch — seams, cases, `na` — and ASK before writing.** The case list is the definition of done. Order: seams; **critical tasks first**, each under its own heading with what must be seen red; the other tasks; levels sent back to `/clio:plan`; ⚠️ values that blocked a case. A re-design shows `clio test diff <tasks>`, not the whole table. On a yes:
```bash
clio add test <area> <<'EOF'
{"type":"case","id":"3.3-u1","task":"3.3","level":"unit","covers":["unit.1"],"behaviour":"page 2 of 120 has 50","expected":"50 items","source":"spec: \"50 per page\"","command":"go test ./orders -run 'TestPage2$'","repeat":1}
{"type":"meta","id":"3.3","seams":["GET /orders"],"na":{"security.2":"public route"}}
EOF
```
A record names only what it sets. Then record the yes, for exactly the accepted tasks: `clio test approve 3.1 3.3`. It is left out of `allowed-tools` on purpose: its permission prompt is the user's own yes. With prompts turned off, say so: only their word stands behind it, and they may prefer `! clio test approve …`. Any later change to a task's cases or `na` voids its approval only: show `clio test diff`, ASK, approve again.

## 4. Write, run once — red only where it proves something
Only **`regression` cases and every case of a `critical` task** (except mutation) must be seen red; the gate asks for no other. Other tasks: write the tests and the least code that passes, build, then `clio test run-task 3.1 3.3`. Failures → fix the code, never loosen a test. `run-task` names other tasks whose `touches` overlap: run them too. That list sees shared files only, so after the batch also run the repo's whole test suite directly (command in `.claude/rules/`; it records nothing). A failing test of a done task is a plan gap: report it, `/clio:plan` adds the task; never loosen or delete the test.

Tasks needing red: read [RED.md](RED.md). Tests first; no code yet → a bare stub, then `run-task`; code exists → `clio test red <task>`, then `run-task`. Red counts only if it failed on its assertion; **never break code by hand**. Test files are recognised by path (`_test.`, `.spec.`, `test_*.py`, `tests/`…); a test named otherwise counts as code.

Long levels (load, stress, perf, mutation, UI e2e): a Bash timeout up to 600000 ms or `run_in_background`; each command is capped at `CLIO_TIMEOUT` seconds (600) and reports every minute; a fast suite that hangs → a low `CLIO_TIMEOUT`. Never start infra, use a secret or hit a paid/shared service on your own. **One runner at a time per build** (shared `target/`, `build/`), and create no file while a run is going.

## 5. Gate
`clio test gate 3.1`, one call per task; `OK` is the only pass, every other line names what is missing. **Flaky is failed**: one red in `repeat`, or a fail on this code after a pass, fails the case; only a code change clears it, and `/clio:memo` files `code-debt` `flaky:`. A stale incremental build can fake one: rebuild clean first.

## 6. Report
Tasks approved, sent back, left for the next batch · seams · cases per level, levels sent back · `na` ids and why · reds seen (`NOT RED`) · each gate's output verbatim · overlapping tasks run · ⚠️ that blocked a case · tools proposed. Then `/clio:memo <task>` records the work and ticks it, only on a passing gate.
