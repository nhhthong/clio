# Changelog

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
