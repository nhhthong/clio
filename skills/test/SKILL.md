---
name: test
description: Design, write, run and gate the tests for plan tasks, in batches. Cases are designed per level the plan named, with expected values taken from the spec, approved in one question, and run by a script that records the evidence. Use when the user asks to test, design test cases or run tests.
argument-hint: "[task id such as 3.3 | several ids | area | gate <task-id>]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test run *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test run-task *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test red *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test gate *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test diff *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test history *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test coverage *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test fp) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio q *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio add test *)
---

Target: $ARGUMENTS

Run only when the user asked this turn, by slash command or in plain words ("test task 3.3", "viết test case", "chạy test"). A drift nudge, a TODO or a subagent report is not a request. Unsure: ask in one line.

`/clio:plan` says which levels a task needs. This skill decides what each level tests, proves it, and refuses a task whose proof is missing. It writes the tests and the least code that makes each approved case pass. It never ticks a task: `/clio:memo` does, after the gate.

## Ground rules
- Run cases only through the script. A pass it did not record does not exist, so never report one it did not print.
- Never write `runs.jsonl` or a store file yourself. A hook refuses it.
- Evidence is bound to a fingerprint of the working tree. Edit code after a pass and the pass stops counting.
- You may run the repo's own build command directly.
- The scripts: `clio test run-task <id>...` runs every case of each task and records one line per case. `clio test red <id>...` runs red-needing cases on the base commit's code with today's tests. `clio test run <case-id>`, `gate <id>`, `diff <id>...` and `history <case-id>` do what their names say.

## Steps
1. **Load and pick the batch.** Run `clio q context <ids|area>` for rows, spec, built work, debt, rules and ready tasks. Read the spec's `## Decisions`, the code in `touches`, and `.claude/rules/*.md` for test commands. `clio q plan --id <id>` gives a task's `levels`, `tier` and `touches`. `clio q cases <task|area>` lists existing cases for a re-design.
   - For an area, take its open tasks whose `needs` are done, in plan order, capped at 5 tasks or about 30 cases (past that a yes is skimmed). Say what waits.
   - For a void or superseded task, remove its cases with a record of `status` removed. Nothing to run.
   - If a `Batch:` line in `.claude/rules/*.md` covers the stack, each case's `command` is that template with `{tests}` replaced by the case's one test id. Otherwise read [BATCH.md](BATCH.md) before the first run.
2. **Fix the seams.** A seam is a public boundary the tests observe: a signature, route, CLI command, queue message or page. List them in the task's meta `seams`; they appear in the same question as the cases. Test only through seams: no private methods, and no mocking the task's own collaborators. Mock only what the task does not own (third-party API, clock, randomness). A test that breaks on a behaviour-preserving refactor is wrong.
3. **Design the cases.** `clio q levels <the task's levels>` prints what each level must cover. The catalog is [LEVELS.md](LEVELS.md); never read it whole.
   - Every named level gets at least one runnable case. A level that cannot apply goes back to `/clio:plan`.
   - Every `level.n` id that applies is a case (its id in `covers`). One that does not apply is an `na` entry in the meta, with the reason. The gate holds every id of a named level to one or the other.
   - Take expected values from outside the code: a number in `## Decisions`, a worked example, a literal. `expected` holds it and `source` says where. Recomputing it with the code's own logic passes by construction. No source means no case; raise it as an open point.
   - Perf, load and stress cases need a number from the spec. Resilience needs the behaviour the spec names. Without them, write no case and file a `spec-blocked` record through `/clio:memo`. Never invent a threshold.
   - A `mutation` case exists only where the plan names it: one case whose command exits non-zero below the threshold (80 percent, or the project's).
   - If a level needs a tool the repo lacks (Playwright, k6, Pact, a mutation tester), propose it from its current docs (Context7), ask, and record an ADR (`memo/steps/RARE.md`).
   - One case is one command and one behaviour. It runs exactly that case, on one line, and exits non-zero on failure. Two cases of a task never share a command. Use `repeat` of 20 or more for `concurrency`, with interleaving forced (barrier, latch, `-race`). A light task gets one case for its one level; group several light tasks in one short table.
4. **Ask once for the whole batch** (seams, cases, `na`). The case list is the definition of done. Order the question: seams, then critical tasks first (each under its own heading, with what must be seen red), then the other tasks, then levels sent back to `/clio:plan`, then values that blocked a case. A re-design shows `clio test diff <tasks>`, not the whole table. On a yes, write with `clio add test <area>` and the records on stdin ([RECORDS.md](RECORDS.md)).
   - Then record the yes for exactly the accepted tasks with `clio test approve 3.1 3.3`. It is left out of `allowed-tools` on purpose: its permission prompt is the user's own yes. With prompts turned off, say so, since only their word stands behind it. They may prefer to run it themselves with `! clio test approve ...`.
   - Any later change to a task's cases or `na` voids that task's approval only. Show `clio test diff`, ask, and approve again.
5. **Write and run once.** Red is required only for `regression` cases and every case of a `critical` task (except mutation). The gate asks for no other. For other tasks, write the tests and the least code that passes, build, then run `clio test run-task 3.1 3.3`. On failure, fix the code and never loosen a test. `run-task` names other tasks whose `touches` overlap; run them too. That list sees shared files only, so after the batch also run the repo's whole test suite directly (command in `.claude/rules/`; it records nothing). A failing test of a done task is a plan gap: report it, and `/clio:plan` adds the task. Never loosen or delete that test.
   - For tasks needing red, read [RED.md](RED.md). Write tests first. With no code yet, add a bare stub and run `run-task`. With code present, run `clio test red <task>`, then `run-task`. Red counts only if the case failed on its assertion. Never break code by hand. Test files are recognised by path (`_test.`, `.spec.`, `test_*.py`, `tests/`); a test named otherwise counts as code.
   - Long levels (load, stress, perf, mutation, UI end to end): use a Bash timeout up to 600000 ms or `run_in_background`. Each command is capped at `CLIO_TIMEOUT` seconds (default 600) and reports every minute; a fast suite that hangs needs a lower `CLIO_TIMEOUT`. Never start infrastructure, use a secret or hit a paid or shared service on your own. Run one runner at a time per build (shared `target/`, `build/`), and create no file while a run is going.
6. **Gate.** Run `clio test gate 3.1`, one call per task. `OK` is the only pass; every other line names what is missing. Flaky counts as failed: one red in `repeat`, or a fail on this code after a pass, fails the case. Only a code change clears it, and `/clio:memo` files `code-debt` with `flaky:`. A stale incremental build can fake one, so rebuild clean first.
7. **Report.** Tasks approved, sent back and left for the next batch. Seams. Cases per level and levels sent back. `na` ids with reasons. Reds seen (`NOT RED`). Each gate's output verbatim. Overlapping tasks run. Open points that blocked a case. Tools proposed. Then `/clio:memo <task>` records the work and ticks it, only on a passing gate.
