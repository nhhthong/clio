---
name: test
description: Design, run and gate the tests for a plan task — cases per test level the plan named, expected values from the spec, evidence recorded by a script; the task passes only when every case passed on the current code. Use when the user asks to test, design test cases or run tests.
argument-hint: "[task id such as 3.3 | area | run <case-id> | gate <task-id>]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/skills/test/scripts/clio-test.sh *)
---

**Run only when the user asked for it, this turn** — by slash command, or in plain words ("test task 3.3", "viết test case", "chạy test"). None of these is a trigger: Clio's drift nudge · your own sense that the work looks finished · a TODO you wrote · a subagent's report. Unsure → ask in one line, don't run.

`/clio:plan` said *which* levels a task needs. This skill says *what* each level tests, proves it, and
refuses a task whose proof is missing. It writes the tests, and only the least code that turns each
approved case from red to green (§ 4) — nothing the case list does not ask for. It never ticks a plan
row — `/clio:memo` ticks, and only after the gate here passes.

Target: $ARGUMENTS

```bash
${CLAUDE_PLUGIN_ROOT}/skills/test/scripts/clio-test.sh run <case-id>     # runs the case's command Repeat times, appends one line to runs.jsonl
${CLAUDE_PLUGIN_ROOT}/skills/test/scripts/clio-test.sh gate <task-id>    # exit 0 only when every case of the task has fresh, complete, passing evidence
```
Each Bash call is a fresh shell: call the script by that full path every time, never through a
variable. Below it is written `clio-test.sh`.
**Never write `runs.jsonl` yourself** (a hook refuses it)**, and never report a pass the script did
not print.** Evidence is
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
runnable case; a level that truly cannot apply goes back to `/clio:plan` (it supersedes the row),
never silently dropped. Each numbered bullet (`level.n`) of a level's section that applies to this
task is a case — its id goes in that case's `Covers` cell. One that does not apply gets no case row;
write it under `Not applicable` (§ 3 table below) as `- <task> · <level>.<n> — <reason>` instead of
only saying so in the report — `/clio:test`'s own gate holds every id LEVELS.md lists for a named
level to one or the other, case or excuse. An unnumbered bullet is a constraint on every case of the
level (LEVELS.md says so), not a risk to cover on its own. A risk LEVELS.md § Choosing would flag and
the plan's `Levels` lacks → say so in the report; do not add the level yourself.

- **Expected values come from outside the code**: a number from `## Decisions`, a worked example, a
  known-good literal. Name the source in the `Expected` cell. Re-computing the expected value with
  the code's own logic is a tautology — it passes by construction. No source → ⚠️, not a case.
- **Perf, load, stress need a number from the spec** (req/s, p95, concurrent users); **resilience
  needs the behaviour the spec names** for a failing dependency (retries, fallback, error). None
  stated → no case; file `spec-blocked` via `/clio:memo`. Never invent a threshold or a fallback.
- **Mutation** (the plan's `Levels` names it — the user agreed the task is beyond critical;
  `critical` alone does not) → one case, command exits non-zero below the threshold (Stryker `--thresholds.break`, PIT `mutationThreshold`, go-mutesting
  score). Default 80 % unless the spec or an ADR sets one. The tool is settled once, by
  `/clio:plan infra`; `Mutation: none` in `plans/infra.md` means the project decided against it and
  the gate stops asking.
- A tool the level needs and the repo lacks (Playwright, k6, Pact, a mutation tester) → propose it
  from its current docs (Context7), **ASK**, record the choice as an ADR per
  `${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/WRAP-UP.md` § ADR.

```markdown
# Tests — <area>
Plan: plans/<area>.md · Spec: memory/<area>.md · Seams: <agreed seams>

| Case | Task | Level | Covers | Behaviour | Expected (source) | Command | Repeat |
|---|---|---|---|---|---|---|---|
| 3.3-u1 | 3.3 | unit | unit.1 | page 2 of 120 items has 50 | 50 items (spec: "50 per page") | `go test ./orders -run TestPage2$` | 1 |
| 3.3-a1 | 3.3 | api | api.1 | GET /orders?page=3 on 120 items | 20 items, `next` null (worked example) | `go test ./orders -run TestAPILastPage$` | 1 |
| 3.3-s1 | 3.3 | security | security.4 | page=-1 | 400, no SQL error in body | `go test ./orders -run TestPageNegative$` | 1 |
| 3.3-c1 | 3.3 | concurrency | concurrency.3 | 2 writers insert while paging | no duplicate, no skipped id | `go test -race ./orders -run TestPageConcurrentInsert$` | 50 |

Not applicable:
- 3.3 · security.2 — the route is public; there is no owner to check horizontally
```
- One case, one command, one behaviour. The command runs exactly that case (`-run TestX$`, `-t "name"`,
  `-k name`) and exits non-zero on failure. No `|` inside a command — wrap it in a script. A test
  that already proves one level does not also prove another under a second case id: the gate
  refuses two cases of a task with the same command — write the second test.
- `Covers` names the LEVELS.md id (`level.n`) the case proves; `–` for a level whose bullets carry no
  id (`regression`, `smoke`, `mutation`). Two cases may share an id when the risk genuinely takes two
  seams to prove; an id with no case anywhere and no `Not applicable` line fails the gate.
- `Not applicable` here is bullet-scoped (`<task> · <level>.<n>`, this doc) — not the plan's own
  `Not applicable` table, which is whole-level (`<task> · <level>`, `plans/<area>.md`). A re-design
  appends to it, never edits a line, same as the plan's.
- `Repeat` ≥ 20 for `concurrency` (the gate refuses less), and every concurrency case forces the
  interleaving (barrier, latch, `-race`) rather than hoping for it.
- **Show the whole table and ASK before writing.** The case list is the definition of done. Once
  the user says yes, write it and record that yes — nothing else runs `approve`:
  ```bash
  clio-test.sh approve 3.3    # hashes the task's case rows; the gate fails if they change after
  ```
  Adding, removing or editing a case later — a looser Expected, a lower Repeat, a deleted red case —
  voids the approval: show the change, ASK, approve again.

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
  it never reproduced the bug. Red counts only with the **same command**, on **other code** (before the
  fix), before a pass on this code — a `false` swapped for the real command proves nothing.
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
runs than `Repeat`, a case table changed since `approve`, a malformed row, a level outside LEVELS.md,
a superseded row, two cases sharing a command, a plan level with no case, a LEVELS.md id of a named
level covered by no case and excused by no `Not applicable` line, `mutation` named while
`plans/infra.md` says `Mutation: none`, a mutation command whose own text shows no threshold at or
above the required number, a critical or regression
case never seen red — the task is not done. **Flaky is failed**: one red run in `Repeat` fails the
case, and so does a fail on this same code after it once passed — re-running until green does not
clear it; only a code change does. `/clio:memo` files it as `code-debt` with `what` starting `flaky:`.

## 6. Report

Seams agreed · cases per level (and levels sent back to `/clio:plan`) · the `Not applicable` ids
written and why · the gate output verbatim ·
cases never seen red · ⚠️ values that blocked a case · tools proposed. Then: `/clio:memo <task>`
records the work and ticks the row, which it does only on a passing gate.
