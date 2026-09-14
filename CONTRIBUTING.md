# Contributing

## One source of truth

- Ledger schema: `skills/memo/steps/DEBT-IT.md` and `skills/memo/steps/INDEX-IT.md`.
- Validation: `skills/memo/scripts/validate.sh`. Every rule the schema states, the validator checks.
- Read-side queries: `skills/context/HOP*.md`. Status semantics: `skills/update/SKILL.md` § 2.
- `hooks/clio-nudge.sh` reads `index.jsonl` `.commits[]` too — change that field and this is the
  fourth file to update.

Change a field in one place, update the others in the same commit.

## Before opening a PR

```bash
claude plugin validate .
bash skills/memo/scripts/test.sh      # validate.sh fixtures: must print OK
bash hooks/test-nudge.sh              # clio-nudge.sh fixtures: must print OK
```

Both tests, the manifests and the version check run on every push and PR
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)). A new rule in `validate.sh` or
`clio-nudge.sh` lands with the case that fails without it — the cheapest proof is to run the new
test against the previous version of the script and watch it fail.

Try the working copy in a scratch repo:

```bash
claude plugin marketplace add /path/to/clio
claude plugin install clio@nhhthong
/clio:setup
```

## Stack rule starters

`skills/setup/rules/<stack>.md`: 10–20 verified bullets, `paths:` frontmatter, a leading HTML
comment telling setup to verify every line. Add the stack's marker file to the `ls` line in
`skills/setup/SKILL.md` step 1.

## Changelog and version

Every user-visible change gets a line in `CHANGELOG.md`, and bumps the version — a release that
ships code without a bump makes the version name two different builds. Version lives in four
places: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, the README badge and the
`CHANGELOG.md` heading. CI fails when they disagree, so no hand-syncing is owed beyond editing
them.
