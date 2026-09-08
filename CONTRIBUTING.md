# Contributing to Clio

Thanks for helping. Two kinds of contribution matter most; both are small.

## 1. A stack rules file

`skills/clio-setup/rules/<stack>.md` is copied into a project when `scaffold.sh` detects that stack.
Wanted: TypeScript/Node, Python, Rust, Ruby, .NET, Swift/Kotlin mobile.

- 10–20 bullets, `paths:` frontmatter, a `<!-- Clio starter -->` comment like the existing files.
- Facts only: formatter command, test command, generated paths and their real source, the one or
  two footguns of that ecosystem (frozen migrations, lockfiles, `mounted` checks). No style opinions.
- Add the detection line to `scripts/scaffold.sh` (`Cargo.toml` → `rust`, `package.json` → `node`…).

## 2. A bug or behaviour fix in a skill

Skills are Markdown read by the model; "code" here is prose with a checkable endpoint.

- Every step must end in something verifiable (a file exists, a `jq` line returns X, a validator
  passes). Vague steps drift.
- One source of truth: the ledger schema lives in `skills/clio-memo/steps/DEBT-IT.md` and
  `INDEX-IT.md`; validation logic lives in `scripts/validate.sh`. Point at them, do not copy them.
- Keep the anti-guessing rule intact: a skill that fills a gap with a plausible answer instead of a
  ⚠️ is a regression, whatever else it improves.

## Running the tests

```bash
tests/selftest.sh          # must end with "fail 0"
```

Try the plugin locally before opening a PR:

```bash
claude plugin marketplace add /path/to/clio
claude plugin install clio@nhhthong
```

## Pull requests

- One change per PR. Rename-only PRs are welcome if they make a term clearer to a newcomer.
- Add a line to `CHANGELOG.md` under *Unreleased*.
- Bump `version` in `.claude-plugin/plugin.json` and `marketplace.json` only in a release PR.
