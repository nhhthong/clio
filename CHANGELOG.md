# Changelog

## 4.1.2 — 2026-09-28

Not breaking. Tasks with a `Not applicable` line need `approve` once more.

- `/clio:test` runs a whole task in one call (`run-task <ids>`), not case by case. No red phase
  unless it proves something: `regression` cases and `critical` tasks only.
- New `clio-test.sh red <task> [--base <rev>]`: runs those cases on the base commit's code with
  today's tests, in a throwaway worktree — red without breaking code by hand. The gate no longer
  warns about other cases never seen red.
- Batch run: a `Batch:` line in `.claude/rules/` (`/clio:test` § 1b researches it with Context7 and
  measures it once per stack) lets `run-task`/`red` start the runner once for every case and read
  each result from the JUnit XML (full classnames; parameter sets are not repetitions). Maven +
  Spring, 8 cases: 72 s → 11 s; with red: 113 s → 22 s.
- Batches: an area → up to 5 ready tasks, seams + cases approved in one question, critical first.
  `approve`/`run-task` take several ids; each task keeps its own hash.
- Gate: `Not applicable` lines (read only from the `Not applicable:` list) are part of the approved
  table · mutation threshold must be a named flag, no `#` · red counts only with tests unchanged
  and code changed (`tfp`/`cfp`).
- New `skills/lib/tables.sh`: one Markdown-table parser for `clio-test.sh`, `validate.sh`, `q.sh`;
  columns found by header name; `validate.sh` now skips tables inside `<!-- -->`, like the gate.
- `q.sh summary`: `next` respects `Needs`.
- `run` and batch runs capped by `CLIO_TIMEOUT` (default 600 s), via `timeout` or `gtimeout`.
- Fixed: fingerprint missed a same-size edit right after `git add`, and ignored edits to a file
  once recorded as a test artifact and later tracked.

## 4.1.1 — 2026-09-25

Hot fix. Not breaking.

- Gate checks a mutation command's own threshold, not just its exit code.
- Gate holds each level to every LEVELS.md bullet id (`Covers` cell or `Not applicable`). Old case
  tables (no `Covers` column) unaffected.

## 4.1.0 — 2026-09-25

Breaking: every task needs `clio-test.sh approve <task>` once before its gate can pass again.

- Levels chosen by risk: `LEVELS.md` § Choosing, 13 questions.
- New levels `idempotency`, `resilience`; transaction/isolation folded into `integration`/`concurrency`.
- `critical` narrowed to money/auth/deletes/corrupting races; no longer implies mutation.
- Mutation asked only for tasks beyond critical (4-question test); user decides.
- `Not applicable` list under a plan table.
- Gate: flaky bound to the code fingerprint · red bound to command+code · approved case table
  (hashed) · strict row parsing · one case, one command.
- New `hooks/clio-guard.sh`: blocks writes to `runs.jsonl` outside `clio-test.sh`.
- Fixed: a staged-then-edited ledger under `.claude/` could move the fingerprint; empty-cell
  column shift; locale-dependent `comm` sort.

## 4.0.0 — 2026-09-24

Breaking. Layout moved, `/clio:update` merged into `/clio:ingest`, new `/clio:test`, `req` now strings.

Migrate 3.x by hand — `/clio:setup` stops on old layout:
```bash
mkdir -p .claude/clio/database
git mv .claude/clio/index.jsonl .claude/clio/debt.jsonl .claude/clio/database/
git mv .claude/docs .claude/clio/docs
mkdir -p .claude/clio/docs/tests && touch .claude/clio/database/runs.jsonl
```
Then: restate `index.jsonl`/`debt.jsonl` records with new paths · move `Domains` line to
`requirements.md`, run `q.sh spec-mark` once · `.gitattributes` → `.claude/clio/.gitattributes` ·
old numeric `req` still resolves.

- Layout: everything under `.claude/clio/` (`docs/`, `database/`).
- New `/clio:test`: seams → cases → red/green, gated by `clio-test.sh`.
- Ingest proposes stack (`memory/infra.md` row 0, ADR); absorbs old `/clio:update`.
- Plan never picks stack; re-plan appends, never edits.
- Memo ticks only on passing gate.
- `req` = strings. Scripts called by full path from `SKILL.md`.

## 3.2.0 — 2026-09-18

- README 255 → 180 lines.
- Fixed: drift nudge never loaded (duplicate hook registration).
- Ten skills → six; `/clio:memo` five steps.
- `validate.sh` joins `requirements.md` to plan tables; `/clio:update --fix` re-plans.

## 3.1.0 — 2026-09-17

- New `/clio:audit` (drift between layers); old `audit` → `/clio:migrate`.
- Doc sections invalidated by a closed `spec-delta` marked superseded.
- `/clio:plan` owns stack; new `docs/plans/infra.md`.

## 3.0.0 — 2026-09-17

Breaking: task docs per feature directory, `index.jsonl` keys on `id`.

- One directory per feature, one doc per sub-task; `id` = creation timestamp, never changes.
- `plan_tasks` joins doc to plan rows.
- `validate.sh`: `plan_tasks`, dead links, orphan check.

## 2.1.0 — 2026-09-14

- New drift nudge (`UserPromptSubmit` hook, once per session).
- Setup writes only under `.claude/`.

## 2.0.1 — 2026-09-10

- `validate.sh` fixes: `commits` must be array, malformed-line resilience, precise pre-2.0 warning.

## 2.0.0 — 2026-09-10

Breaking: `index.jsonl` last-wins per field; scalar `commit` → `commits` array. Migrate (keeps backup):
```bash
cp .claude/clio/index.jsonl .claude/clio/index.jsonl.pre2
jq -s -c 'group_by(.doc)[] | last + {files:(map(.files[]?)|unique), keywords:(map(.keywords[]?)|unique),
  commits:([.[] | .commit, .commits[]?] | map(values) | unique)} | del(.commit)' \
  .claude/clio/index.jsonl.pre2 > .claude/clio/index.jsonl
```

## 1.1.0 — 2026-09-09

- New `/clio:plan <area>`; `clio:context` two depths.

## 1.0.2 — 2026-09-08

- Skills renamed (`/clio:memo`, …).

## 1.0.1 — 2026-09-08

- Setup tooling step.

## 1.0.0 — 2026-09-08

First release as Claude Code plugin.
