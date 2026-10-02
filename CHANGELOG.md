# Changelog

## 4.2.0 — 2026-09-28

Not breaking. Tasks with a `Not applicable` line need `approve` once more.

- **Python rewrite**: Python 3.9+, stdlib only, no `jq`. One entry point `bin/clio` (`test` / `q` /
  `validate` / `selftest`); hooks are `clio_guard.py` and `clio_nudge.py`.
- **`run-task <ids>`**: run a whole task in one call. Red is required only for `regression` cases and
  `critical` tasks.
- **`clio test red`**: gets the red from the base commit's code with today's tests, so no code is
  broken by hand. Behaviour always right → a passing `mutation` case or an approved `Red waived:` line.
- **`clio test history <case>`**: every recorded run of one case.
- **Batch runs**: a `Batch:` line in `.claude/rules/` starts the runner once and reads results from
  JUnit XML (Maven + Spring, 8 cases: 72 s → 11 s). Up to 5 tasks per batch, approved in one question.
- **Stricter gate**: `Not applicable` lines are part of the approved table; a mutation command must name
  its threshold; red counts only with tests unchanged and code changed; a red the runner never ran
  is not a red.
- Fixed: batch `red` recorded no command; memo nudge missed paths with spaces or accents; fingerprint
  missed a same-size edit after `git add`; JUnit parser misread vitest, gotestsum, `<skipped/>` and
  CDATA errors.

## 4.1.1 — 2026-09-25

Hot fix. Gate checks a mutation command's own threshold, and holds each level to every `LEVELS.md`
bullet id (`Covers` cell or `Not applicable`).

## 4.1.0 — 2026-09-25

Breaking: a case table must be approved before its gate can pass.

- Levels chosen by risk; new `idempotency` and `resilience`; `critical` no longer implies mutation.
- Gate: flaky and red bound to the code fingerprint; hashed case table; one case, one command.
- New guard hook: only the script writes `runs.jsonl`.

## 4.0.0 — 2026-09-24

Breaking: layout moved under `.claude/clio/`, `/clio:update` merged into `/clio:ingest`, `req` is a string.

- New `/clio:test` (seams → cases → gate); ingest proposes the stack; re-plan appends, never edits;
  memo ticks only on a passing gate.

## 3.x

- **3.2.0** (2026-09-18): ten skills → six; fixed drift nudge never loading.
- **3.1.0** (2026-09-17): `/clio:audit`; `/clio:plan` owns the stack.
- **3.0.0** (2026-09-17), breaking: one directory per feature, one doc per sub-task; `index.jsonl` keys on `id`.

## 2.x and earlier

- **2.1.0**: drift nudge hook. **2.0.0** (breaking): `index.jsonl` last-wins per field, `commits` array.
- **1.1.0**: `/clio:plan`. **1.0.0** (2026-09-08): first release as a Claude Code plugin.
