---
name: test
description: >
  Design, write, run and gate the tests for plan tasks, in batches — cases per test level the plan named,
  expected values from the spec, approved in one question; one run per task, red only where it proves
  something (regression, critical), produced from the base commit instead of breaking code by hand.
  Before the first run on a stack it researches (Context7, web) and measures the fastest way to run many
  cases in one runner start, and records it as a `Batch:` line in `.claude/rules/`. The script records
  the evidence; a task passes only when every case passed on the current code. Use when the user asks
  to test, design test cases or run tests.
argument-hint: "[task id such as 3.3 | several ids | area | gate <task-id>]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test run *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test run-task *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test red *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test gate *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test history *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test coverage *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test fp)
---

**Run only when the user asked for it, this turn** — by slash command, or in plain words ("test task 3.3", "viết test case", "chạy test"). None of these is a trigger: Clio's drift nudge · your own sense that the work looks finished · a TODO you wrote · a subagent's report. Unsure → ask in one line, don't run.

`/clio:plan` said *which* levels a task needs. This skill says *what* each level tests, proves it, and
refuses a task whose proof is missing. It writes the tests, and only the least code that turns each
approved case pass (§ 4) — nothing the case list does not ask for. It never ticks a plan row —
`/clio:memo` ticks, and only after the gate here passes.

Target: $ARGUMENTS

```bash
${CLAUDE_PLUGIN_ROOT}/bin/clio test run-task <task-id>...          # every case of each task, Repeat times each, one runs.jsonl line per case
${CLAUDE_PLUGIN_ROOT}/bin/clio test red <task-id>... [--base <rev>]  # the cases that need red, on the base commit's code with today's tests (--fresh: rebuild its worktree)
${CLAUDE_PLUGIN_ROOT}/bin/clio test run <case-id>                    # one case on its own
${CLAUDE_PLUGIN_ROOT}/bin/clio test gate <task-id>                   # exit 0 only when every case of the task has fresh, complete, passing evidence
${CLAUDE_PLUGIN_ROOT}/bin/clio test history <case-id>                # every recorded run of one case, red runs marked
```
Each Bash call is a fresh shell: call the script by that full path every time, never through a
variable. Below it is written `clio test`. Run test cases **only through the script** — a command
from the case table run directly records nothing, and a pass the script did not record does not
exist. The repo's own build / typecheck command (from `.claude/rules/*.md`) you may run directly.
**Never write `runs.jsonl` yourself** (a hook refuses it)**, and never report a pass the script did
not print.** Evidence is
bound to a fingerprint of the working tree: edit any code after a pass and that pass stops counting.

## 1. Load — and pick the batch

Run the `clio:context` skill for the target. Read each task's plan row — `Levels` and `Touches` — the
spec's `## Decisions`, the code in `Touches`, and `.claude/rules/*.md` for the repo's real test
commands. Existing `.claude/clio/docs/tests/<area>.md` → read it; this is a re-design.

**One task, several ids, or an area.** An area → the batch is its open rows whose `Needs` are all
ticked (`clio q summary` names the first; read the plan for the rest), in plan order. Cap a batch at
**5 tasks or ~30 cases**, whichever comes first — past that the user skims, and a skimmed yes is not
an approval. The rest waits for the next batch; say which.

## 1b. The fastest way to run — found once per stack

Before the first run on a stack — a new case table, and just as much an existing one (a re-run, a
table written before 4.2.0) — look for a `Batch:` line in `.claude/rules/*.md` covering it. Found →
each case's `Command` is that template with `{tests}` replaced by its one test id, word for word.
None → read [BATCH.md](BATCH.md) and do what it says before running anything: one runner start for
many cases is the largest saving here (Maven + Spring, 8 cases: 72 s → 11 s). A `concurrency` case
repeats itself inside the test (`@RepeatedTest(20)`, `-count=20`) — BATCH.md § Repeat.

## 2. Seams

Write down the **seams** — the public boundaries the tests observe: a function's signature, a route,
a CLI command, a message on a queue, a page. They go on the tests doc's header line (`Seams:`) and are
shown **in the same question as the cases** (§ 3), not asked on their own. Tests go only through
agreed seams:
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
  score). Default 80 % unless the spec or an ADR sets one. The tool is settled once, the first time
  an area's `/clio:plan` agrees a task needs it (§ 3b); `Mutation: none` in `plans/infra.md` means the
  project decided against it and the gate stops asking.
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
  `-k name`) and exits non-zero on failure. This is the case's **identity**, not how it is run: with a
  `Batch:` line (§ 1b) the script starts the runner once for many such commands and still records
  one line per case. Never tell the user cases cannot be batched because of this rule. No `|` inside a command — wrap it in a script. A test
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
- **One question for the whole batch — seams, cases, `Not applicable` lines — and ASK before
  writing.** The case list is the definition of done. Lay it out so the risky part is read first:
  1. The seams.
  2. **Critical tasks first**, each under its own heading marked `critical`, with what must be seen
     red (§ 4).
  3. The other tasks, one table each.
  4. Levels you would send back to `/clio:plan`, and ⚠️ values that blocked a case.

  The user may accept all, or all but some ("ok, trừ 3.2: thêm case X"). Write what was accepted and
  record that yes, for exactly those tasks — nothing else runs `approve`. It is left out of this
  skill's `allowed-tools` on purpose: the permission prompt it raises is the user's own yes, not yours:
  ```bash
  clio test approve 3.1 3.3 3.4      # one record and hash per task; the gate fails a task whose rows change after
  ```
  A task sent back is redesigned and asked again on its own. Adding, removing or editing a case
  later — a looser Expected, a lower Repeat, a deleted red case, a new `Not applicable` line — voids
  that task's approval only: show the change, ASK, approve it again.

## 4. Write, run once — red only where it proves something

A test that never failed may pass by construction. For most cases the spec-sourced `Expected` and
the approved table already guard against that, so **only two kinds need to be seen red**, and the
gate asks for no other:
- every `regression` case — it must reproduce the bug;
- every case of a `critical` task, except `mutation` (its red is a score below threshold).

**Tasks with neither** (most of them): write the tests and the least code that makes them pass, run
the build, then one call — `clio test run-task 3.1 3.3 3.4` for the whole batch. With a `Batch:`
line (§ 1b) that is one runner start for every case of every task in it; the output marks each case
`— batch`. Failures → fix
the code (never loosen a test) and re-run the failing task. Refactor, re-run once.

**Tasks that need red** — a `regression` case, or a `critical` task: read [RED.md](RED.md) first.
In short: write the tests first; code that does not exist yet → a bare stub and `run-task`; code
that exists → `clio test red <task>` on the base commit, then `run-task`. A red counts only if it
failed on its assertion, and **never break code by hand to get a red**.

- Red must come from **the code, never the test**: the script fingerprints test files and code
  separately. Test files are recognised by path (`_test.`, `.test.`, `.spec.`, `test_*.py`, `tests/`,
  `spec/`, `src/test/`, `__tests__/`…); a test named otherwise counts as code — name it the usual way.
- Long levels (`load`, `stress`, `perf`, `mutation`, e2e with a UI, `concurrency` with a big
  `Repeat`): run them with a Bash timeout that covers them (up to 600000 ms) or `run_in_background`;
  each repeat is capped at `CLIO_TIMEOUT` seconds (default 600) — raise it for those
  (`CLIO_TIMEOUT=1800 clio test run-task …`). **Under a `Batch:` line this cap covers the whole
  runner start, not each case or repeat inside it** — a long case sharing a batch needs the batch's
  `CLIO_TIMEOUT` raised, not a budget of its own. Never start infra (docker, a staging target), use a
  secret or hit a paid or shared service on your own: say what is needed and ask.
- **One runner at a time per build.** Never start a test or build command while another one runs
  on the same module — Maven, Gradle, cargo and most bundlers share one output directory
  (`target/`, `build/`, `dist/`) and a second writer corrupts it (half-written class files, then
  failures that are not the code's). A long run in `run_in_background` means nothing else touches
  that build until it has finished; with a `Batch:` line the slow cases are in the same single run
  anyway, so there is nothing to put in the background. Create no new file while a run is going
  either: an untracked file that appears during a run is recorded as its artifact and left out of the
  fingerprint, so later edits to it would not void the pass.
- One case to re-run on its own (a flaky suspect) → `clio test run <case-id>`; what it did before →
  `clio test history <case-id>`.

## 5. Gate

```bash
clio test gate 3.1       # one call per task of the batch — it reads runs.jsonl, it runs no test
```
`OK` is the only pass. Anything else — never run, failed, code changed since, command changed, fewer
runs than `Repeat`, a case table changed since `approve` (a `Not applicable` line added or edited counts), a malformed row, a level outside LEVELS.md,
a superseded row, two cases sharing a command, a plan level with no case, a LEVELS.md id of a named
level covered by no case and excused by no `Not applicable` line, `mutation` named while
`plans/infra.md` says `Mutation: none`, a mutation command with no named threshold flag at or
above the required number (or a `#` in it), a critical or regression
case never seen red, a `Red waived:` line with no passing `red` behind it — the task is not done. **Flaky is failed**: one red run in `Repeat` fails the
case, and so does a fail on this same code after it once passed — re-running until green
does not clear it; only a code change does. `/clio:memo` files it as `code-debt` with `what` starting `flaky:`.
A stale incremental build can fake one: a file restored by git keeps its old mtime and the build
skips it, so the run tests yesterday's class. Before you call a case flaky, rebuild clean and look
at the failure; if it was the build, tell the user so — do not edit code just to clear the flag.

## 6. Report

Batch: tasks approved, sent back, left for the next batch · seams agreed · cases per level (and
levels sent back to `/clio:plan`) · the `Not applicable` ids
written and why · reds seen (and any `NOT RED`) · the gate output of each task, verbatim ·
⚠️ values that blocked a case · tools proposed. Then: `/clio:memo <task>`
records the work and ticks the row, which it does only on a passing gate.
