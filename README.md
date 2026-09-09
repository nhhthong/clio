<div align="center">
  <img src="resources/clio_avatar_512.png" alt="Clio, the Muse of History" width="200">

  # Clio

  **A standard layout for `.claude/`** — so Claude Code remembers across sessions
  and asks instead of guessing.

  [![Claude Code plugin](https://img.shields.io/badge/Claude_Code-plugin-D97757?logo=anthropic&logoColor=white)](https://code.claude.com/docs/en/plugins)
  [![Version](https://img.shields.io/badge/version-1.1.0-blue)](CHANGELOG.md)
  [![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
</div>

<br>

Start a task in an area Clio knows, and this is what Claude reads before touching code:

```text
clio:context checkout

Spec      memory/checkout.md · rows 3–5 · row 4 open: tax rounding rule owed by PO since 08-12
Built     2026-08-20 checkout-orders.md — GET /orders, pagination 50/page (commit 3f2a1c)
Owed      cart-rounding · code-debt · CartService.php:52 · blocked_by: null   ← work queue
          tax-rule-open · spec-blocked · waiting on PO                        ← do not start
Next      plan 3.3 — orders list filters by status · test: go test ./orders -run TestListFilter
```

No guessing about row 4. No re-reading last month's diff. One screen, then work.

## Install

```bash
claude plugin marketplace add nhhthong/clio
claude plugin install clio@nhhthong
```

Then, once per repository:

```text
/clio:setup
```

Requires `bash`, `jq`, `git`, `awk`, `sed`. Updates never touch your `.claude/`.

## Why

Every session starts from zero. `CLAUDE.md` grows into a dump of rules, task notes and half-true
facts; the agent reads it all, still cannot tell what was *decided* from what was merely *built*,
and fills the gap with a plausible answer.

Clio fixes the layout, not the model. Each kind of knowledge gets one place, "unverified" becomes
a valid answer, and a short loop writes what happened back to disk before the session ends.

> **Why "Clio"?** In Greek myth, Clio is the Muse of history — one of nine daughters of Mnemosyne,
> the goddess of memory. Her job was to write down what actually happened, and to leave the line
> blank when nobody told her. That is the whole rule this plugin enforces.

## The layout

Everything lives under `.claude/`. Three questions, one home each.

| | Path | Holds | Written by |
|---|---|---|---|
| **Decided** | `docs/specs/requirements.md` | one row per requirement → spec file → decided / open / blocked | humans, `/clio:update` |
| | `docs/specs/memory/*.md` | distilled decisions per area, each quoting its source | `/clio:ingest` |
| | `docs/plans/<area>.md` | decided rows split into the smallest testable tasks | `/clio:plan` |
| **Built** | `clio/index.jsonl` | one line per documented run, append-only | `/clio:memo` |
| | `docs/tasks/*.md` | one doc per feature, for life — updated, never forked | `/clio:memo` |
| | `docs/decisions/*.md` | ADRs | `/clio:memo` |
| **Owed** | `clio/debt.jsonl` | bugs, unverified work, open questions, append-only | `/clio:memo`, `/clio:update` |
| **Always loaded** | `CLAUDE.md` | rules only, ~80 lines; imports `CONTEXT.md`; domain vocabulary | you, `/clio:setup` |
| | `CONTEXT.md` | stable facts: entities, colliding terms, key flows, landmines | you, `/clio:memo` (with a yes) |
| | `rules/<stack>.md` | path-scoped, loads only for the files it names | you, `/clio:setup` |

The three ledgers join on `req`, the requirement row number. `.jsonl` files are append-only: an
update is a new line with the same `id`, readers take the last. Only `CLAUDE.md` and `CONTEXT.md`
load every session; the rest is queried on demand, never read whole.

Already have a `.claude/`? Clio appends its import and one `## Project memory` block, then asks
whether to bring `CLAUDE.md`, `CONTEXT.md` and `rules/` to this layout. Yes → diff shown, second
yes before writing. No → nothing else is touched.

## The loop

```mermaid
flowchart LR
    A(["new task"]) --> B["clio:context<br/>spec · built · owed · next plan task"]
    B -- "open row, no record" --> S(["stop and ask"])
    B --> C["work<br/>one plan task at a time, its Test column is the criterion"]
    C --> D["/clio:memo<br/>task doc · index line · debt lines · plan tick"]
    D -. "next session" .-> A
```

No hook. Run `/clio:memo` when a piece of work is done; skip it and the next session starts
without it.

## Rules the layout enforces

- Not verified by reading, grepping, querying or running → say "unverified" and ask.
- **Decided ≠ built.** Decisions live in the spec register, build state only in the ledgers.
- Ledger lines are never edited, reordered or deleted. One feature, one doc, for life.
- A task is done when its named test ran, not when the code looks right.
- `blocked_by: null` is the work queue; anything else waits. Every open spec point has a debt record.

## Commands

| Command | Does | When |
|---|---|---|
| `/clio:setup` | lay out `.claude/`, fill CLAUDE.md / CONTEXT.md by asking | once per repo |
| `/clio:ingest <doc>` | requirement document → spec files + row table | new source arrives |
| `/clio:plan <area>` | decided rows → smallest testable tasks | after ingest, when a row moves |
| `/clio:context [x]` | no arg: where are we · with area / row / id / question: spec, built, owed, quoted | Claude, before work; you, to ask "why?" |
| `/clio:memo [doc]` | record finished work: task doc, ledgers, plan tick, ADR | after each feature or fix |
| `/clio:update [spec]` | a spec changed: what it invalidates, move the row marker | requirements change |
| `/clio:debt [filter]` | what is still owed, actionable vs. blocked | any time |
| `/clio:ask [x]` | explain any of the above | when unsure |

Skills and the validator stay in the plugin. Nothing outside `.claude/` is touched; without
`.claude/clio/` the skills say so and stop.

<details>
<summary>Auto-enable for a team</summary>

Add to the project's `.claude/settings.json`; members get the plugin when they trust the repo.

```json
{
  "extraKnownMarketplaces": { "nhhthong": { "source": { "source": "github", "repo": "nhhthong/clio" } } },
  "enabledPlugins": { "clio@nhhthong": true }
}
```
</details>

---

<div align="center">
  <sub><a href="CONTRIBUTING.md">Contributing</a> · <a href="CHANGELOG.md">Changelog</a> · MIT © 2026 nhhthong</sub>
</div>
