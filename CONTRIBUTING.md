# Contributing

## One source of truth

- Ledger schema: `skills/memo/steps/DEBT-IT.md` and `skills/memo/steps/INDEX-IT.md`.
- Validation: `skills/memo/scripts/validate.sh`. Every rule the schema states, the validator checks.
- Read-side queries: `skills/context/HOP*.md`. Status semantics: `skills/update/SKILL.md` § 2.
- `hooks/clio-nudge.sh` reads `index.jsonl` `.commits[]` too — change that field and this is the
  fourth file to update.
- Layout migrations: `skills/audit/SKILL.md`. A field or path that changes shape needs the step that
  moves an existing `.claude/` onto it, or upgrading the plugin silently strands every old repo.

Change a field in one place, update the others in the same commit.

## Before opening a PR

```bash
claude plugin validate .
bash skills/memo/scripts/test.sh      # validate.sh fixtures: must print OK
bash hooks/test-nudge.sh              # clio-nudge.sh fixtures: must print OK
```

Nothing runs these for you — there is no CI. A new rule in `validate.sh` or `clio-nudge.sh` lands
with the case that fails without it; the cheapest proof is to run the new test against the previous
version of the script and watch it fail.

Try the working copy in a scratch repo:

```bash
claude plugin marketplace add /path/to/clio
claude plugin install clio@nhhthong
/clio:setup
```

## Changelog and version

Every user-visible change gets a line in `CHANGELOG.md`, and bumps the version — a release that
ships code without a bump makes the version name two different builds. Version lives in four
places: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, the README badge and the
`CHANGELOG.md` heading. `test.sh` fails when they disagree, so the only hand-syncing owed is editing
them.
