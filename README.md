<div align="center">
  <img src="resources/clio_avatar_512.png" alt="Clio, the Muse of History" width="220">

  # Clio

  **Project memory for Claude Code.**
  She writes down what happened, not what sounds right.

  [![Claude Code plugin](https://img.shields.io/badge/Claude_Code-plugin-D97757?logo=anthropic&logoColor=white)](https://code.claude.com/docs/en/plugins)
  [![Version](https://img.shields.io/badge/version-1.0.0-blue)](CHANGELOG.md)
  [![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
  [![Tests](https://img.shields.io/badge/selftest-52_passing-brightgreen)](tests/selftest.sh)
</div>

---

Clio keeps three small, append-only ledgers inside your repo and teaches Claude Code to read them
before it works and write to them after. The result: a new session loads the context that matters
in seconds, and the agent stops filling gaps with plausible guesses.

Named after the Greek Muse of history, who carried a scroll and recorded only what actually happened.

## Table of contents

- [Why](#why)
- [How it works](#how-it-works)
- [Install](#install)
- [Quick start](#quick-start)
- [Commands](#commands)
- [What lands in your repo](#what-lands-in-your-repo)
- [Hooks](#hooks)
- [Design rules](#design-rules)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)

## Why

Three things go wrong on any project an agent works on for more than a week:

1. **Context re-derivation.** Every session starts cold and rereads the codebase to rediscover what
   the last session already knew. Expensive, slow, and it misses the decisions that never made it
   into code.
2. **Hallucinated certainty.** Asked about a rule, a route, a column, a number, the agent answers
   with something that *sounds* right. Wrong-per-spec is worse than incomplete.
3. **Silent debt.** "I'll test that later", "the spec is unclear here", "this is a workaround" —
   said in a session, gone by the next one.

Clio answers each with a file the agent must consult, and a rule that a gap is recorded as a gap,
never papered over.

## How it works

Three questions, three homes, one join key (`req`, the requirement row number):

| Question | Home | Written by |
|---|---|---|
| Has it been **decided**? | `.claude/docs/specs/requirements.md` — status column | humans + `/clio-update` |
| What was **built**, and when? | `.claude/clio/index.jsonl` | `/clio-memo` |
| What is still **owed**? | `.claude/clio/debt.jsonl` | `/clio-memo`, `/clio-update` |

Both `.jsonl` files are **append-only**. A record is never edited; an update is a new line with the
same `id`, and readers take the last line. History is free, concurrent sessions cannot clobber each
other, and `git log` recovers anything.

The loop runs itself:

```
session start ──► hook: open debt + "CONTEXT.md is falling behind"
      │
      ▼
  new task ──► clio-context (auto): spec that governs it → what was built → what is owed
      │                              ⚠️ row with no record?  stop and ask, don't guess
      ▼
  work …
      │
      ▼
  /clio-memo ──► task doc · index.jsonl line · debt.jsonl lines · validate
      │
      ▼
session stop ──► hook: "3 files changed, nothing recorded — memo it, or say why not"
```

A developer has to remember one command: `/clio-memo` when a piece of work is done.

## Install

Requires Claude Code with plugin support, plus `bash`, `jq`, `git`, `awk` (macOS: `brew install gnu-sed`).

```bash
claude plugin marketplace add nhhthong/clio
claude plugin install clio@nhhthong
```

Or inside a session: `/plugin install clio@nhhthong`.

To make a whole team pick it up when they trust the repo, add to the project's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "nhhthong": { "source": { "source": "github", "repo": "nhhthong/clio" } }
  },
  "enabledPlugins": { "clio@nhhthong": true }
}
```

Update later with `claude plugin update clio`. Your ledgers and docs are data in your repo; updates
never touch them.

## Quick start

```
/clio-setup
```

Runs once per repository. Scaffolds `.claude/`, then asks a handful of questions (domain vocabulary,
formatter, timezone, generated files, the things that are expensive to get wrong) and writes the
answers into `CLAUDE.md` and `CONTEXT.md`. It never guesses an answer you did not give.

Have a requirements document, contract or PRD?

```
/clio-ingest docs/requirements.pdf
```

Distils it into one short `memory/<area>.md` per domain plus a row table, marking every undecided
point ⚠️ with the name of whoever owes the answer. From now on, `clio-context` fires on its own
before non-trivial work, and the Stop hook nudges you when work goes unrecorded.

## Commands

| Command | Does | Run when |
|---|---|---|
| `/clio-setup` | scaffold `.claude/` and fill CLAUDE.md / CONTEXT.md by asking you | once per repo |
| `/clio-ingest <doc>` | turn a requirement document into `docs/specs/memory/*.md` + `requirements.md` | once, and when a new source arrives |
| `clio-context` | before coding: the governing spec, what was built, what is owed — read-only | Claude triggers it |
| `/clio-memo [doc]` | record finished work: task doc, `index.jsonl`, `debt.jsonl`, CONTEXT.md diff, ADR | after each feature / fix |
| `/clio-update [spec]` | a spec changed: what it invalidates, is it safe to build yet, move the row marker | when requirements change |
| `/clio-debt [filter]` | what is still owed, actionable vs. blocked — read-only | any time |
| `/clio-ask [x]` | explain any of the above | when unsure |

Each skill is a short `SKILL.md` that walks numbered step files, so only the step being executed is
in context. Every step ends in something checkable — a file exists, a validator passes.

## What lands in your repo

```
.claude/
├── CLAUDE.md                 # rules + @CONTEXT.md import; domain vocabulary
├── CONTEXT.md                # stable facts: entities, term collisions, key flows, landmines
├── rules/<stack>.md          # path-scoped stack rules, only for stacks the repo has
├── clio/
│   ├── index.jsonl           # what was built — append-only
│   └── debt.jsonl            # what is owed — append-only
└── docs/
    ├── specs/requirements.md # decision register: row → spec file → ✅ ⚠️ ❌
    ├── specs/memory/*.md     # distilled per-domain decisions, each quoting its source verbatim
    ├── tasks/*.md            # one doc per feature, forever (update, never fork)
    └── decisions/*.md        # ADRs
```

Everything else — skills, hooks, the validator — stays in the plugin. Nothing outside `.claude/` is
touched.

## Hooks

| Event | Hook | Behaviour |
|---|---|---|
| `SessionStart` | `session-debt` | prints open, actionable debt (newest first, max 5) and warns when `CONTEXT.md` is older than five recorded runs |
| `Stop` | `memo-reminder` | if tracked files changed after the ledger was last written, blocks **once** with "run `/clio-memo`, or say in one line why this needs no record" |

Both exit silently in any project without `.claude/clio/`, so the plugin is safe to leave enabled
everywhere.

## Design rules

These are the rules the skills enforce. They are the point.

- **No speculation.** Not verified by reading, grepping, querying or running → say "unverified" and
  ask. Multiple valid interpretations → present them, never pick one silently.
- **✅ means decided, never built.** Build state lives in the ledgers, decision state in the spec
  register. Mixing them is how "done" gets claimed twice.
- **Append only.** Ledger lines are never edited, reordered or deleted. Updates are new lines.
- **One feature, one doc, forever.** Continuing a feature updates its doc; it never creates a second.
- **`blocked_by` decides, not `status`.** A debt record with `blocked_by: null` is the work queue;
  anything else must not be started, whatever its status says.
- **Every ⚠️ has a record.** An open point in the spec without a `debt.jsonl` line naming who owes
  the answer is itself a finding.
- **Verification is not optional.** Work that ran no test, build or recorded manual check is filed
  as `unverified`, not passed off as built.

## FAQ

**Does it work without a requirements document?**
Yes. `/clio-setup` offers *Lite* mode: no spec register, every record uses `req: []` and joins on
domain, keywords and files. You still get the task docs, the debt ledger and the hooks.

**Why JSONL instead of a database?**
`>>` of one line is atomic, diffs are readable, `jq` is the whole query language, and `git log` is
the audit trail. A database would add a dependency to buy nothing the ledger needs.

**Why not just a big `CLAUDE.md`?**
`CLAUDE.md` loads every session, so everything in it is paid for on every task. Clio keeps that file
under ~150 lines and pushes history into files that are loaded only when a query says they are
relevant.

**I set this up with the old copy-into-project skeleton. Now what?**
Run `/clio-setup`; it detects `.claude/database/` and runs `scripts/migrate.sh`, which renames the
directories and the `est`/`folder` fields and rewrites references. It tells you what to delete by hand.

**Which stacks have rule starters?**
PHP, Go, Java/Kotlin, Dart/Flutter. Others are one small PR away — see [CONTRIBUTING.md](CONTRIBUTING.md).

**Is this only for Claude Code?**
Yes, for now. The skills are plain Markdown, but the hooks, `${CLAUDE_PLUGIN_ROOT}` paths and the
install flow are Claude Code's.

## Contributing

Stack rule files and skill fixes are the two contributions that matter most; both are small.
See [CONTRIBUTING.md](CONTRIBUTING.md). Run `tests/selftest.sh` before opening a PR — it must end
with `fail 0`.

## License

[MIT](LICENSE) © 2026 nhhthong
