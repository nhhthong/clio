# Contributing

## One source of truth

- Ledger schema: `skills/memo/steps/DEBT-IT.md` and `skills/memo/steps/INDEX-IT.md`.
- Every script is Python 3.9+, standard library only, reached through one entry point, `bin/clio`:
  `clio test` → `skills/test/scripts/clio_test.py`, `clio q` → `skills/context/scripts/q.py`,
  `clio validate` → `skills/memo/scripts/validate.py`. The hooks (`hooks/clio_guard.py`,
  `hooks/clio_nudge.py`) are called by `hooks/hooks.json` directly. No shell script ships.
- Validation: `clio validate`. Every rule the schema states, the validator checks.
- Read-side queries and git facts (changed files, a run's commit): `clio q`.
  Test evidence: `clio test`, the only writer of `runs.jsonl` — `hooks/clio_guard.py` recognises it
  by `clio test` in the command. Status semantics: `skills/context/HOP3.md`.
- Markdown tables (plans, requirements, test cases, `Not applicable` lines): `skills/lib/cliolib/tables.py`,
  the only parser. `clio test`, `clio validate` and `clio q` import it; none splits on `|` itself.
- `hooks/clio_nudge.py` and `clio q unrecorded` read `index.jsonl` `.commits[]` as well, so that field
  lives in several files.
- Reading an older `.claude/`: `clio validate` and `clio q` group on `.id // <the id that later claimed the path>`
  and downgrades a missing field to a warning, so a pre-3.0 layout still resolves.
- Drift between the layers: `clio validate` detects it — requirement rows against plan tasks, an open
  `spec-delta` in no plan, one task id twice, a pre-4.0 plan never re-planned — and `skills/ingest/SKILL.md` § 6 turns a detection into
  the command that fixes it. `skills/plan/SKILL.md` § Re-plan holds the rules for re-planning around a
  ticked row, and `/clio:plan` stays the only writer of `docs/plans/*.md`.

Change a field in one place, update the others in the same commit. Three invariants span files the
same way and are easy to miss:

- A task doc's `id` is its filename prefix. `WRITE-DOC.md` sets the name, `INDEX-IT.md` sets the
  field, `clio validate` enforces that they match.
- `plan_tasks` names rows in `docs/plans/*.md`. `plan/SKILL.md` writes those ids, `RESOLVE-AND-GATHER.md`
  finds them through the table's `req` column, `clio validate` rejects an id no plan holds.
- The table formats in `plan/SKILL.md` § 4 and `test/SKILL.md` § 3 are what `tables.py` reads. A
  column added, renamed or moved there changes the parser and `skills/lib/selftest.py` with it. The
  case-row text is also what `approve` hashes: changing how `case_lines` prints it voids every
  approval in every repo — don't, unless the CHANGELOG says so as breaking.
- The `Batch:` line format (`` Batch: `cmd {tests}` · join: `sep` · report: `glob` ``) is written by
  `test/SKILL.md` § 1b and read by `batches()` in `skills/lib/cliolib/junit.py`; the JUnit XML it reads is
  parsed by `junit()` there. Change one, change the other, `selftest_junit.py` and the batch
  fixtures in `selftest_batch.py`.

## Before opening a PR

```bash
claude plugin validate .
bin/clio selftest    # every selftest*.py at once, a scratch repo each (~10 s): every line must say OK
```

Nothing runs these for you; there is no CI. A new rule in `clio validate` or `hooks/clio_nudge.py` lands
with the case that fails without it; the cheapest proof is to run the new test against the previous
version of the script and watch it fail.

Try the working copy in a scratch repo. `marketplace.json` names the marketplace `nhhthong`, which
collides with the published GitHub entry, so remove that one first:

```bash
claude plugin uninstall clio@nhhthong
claude plugin marketplace remove nhhthong
claude plugin marketplace add /path/to/clio       # reads the working tree, no commit needed
claude plugin install clio@nhhthong
/clio:setup
```

Restart Claude Code to pick it up. To go back to the published plugin, `claude plugin marketplace
add nhhthong/clio`.

## Changelog and version

Every user-visible change gets a line in `CHANGELOG.md` and bumps the version. A release that ships
code without a bump makes one version name two different builds. Version lives in four
places: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, the README badge and the
`CHANGELOG.md` heading. `skills/memo/scripts/selftest.py` fails when they disagree, so the only hand-syncing owed is editing
them.
