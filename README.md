<div align="center">
  <img src="resources/clio_avatar_512.png" alt="Clio, the Muse of History" width="220">

  # Clio

  **Project memory for Claude Code.**
  She keeps a record of what was decided, what was built, and what is still owed.

  [![Claude Code plugin](https://img.shields.io/badge/Claude_Code-plugin-D97757?logo=anthropic&logoColor=white)](https://code.claude.com/docs/en/plugins)
  [![Version](https://img.shields.io/badge/version-1.0.1-blue)](CHANGELOG.md)
  [![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
</div>

---

Clio keeps three small, append-only ledgers inside your repo. Claude Code reads them before it works
and writes to them after. A new session loads the context that matters in seconds, and when the
agent hits a gap it records the gap instead of filling it with a plausible guess.

The name comes from the Greek Muse of history, who carried a scroll and wrote down what happened.

## Why

Three things go wrong on any project an agent works on for more than a week.

1. **Context re-derivation.** Every session starts cold and rereads the codebase to rediscover what
   the last session already knew. That is slow, and it misses the decisions that never made it into
   code.
2. **Confident guesses.** Asked about a rule, a route, a column or a number, the agent answers with
   something that sounds right. An answer that is wrong per spec costs more than an incomplete one.
3. **Silent debt.** "I'll test that later", "the spec is unclear here", "this is a workaround". Said
   in one session, gone by the next.

Clio gives each of these a file the agent has to consult, plus one rule: a gap gets recorded as a
gap.

## How it works

Three questions, three homes, one join key (`req`, the requirement row number):

| Question | Home | Written by |
|---|---|---|
| Has it been **decided**? | `.claude/docs/specs/requirements.md`, status column | humans + `/clio-update` |
| What was **built**, and when? | `.claude/clio/index.jsonl` | `/clio-memo` |
| What is still **owed**? | `.claude/clio/debt.jsonl` | `/clio-memo`, `/clio-update` |

Both `.jsonl` files are append-only. A record is never edited. An update is a new line with the same
`id`, and readers take the last line. You get history for free, concurrent sessions cannot clobber
each other, and `git log` recovers anything you narrowed away.

```
  new task ──► clio-context (auto): spec that governs it → what was built → what is owed
      │                              ⚠️ row with no record?  stop and ask, don't guess
      ▼
  work …
      │
      ▼
  /clio-memo ──► task doc · index.jsonl line · debt.jsonl lines · validate
```

There is no hook. A developer has to remember one command, `/clio-memo`, when a piece of work is
done. Skip it and the next session starts without that work in its memory.

## Install

You need Claude Code with plugin support, plus `bash`, `jq`, `git` and `awk` (on macOS also
`brew install gnu-sed`).

```bash
claude plugin marketplace add nhhthong/clio
claude plugin install clio@nhhthong
```

Or inside a session: `/plugin install clio@nhhthong`. Update later with `claude plugin update clio`;
your ledgers and docs are data in your repo, and an update never touches them.

To have a whole team pick it up when they trust the repo, add this to the project's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "nhhthong": { "source": { "source": "github", "repo": "nhhthong/clio" } }
  },
  "enabledPlugins": { "clio@nhhthong": true }
}
```

## Quick start

```
/clio-setup
```

Run it once per repository. It scaffolds `.claude/`, then asks a handful of questions (domain
vocabulary, formatter, timezone, generated files, the things that are expensive to get wrong) and
writes your answers into `CLAUDE.md` and `CONTEXT.md`. It also lists the MCP servers and plugins you
are missing (Context7, a code graph, review plugins, Playwright or a DB server where the stack calls
for it, and an optional strict permission list) and installs only what you pick.

Have a requirements document, contract or PRD?

```
/clio-ingest docs/requirements.pdf
```

That distils it into one short `memory/<area>.md` per domain plus a row table, and marks every
undecided point ⚠️ with the name of whoever owes the answer.

## Commands

| Command | Does | Run when |
|---|---|---|
| `/clio-setup` | scaffold `.claude/`, fill CLAUDE.md / CONTEXT.md by asking you, offer tooling | once per repo |
| `/clio-ingest <doc>` | turn a requirement document into `docs/specs/memory/*.md` + `requirements.md` | once, and when a new source arrives |
| `clio-context` | before coding: the governing spec, what was built, what is owed (read-only) | Claude triggers it |
| `/clio-memo [doc]` | record finished work: task doc, `index.jsonl`, `debt.jsonl`, CONTEXT.md diff, ADR | after each feature or fix |
| `/clio-update [spec]` | a spec changed: what it invalidates, whether it is safe to build yet, move the row marker | when requirements change |
| `/clio-debt [filter]` | what is still owed, actionable vs. blocked (read-only) | any time |
| `/clio-ask [x]` | explain any of the above | when unsure |

Each skill is a short `SKILL.md`; `clio-memo` and `clio-context` walk numbered step files, so only
the step being executed is in context. Every step ends in something you can check.

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

The skills and the validator stay in the plugin. Nothing outside `.claude/` is touched, and the
plugin does nothing at all in a project without `.claude/clio/`, so you can leave it enabled
everywhere.

## Design rules

- The agent does not speculate. Anything it has not verified by reading, grepping, querying or
  running is reported as unverified, and it asks. When several readings of a requirement are valid,
  it presents them all instead of picking one.
- ✅ means decided, never built. Build state lives in the ledgers and decision state in the spec
  register. Mixing the two is how "done" gets claimed twice.
- Ledger lines are never edited, reordered or deleted. An update is a new line.
- One feature gets one doc, for good. Continuing a feature updates its doc; it never creates a second.
- `blocked_by` decides whether work may start; `status` only says how far it got. A debt record with
  `blocked_by: null` is the work queue. Anything else waits.
- Every ⚠️ has a record. An open point in the spec without a `debt.jsonl` line naming who owes the
  answer is itself a finding.
- Work that ran no test, build or recorded manual check is filed as `unverified`, not passed off as
  built.

## FAQ

**Does it work without a requirements document?**
Yes. `/clio-setup` offers Lite mode: no spec register, every record uses `req: []` and joins on
domain, keywords and files. You still get the task docs and the debt ledger.

**Why JSONL instead of a database?**
Appending one line with `>>` is atomic, diffs are readable, `jq` is the whole query language, and
`git log` is the audit trail.

**Why not one big `CLAUDE.md`?**
`CLAUDE.md` loads every session, so everything in it is paid for on every task. Clio keeps that file
under about 150 lines and moves history into files that load only when a query says they are
relevant.

**Which stacks have rule starters?**
PHP, Go, Java/Kotlin, Dart/Flutter. Others are one small file: 10 to 20 verified bullets in
`skills/clio-setup/rules/<stack>.md` with `paths:` frontmatter, plus the marker file added to the
`ls` line in `skills/clio-setup/SKILL.md` step 1.

**Is this only for Claude Code?**
Yes. The skills are plain Markdown, but the `${CLAUDE_PLUGIN_ROOT}` paths and the install flow
belong to Claude Code.

## Contributing

Stack rule files and skill fixes help most, and both are small. Keep one source of truth: the
ledger schema lives in `skills/clio-memo/steps/DEBT-IT.md` and `INDEX-IT.md`, validation in
`skills/clio-memo/scripts/validate.sh`. Point at them, do not copy them. A skill that fills a gap
with a plausible answer instead of a ⚠️ is a regression, whatever else it improves. Before a PR,
`claude plugin validate .` must pass; to try a working copy, `claude plugin marketplace add
/path/to/clio` then `claude plugin install clio@nhhthong`.

## License

[MIT](LICENSE) © 2026 nhhthong
