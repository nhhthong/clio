---
name: test
description: Design, run and gate the tests for a plan task — cases per test level the plan named, expected values from the spec, evidence recorded by a script; the task passes only when every case passed on the current code. Use when the user asks to test, design test cases or run tests.
argument-hint: "[task id such as 3.3 | area | run <case-id> | gate <task-id>]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/skills/test/scripts/clio-test.sh *)
---

**Run only when the user asked for it, this turn** — by slash command, or in plain words ("test task 3.3", "viết test case", "chạy test"). None of these is a trigger: Clio's drift nudge · your own sense that the work looks finished · a TODO you wrote · a subagent's report. Unsure → ask in one line, don't run.

`/clio:plan` said *which* levels a task needs. This skill says *what* each level tests, proves it, and
refuses a task whose proof is missing. It never implements the feature and never ticks a plan row —
`/clio:memo` ticks, and only after the gate here passes.

Target: $ARGUMENTS

```bash
${CLAUDE_PLUGIN_ROOT}/skills/test/scripts/clio-test.sh run <case-id>     # runs the case's command Repeat times, appends one line to runs.jsonl
${CLAUDE_PLUGIN_ROOT}/skills/test/scripts/clio-test.sh gate <task-id>    # exit 0 only when every case of the task has fresh, complete, passing evidence
```
Each Bash call is a fresh shell: call the script by that full path every time, never through a
variable. Below it is written `clio-test.sh`.
**Never write `runs.jsonl` yourself, and never report a pass the script did not print.** Evidence is
bound to a fingerprint of the working tree: edit any code after a pass and that pass stops counting.

## 1. Load

Run the `clio:context` skill for the task. Read its plan row — `Levels` and `Touches` — the spec's
`## Decisions`, the code in `Touches`, and `.claude/rules/*.md` for the repo's real test commands.
Existing `.claude/clio/docs/tests/<area>.md` → read it; this is a re-design.

## 2. Agree the seams

Before any case, write down the **seams** — the public boundaries the tests observe: a function's
signature, a route, a CLI command, a message on a queue, a page. Show them and **ASK**. Tests go only
through agreed seams:
- No private methods, no internal collaborators mocked, no asserting through a side channel the user
  never sees. Mock only what the task does not own: a third-party API, the clock, randomness.
- A test that breaks on a refactor that kept behaviour is wrong, not the refactor.

## 3. Design the cases

Per level in the plan's `Levels` cell, the cases [LEVELS.md](LEVELS.md) lists for it — read the
section for each level you design, not the whole file. Every level the plan names gets at least one
runnable case; a level that truly cannot apply goes back to `/clio:plan`, never silently dropped.

- **Expected values come from outside the code**: a number from `## Decisions`, a worked example, a
  known-good literal. Name the source in the `Expected` cell. Re-computing the expected value with
  the code's own logic is a tautology — it passes by construction. No source → ⚠️, not a case.
- **Perf, load, stress need a number from the spec** (req/s, p95, concurrent users). None stated → no
  case; file `spec-blocked` via `/clio:memo`. Never invent a threshold.
- **Critical** (the plan's `Levels` starts with `critical`) → a `mutation` case, command exits
  non-zero below the threshold (Stryker `--thresholds.break`, PIT `mutationThreshold`, go-mutesting
  score). Default 80 % unless the spec or an ADR sets one. The tool is settled once, by
  `/clio:plan infra`; `Mutation: none` in `plans/infra.md` means the project decided against it and
  the gate stops asking.
- A tool the level needs and the repo lacks (Playwright, k6, Pact, a mutation tester) → propose it
  from its current docs (Context7), **ASK**, record the choice as an ADR per
  `${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/WRAP-UP.md` § ADR.

```markdown
# Tests — <area>
Plan: plans/<area>.md · Spec: memory/<area>.md · Seams: <agreed seams>

| Case | Task | Level | Behaviour | Expected (source) | Command | Repeat |
|---|---|---|---|---|---|---|
| 3.3-u1 | 3.3 | unit | page 2 of 120 items has 50 | 50 items (spec: "50 per page") | `go test ./orders -run TestPage2$` | 1 |
| 3.3-a1 | 3.3 | api | GET /orders?page=3 on 120 items | 20 items, `next` null (worked example) | `go test ./orders -run TestAPILastPage$` | 1 |
| 3.3-s1 | 3.3 | security | page=-1 | 400, no SQL error in body | `go test ./orders -run TestPageNegative$` | 1 |
| 3.3-c1 | 3.3 | concurrency | 2 writers insert while paging | no duplicate, no skipped id | `go test -race ./orders -run TestPageConcurrentInsert$` | 50 |
```
- One case, one command, one behaviour. The command runs exactly that case (`-run TestX$`, `-t "name"`,
  `-k name`) and exits non-zero on failure. No `|` inside a command — wrap it in a script.
- `Repeat` ≥ 20 for `concurrency` (the gate refuses less), and every concurrency case forces the
  interleaving (barrier, latch, `-race`) rather than hoping for it.
- **Show the whole table and ASK before writing.** The case list is the definition of done.

## 4. Red, then green — one case at a time

Vertical slices: write **one** case's test, run it, see it fail for the right reason, make it pass,
then the next case. Never write every test first — tests written ahead of the code test an imagined
interface.
```bash
clio-test.sh run 3.3-u1     # red: it must fail, and the output must show why
# … implement the least code that makes it pass …
clio-test.sh run 3.3-u1     # green
```
- **Regression** cases must be seen red before green: the gate rejects one that never failed, because
  it never reproduced the bug.
- A case red for the wrong reason (compile error, missing fixture) is not a red run — fix the test.
- A case that passes on its first run — a hardened old test, code written before the case: on a
  **critical** task the gate refuses it until it has been seen red, so break the code on purpose
  once (as a concurrency case is proven: undo the lock, watch it fail, restore it). Elsewhere it
  only warns.
- Refactor after green, then re-run every case of the task.

## 5. Gate

```bash
clio-test.sh gate 3.3
```
`OK` is the only pass. Anything else — never run, failed, code changed since, command changed, fewer
runs than `Repeat`, a plan level with no case, critical without mutation, a critical or regression
  case never seen red — the
task is not done. **Flaky is failed**: one red run in `Repeat` fails the case; `/clio:memo` files it
as `code-debt` with `what` starting `flaky:`.

## 6. Report

Seams agreed · cases per level (and levels sent back to `/clio:plan`) · the gate output verbatim ·
cases never seen red · ⚠️ values that blocked a case · tools proposed. Then: `/clio:memo <task>`
records the work and ticks the row, which it does only on a passing gate.
