# Changelog

## 4.2.0 — 2026-09-28

Not breaking; existing evidence and approvals stay valid. Tasks with a `Not applicable` line need
`approve` once more.

- **Python rewrite.** All scripts are Python 3.9+, stdlib only; `jq` no longer needed. One entry
  point `bin/clio`: `clio test` / `clio q` / `clio validate` (were `clio-test.sh` / `q.sh` /
  `validate.sh`). Hooks: `hooks/clio_guard.py`, `hooks/clio_nudge.py`. No `.sh` ships; output and
  fingerprints unchanged. `bin/clio selftest` runs every selftest.
- **Run a task in one call** (`run-task <ids>`); red only for `regression` cases and `critical` tasks.
- **`clio test red <task> [--base <rev>]`**: runs those cases on the base commit's code with today's
  tests, in a worktree kept at `.git/clio-red` and reused (`--fresh` rebuilds it) — no breaking code
  by hand. When the behaviour was always right: a passing `mutation` case covers red, or an approved
  `Red waived:` line — accepted only after a `red` of that case passed on the base.
- **`clio test history <case>`**: every recorded run of one case.
- **Batch runs**: a `Batch:` line in `.claude/rules/` starts the runner once and reads each result
  from JUnit XML (Maven + Spring, 8 cases: 72 s → 11 s). `run-task` says why cases ran unbatched and
  how long it took.
- **Batches of tasks**: up to 5 ready tasks, approved in one question; each keeps its own hash.
- **Gate**: `Not applicable` lines are part of the approved table · mutation threshold must be a
  named flag · red counts only with tests unchanged and code changed · a `red` run is never today's
  last run · a red the runner never ran (base did not compile) is not a red.
- One Markdown-table parser for all scripts; `clio q summary` `next` respects `Needs`; runs capped
  by `CLIO_TIMEOUT` (default 600 s).
- Fixed: batch `red` recorded no command; the memo nudge missed recorded paths with a space or accent; fingerprint missed a same-size edit after `git add`;
  JUnit parser misread vitest, gotestsum, one-line `<skipped/>`, `<error>` in CDATA.

## 4.1.1 — 2026-09-25

Hot fix. Not breaking.

- Gate checks a mutation command's own threshold, not just its exit code.
- Gate holds each level to every LEVELS.md bullet id (`Covers` cell or `Not applicable`). Old case
  tables (no `Covers` column) unaffected.

## 4.1.0 — 2026-09-25

Breaking: a case table must be approved before its gate can pass.

- Levels chosen by risk (`LEVELS.md` § Choosing); new `idempotency`, `resilience`; `critical`
  narrowed, no longer implies mutation.
- Gate: flaky and red bound to the code fingerprint · approved, hashed case table · one case, one command.
- New guard hook: only the script writes `runs.jsonl`.

## 4.0.0 — 2026-09-24

Breaking. Layout moved, `/clio:update` merged into `/clio:ingest`, new `/clio:test`, `req` now strings.

- Everything under `.claude/clio/`; new `/clio:test` (seams → cases → gate); ingest proposes the
  stack; re-plan appends, never edits; memo ticks only on a passing gate.

## 3.2.0 — 2026-09-18

- Ten skills → six. Fixed: drift nudge never loaded.

## 3.1.0 — 2026-09-17

- New `/clio:audit` (drift between layers); `/clio:plan` owns the stack (`plans/infra.md`).

## 3.0.0 — 2026-09-17

Breaking: task docs per feature directory, `index.jsonl` keys on `id`.

- One directory per feature, one doc per sub-task; `id` = creation timestamp; `plan_tasks` joins docs to plans.

## 2.1.0 — 2026-09-14

- New drift nudge hook; setup writes only under `.claude/`.

## 2.0.1 — 2026-09-10

- Validator fixes.

## 2.0.0 — 2026-09-10

Breaking: `index.jsonl` last-wins per field; scalar `commit` → `commits` array.

## 1.1.0 — 2026-09-09

- New `/clio:plan <area>`; `clio:context` two depths.

## 1.0.0 – 1.0.2 — 2026-09-08

First release as a Claude Code plugin; skills renamed, setup tooling step.
