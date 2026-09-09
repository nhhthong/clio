<div align="center">
  <img src="resources/clio_avatar_512.png" alt="Clio, the Muse of History" width="220">

  # Clio

  **A standard layout for `.claude/`** — so Claude Code remembers across sessions
  and asks instead of guessing.

  [![Claude Code plugin](https://img.shields.io/badge/Claude_Code-plugin-D97757?logo=anthropic&logoColor=white)](https://code.claude.com/docs/en/plugins)
  [![Version](https://img.shields.io/badge/version-1.1.0-blue)](CHANGELOG.md)
  [![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
</div>

---

Every session starts from zero. `CLAUDE.md` grows into a dump of rules, task notes and half-true
facts; the agent reads it all, still cannot tell what was decided from what was merely built, and
fills the gap with a plausible answer. Clio fixes the layout, not the model: one place for each kind
of knowledge, rules that make "unverified" a valid answer, and a loop that writes what happened
back to disk before the session ends.

## The standard

```
.claude/
├── CLAUDE.md                 # rules only, ≤ ~80 lines; imports CONTEXT.md; domain vocabulary
├── CONTEXT.md                # stable facts: entities, terms that collide, key flows, landmines
├── rules/<stack>.md          # path-scoped, loads only for files it names
├── clio/
│   ├── index.jsonl           # what was BUILT — one line per documented run, append-only
│   └── debt.jsonl            # what is OWED — bugs, unverified work, open questions, append-only
└── docs/
    ├── specs/requirements.md # what was DECIDED — row → spec file → decided / open / blocked
    ├── specs/memory/*.md     # distilled decisions per area, each quoting its source verbatim
    ├── plans/<area>.md       # decided rows split into the smallest testable tasks
    ├── tasks/*.md            # one doc per feature, forever — updated, never forked
    └── decisions/*.md        # ADRs
```

Three questions, three homes, never mixed:

| Question | Home | Written by |
|---|---|---|
| Has it been **decided**? | `docs/specs/requirements.md`, status column | humans + `/clio:update` |
| Was it **built**, when, how? | `clio/index.jsonl` → `docs/tasks/*.md` | `/clio:memo` |
| What is still **owed**? | `clio/debt.jsonl` | `/clio:memo`, `/clio:update` |

They join on `req`, the requirement row number. The `.jsonl` files are append-only: an update is a
new line with the same `id`, readers take the last one. `CLAUDE.md` and `CONTEXT.md` load every
session and stay short; everything else is loaded on demand, by query, never by reading the folder.

## The loop

```
  new task ──► clio:context (auto)  governing spec → what was built → what is owed → next plan task
      │                             open row with no record? stop and ask, don't guess
      ▼
  work, one plan task at a time — its Test column is the success criterion
      │
      ▼
  /clio:memo ──► task doc · index.jsonl line · debt.jsonl lines · plan tick (only if the test ran)
```

No hook. Run `/clio:memo` when a piece of work is done; skip it and the next session starts
without that work in its memory.

## Rules the layout enforces

- Not verified by reading, grepping, querying or running → say "unverified" and ask. Never fill a
  gap with a plausible answer.
- **Decided ≠ built.** A decided row in the spec register means a decision exists; build state
  lives only in the ledgers. Nobody writes progress into a spec, or a decision into a ledger.
- Ledger lines are never edited, reordered or deleted. One feature, one doc, forever.
- A task is done when its named test ran, not when the code looks right.
- `blocked_by: null` is the work queue; anything else waits. Every open spec point has a debt record.

## Install

Requires `bash`, `jq`, `git`, `awk`, `sed`.

```bash
claude plugin marketplace add nhhthong/clio
claude plugin install clio@nhhthong
```

Update with `claude plugin update clio`; your `.claude/` is never touched by an update. To have a
team pick it up when they trust the repo, add to the project's `.claude/settings.json`:

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

Once per repository. Lays out `.claude/` as above, asks for domain vocabulary, timezone, money,
generated files and the things that are expensive to get wrong, drafts `CLAUDE.md` and
`CONTEXT.md`, shows both and writes only what you approve.

**Already have a `.claude/`?** Clio appends its import and one `## Project memory` block, then asks
one question: bring `CLAUDE.md` / `CONTEXT.md` / `rules/` to this layout and line budget? Yes →
diff shown, nothing written without a second yes. No → nothing else is touched.

```
/clio:ingest docs/requirements.pdf
/clio:plan checkout
```

With a requirements document: distil it into `specs/memory/<area>.md` + the row table, every
undecided point marked open with the name of whoever owes the answer. Then split an area's decided
rows into tasks small enough that each names the test proving it.

## Commands

| Command | Does | Run when |
|---|---|---|
| `/clio:setup` | lay out `.claude/`, fill CLAUDE.md / CONTEXT.md by asking | once per repo |
| `/clio:ingest <doc>` | requirement document → `specs/memory/*.md` + `requirements.md` | once, and when a new source arrives |
| `/clio:plan <area>` | decided rows → smallest testable tasks → `plans/<area>.md` | after ingest, and when a row moves |
| `/clio:context [x]` | no arg: where are we — plans done/open, next task, debt queue · with an area / row / debt id / question: spec, what was built, what is owed, quoted from the docs | Claude triggers it before work; you, to ask "where are we?" or "why?" |
| `/clio:memo [doc]` | record finished work: task doc, ledgers, plan tick, CONTEXT.md diff, ADR | after each feature or fix |
| `/clio:update [spec]` | a spec changed: what it invalidates, safe to build yet, move the row marker | when requirements change |
| `/clio:debt [filter]` | what is still owed, actionable vs. blocked | any time |
| `/clio:ask [x]` | explain any of the above | when unsure |

Skills and the validator stay in the plugin. Nothing outside `.claude/` is touched; in a project
without `.claude/clio/` the skills say so and stop.

## Contributing

One source of truth: ledger schema in `skills/memo/steps/DEBT-IT.md` and `INDEX-IT.md`, validation
in `skills/memo/scripts/validate.sh`. `claude plugin validate .` must pass. Stack rule starters live
in `skills/setup/rules/`; a new one is 10–20 verified bullets with `paths:` frontmatter plus its
marker file on the `ls` line in `skills/setup/SKILL.md` step 1. Try a working copy with
`claude plugin marketplace add /path/to/clio`, then `claude plugin install clio@nhhthong`.

Named after the Greek Muse of history, daughter of Memory, who wrote down what happened and left
the line blank when nobody told her.

## License

[MIT](LICENSE) © 2026 nhhthong
