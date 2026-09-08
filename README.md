<div align="center">
  <img src="resources/clio_avatar_512.png" alt="Clio, the Muse of History" width="220">

  # Clio

  **Project memory for Claude Code.**
  She keeps a record of what was decided, what was built, and what is still owed.

  [![Claude Code plugin](https://img.shields.io/badge/Claude_Code-plugin-D97757?logo=anthropic&logoColor=white)](https://code.claude.com/docs/en/plugins)
  [![Version](https://img.shields.io/badge/version-1.0.2-blue)](CHANGELOG.md)
  [![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
</div>

---

Clio keeps three small, append-only ledgers inside your repo. Claude Code reads them before it works
and writes to them after, and when it hits a gap it records the gap instead of guessing. Named after
the Greek Muse of history, daughter of Memory, who wrote down what happened and left the line blank
when nobody told her.

## How it works

| Question | Home | Written by |
|---|---|---|
| Has it been **decided**? | `.claude/docs/specs/requirements.md`, status column | humans + `/clio:update` |
| What was **built**, and when? | `.claude/clio/index.jsonl` | `/clio:memo` |
| What is still **owed**? | `.claude/clio/debt.jsonl` | `/clio:memo`, `/clio:update` |

The three join on `req`, the requirement row number. Both `.jsonl` files are append-only: an update
is a new line with the same `id`, and readers take the last line.

```
  new task ──► clio:context (auto): spec that governs it → what was built → what is owed
      │                              open row with no record? stop and ask, don't guess
      ▼
  work …
      │
      ▼
  /clio:memo ──► task doc · index.jsonl line · debt.jsonl lines · validate
```

There is no hook. Run `/clio:memo` when a piece of work is done; skip it and the next session starts
without that work in its memory.

## Install

Requires `bash`, `jq`, `git`, `awk` (macOS: also `brew install gnu-sed`).

```bash
claude plugin marketplace add nhhthong/clio
claude plugin install clio@nhhthong
```

Update with `claude plugin update clio`; your ledgers and docs are never touched. To have a team pick
it up when they trust the repo, add to the project's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": { "nhhthong": { "source": { "source": "github", "repo": "nhhthong/clio" } } },
  "enabledPlugins": { "clio@nhhthong": true }
}
```

## Quick start

```
/clio:setup
```

Once per repository. Scaffolds `.claude/`, asks about domain vocabulary, formatter, timezone,
generated files and the things that are expensive to get wrong, writes the answers into `CLAUDE.md`
and `CONTEXT.md`, then offers missing MCP servers and plugins and installs only what you pick.

```
/clio:ingest docs/requirements.pdf
```

If you have a requirements document: distils it into one `memory/<area>.md` per domain plus a row
table, marking every undecided point as open with the name of whoever owes the answer.

## Commands

| Command | Does | Run when |
|---|---|---|
| `/clio:setup` | scaffold `.claude/`, fill CLAUDE.md / CONTEXT.md by asking, offer tooling | once per repo |
| `/clio:ingest <doc>` | requirement document → `docs/specs/memory/*.md` + `requirements.md` | once, and when a new source arrives |
| `clio:context` | before coding: governing spec, what was built, what is owed (read-only) | Claude triggers it |
| `/clio:memo [doc]` | record finished work: task doc, `index.jsonl`, `debt.jsonl`, CONTEXT.md diff, ADR | after each feature or fix |
| `/clio:update [spec]` | a spec changed: what it invalidates, safe to build yet, move the row marker | when requirements change |
| `/clio:debt [filter]` | what is still owed, actionable vs. blocked (read-only) | any time |
| `/clio:ask [x]` | explain any of the above | when unsure |

## What lands in your repo

```
.claude/
├── CLAUDE.md                 # rules + @CONTEXT.md import; domain vocabulary
├── CONTEXT.md                # stable facts: entities, term collisions, key flows, landmines
├── rules/<stack>.md          # path-scoped stack rules, only for stacks the repo has
├── clio/
│   ├── index.jsonl           # what was built, append-only
│   └── debt.jsonl            # what is owed, append-only
└── docs/
    ├── specs/requirements.md # decision register: row → spec file → ✅ ⚠️ ❌
    ├── specs/memory/*.md     # distilled per-domain decisions, each quoting its source verbatim
    ├── tasks/*.md            # one doc per feature, forever (update, never fork)
    └── decisions/*.md        # ADRs
```

Skills and the validator stay in the plugin. Nothing outside `.claude/` is touched; in a project
without `.claude/clio/` the skills say so and stop.

## Rules the skills enforce

- Not verified by reading, grepping, querying or running → reported as unverified, and the agent asks.
- Decided means decided, never built. Build state lives in the ledgers, decisions in the spec register.
- Ledger lines are never edited, reordered or deleted. One feature, one doc, forever.
- `blocked_by: null` is the work queue; anything else waits. Every open spec point has a debt record.

Stack rule starters: PHP, Go, Java/Kotlin, Dart/Flutter. Others: 10 to 20 verified bullets in
`skills/setup/rules/<stack>.md` with `paths:` frontmatter, plus its marker file on the `ls` line in
`skills/setup/SKILL.md` step 1.

## Contributing

Keep one source of truth: ledger schema in `skills/memo/steps/DEBT-IT.md` and `INDEX-IT.md`,
validation in `skills/memo/scripts/validate.sh`. `claude plugin validate .` must pass. Try a working
copy with `claude plugin marketplace add /path/to/clio`, then `claude plugin install clio@nhhthong`.

## License

[MIT](LICENSE) © 2026 nhhthong
