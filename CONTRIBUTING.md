# Contributing

## One source of truth

- Ledger schema: `skills/memo/steps/DEBT-IT.md` and `skills/memo/steps/INDEX-IT.md`.
- Validation: `skills/memo/scripts/validate.sh`. Every rule the schema states, the validator checks.
- Read-side queries and git facts (changed files, a run's commit): `skills/context/scripts/q.sh`.
  Test evidence: `skills/test/scripts/clio-test.sh`, the only writer of `runs.jsonl`. Status
  semantics: `skills/context/HOP3.md`.
- Markdown tables (plans, requirements, test cases, `Not applicable` lines): `skills/lib/tables.sh`,
  the only parser. `clio-test.sh`, `validate.sh` and `q.sh` source it; none splits on `|` itself.
- `hooks/clio-nudge.sh` and `q.sh unrecorded` read `index.jsonl` `.commits[]` as well, so that field
  lives in several files.
- Reading an older `.claude/`: `validate.sh` and `q.sh` group on `.id // <the id that later claimed the path>`
  and downgrades a missing field to a warning, so a pre-3.0 layout still resolves. A change that
  breaks that has to say so in `CHANGELOG.md` with the steps to move a repo across by hand.
- Drift between the layers: `validate.sh` detects it — requirement rows against plan tasks, an open
  `spec-delta` in no plan, one task id twice, a pre-4.0 plan never re-planned — and `skills/ingest/SKILL.md` § 6 turns a detection into
  the command that fixes it. `skills/plan/SKILL.md` § Re-plan holds the rules for re-planning around a
  ticked row, and `/clio:plan` stays the only writer of `docs/plans/*.md`.

Change a field in one place, update the others in the same commit. Three invariants span files the
same way and are easy to miss:

- A task doc's `id` is its filename prefix. `WRITE-DOC.md` sets the name, `INDEX-IT.md` sets the
  field, `validate.sh` enforces that they match.
- `plan_tasks` names rows in `docs/plans/*.md`. `plan/SKILL.md` writes those ids, `RESOLVE-AND-GATHER.md`
  finds them through the table's `req` column, `validate.sh` rejects an id no plan holds.
- The table formats in `plan/SKILL.md` § 4 and `test/SKILL.md` § 3 are what `tables.sh` reads. A
  column added, renamed or moved there changes the parser and `skills/lib/selftest.sh` with it. The
  case-row text is also what `approve` hashes: changing how `case_lines` prints it voids every
  approval in every repo — don't, unless the CHANGELOG says so as breaking.
- The `Batch:` line format (`` Batch: `cmd {tests}` · join: `sep` · report: `glob` ``) is written by
  `test/SKILL.md` § 1b and read by `batches()` in `skills/lib/junit.sh`; the JUnit XML it reads is
  parsed by `junit()` there. Change one, change the other, `selftest-junit.sh` and the batch
  fixtures in `selftest-batch.sh`.

## Before opening a PR

```bash
claude plugin validate .
bash skills/memo/scripts/test.sh      # validate.sh fixtures: must print OK
bash hooks/test-nudge.sh              # clio-nudge.sh fixtures: must print OK
bash hooks/test-guard.sh              # clio-guard.sh fixtures: must print OK
bash skills/test/scripts/selftest.sh  # clio-test.sh: selftest-gate/-red/-batch.sh, a repo each (~40 s): must print OK
bash skills/context/scripts/selftest.sh  # q.sh query fixtures: must print OK
bash skills/lib/selftest.sh           # tables.sh parser, golden output: must print OK
bash skills/lib/selftest-junit.sh     # junit.sh: real runners' report shapes, batch templates: must print OK
bash skills/lib/selftest-fingerprint.sh  # fingerprint.sh: what moves the fp, test/code split: must print OK
```

Nothing runs these for you; there is no CI. A new rule in `validate.sh` or `clio-nudge.sh` lands
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
`CHANGELOG.md` heading. `test.sh` fails when they disagree, so the only hand-syncing owed is editing
them.
