# Contributing

## One source of truth

- Ledger schema: `skills/memo/steps/DEBT-IT.md` and `skills/memo/steps/INDEX-IT.md`.
- Validation: `skills/memo/scripts/validate.sh`. Every rule the schema states, the validator checks.
- Read-side queries: `skills/context/HOP*.md`. Status semantics: `skills/update/SKILL.md` § 2.
- `hooks/clio-nudge.sh` reads `index.jsonl` `.commits[]` as well, so that field lives in four files.
- Layout migrations: `skills/migrate/SKILL.md`. A field or path that changes shape needs the step that
  moves an existing `.claude/` onto it, or upgrading the plugin silently strands every old repo.
- Drift between the layers: `skills/audit/SKILL.md` reports it, `validate.sh` warns on the one case
  that is derivable, and `skills/plan/SKILL.md` § 3 holds the rules for re-planning around a ticked
  row. Audit never writes a plan; `/clio:plan` is the only writer of `docs/plans/*.md`.

Change a field in one place, update the others in the same commit. Two invariants span files the
same way and are easy to miss:

- A task doc's `id` is its filename prefix. `WRITE-DOC.md` sets the name, `INDEX-IT.md` sets the
  field, `validate.sh` enforces that they match, `audit/SKILL.md` assigns both when migrating.
- `plan_tasks` names rows in `docs/plans/*.md`. `plan/SKILL.md` writes those ids, `GATHER-FACTS.md`
  finds them through the table's `req` column, `validate.sh` rejects an id no plan holds.

## Before opening a PR

```bash
claude plugin validate .
bash skills/memo/scripts/test.sh      # validate.sh fixtures: must print OK
bash hooks/test-nudge.sh              # clio-nudge.sh fixtures: must print OK
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
