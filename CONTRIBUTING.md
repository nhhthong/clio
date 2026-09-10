# Contributing

## One source of truth

- Ledger schema: `skills/memo/steps/DEBT-IT.md` and `skills/memo/steps/INDEX-IT.md`.
- Validation: `skills/memo/scripts/validate.sh`. Every rule the schema states, the validator checks.
- Read-side queries: `skills/context/HOP*.md`. Status semantics: `skills/update/SKILL.md` § 2.

Change a field in one place, update the other two in the same commit.

## Before opening a PR

```bash
claude plugin validate .
bash skills/memo/scripts/test.sh      # validate.sh fixtures: must print OK
```

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

Every user-visible change gets a line in `CHANGELOG.md`. Version lives in three places:
`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, the README badge.
