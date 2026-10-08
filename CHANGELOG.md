# Changelog

## 5.0.0 — 2026-10-08

Breaking: plans and test cases move from Markdown to `database/plan|test/<area>.jsonl`. `/clio:plan`
migrates a 4.x project on first run; approvals and runs carry over.

- Append-only stores written only by `clio add`; a task is done only through `clio test tick`.
- Open tasks are edited in place; only done work is history.
- Light tier for small, visible, easily undone work.
- Ingest shows what a change invalidates before writing it.
- New: `clio q plan|cases|spec-grep`, `clio test diff|migrate`, `chore` index records.
- `clio test withdraw`: take back done work that never left the working tree, with the user's yes.
- Index records carry `fp`, so a bare `/clio:memo` knows when nothing moved since the last one.
- A test command that runs no test is a fail, not a pass.
- `clio q summary` ends with `suggest:` lines (memo, test, plan, a question to answer), computed from the state.
- Skills are checked by a selftest: commands exist, allowed-tools cover them, no dead links.
- Fix bug.

## 4.2.0 — 2026-09-28

Python rewrite (3.9+, stdlib only). `run-task` runs a whole task in one call; `clio test red` gets red
from the base commit; batch runs start the runner once (8 cases: 72 s → 11 s); stricter gate. Tasks
with a `Not applicable` line need `approve` once more. Fix bug.

## 4.1.0 — 4.1.1 — 2026-09-25

Breaking: a case table must be approved before its gate can pass. Levels chosen by risk; flaky and red
bound to the code fingerprint; guard hook protects `runs.jsonl`.

## 4.0.0 — 2026-09-24

Breaking: layout moved under `.claude/clio/`; new `/clio:test`; `/clio:update` merged into
`/clio:ingest`; `req` is a string.

## 1.0.0 – 3.2.0 — 2026-09-08 to 2026-09-18

First plugin release, `/clio:plan`, drift nudge, one doc per sub-task keyed on `id`, ten skills cut to six.
