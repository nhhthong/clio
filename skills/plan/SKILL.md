---
name: plan
description: "Break a spec area into the smallest independently testable tasks, each with the test levels it needs, stored in .claude/clio/database/plan/<area>.jsonl — and change that plan when the spec moves or the user changes their mind. `infra` goes first. Run after /clio:ingest, or when the user asks to plan, re-plan, drop or change a task."
argument-hint: "[infra | area | requirements row | task id | a change in plain words]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio q *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio add plan *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio add index *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test coverage *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test migrate) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio validate *)
---

**Run only when the user asked, this turn** — by slash command or in plain words ("plan the checkout area", "chia nhỏ task đi", "bỏ task 3.2", "đổi lại layout"). Not triggers: the drift nudge, your sense that work looks finished, a TODO, a subagent's report, an earlier plan. Unsure → ask in one line, don't run.

A spec says what must be true; this skill turns it into tasks small enough to prove one at a time and decides *which kinds* of proof each needs (the cases are `/clio:test`'s). It writes only through `clio add plan <area>` (`clio` = `${CLAUDE_PLUGIN_ROOT}/bin/clio`, full path every call), and for `infra` also `.claude/rules/<stack>.md`. Nothing is implemented here. Target: $ARGUMENTS

| The target | Read first, then come back for § 4 |
|---|---|
| any, while `clio q summary` reports 4.x Markdown plans | [cases/MIGRATE.md](cases/MIGRATE.md), whatever was asked |
| `infra`, or no `plan/infra.jsonl` yet | [cases/INFRA.md](cases/INFRA.md) — nothing is planned before it |
| an area with no tasks yet (`clio q plan <area> --all` prints `no tasks`) | nothing: §§ 1–4 |
| an area where tasks exist: a spec-delta, a change of mind, a task to drop, tests that fall short | [cases/CHANGE.md](cases/CHANGE.md) |

## 1. Load
`clio q context <area>` (rows, built, owed, rules, open tasks, what looks wrong), then the spec file in full. Every task of an area, any status: `clio q plan <area> --all`; never read a store file.

## 2. Dig into each row before splitting
A row is the size of a contract line; a list written from the spec alone names files that do not exist. Per ✅ row:
- **The code.** Grep the routes, models, tables, components and config keys it names: what exists, what the row changes, what it must not break. Nothing found → it starts from nothing.
- **The shared values.** A row that changes a constant, a width, a type or a config key → grep every use, not only the files it names. Each other user is decoupled first (an earlier task in `needs`) or follows on purpose; every test asserting the old value is a task of its own (a done task's test cannot be edited).
- **The library.** A row leaning on a framework feature → its *current* API in Context7 (else web search, say which).
- **The gaps.** Anything neither spec nor code settles → a ⚠️ (via `/clio:memo`, or noted on an existing debt `id`). Never fill it with the obvious default.

The findings become each task's `touches` and `levels`, nothing else.

## 3. Split
- **One task = one observable behaviour.** Cannot say what would be observed → split further; still cannot → a ⚠️, not a task. It fits one session with room to prove it: "add the orders endpoint" is four tasks (200 · 401 unauthenticated · pages at the spec's limit · returns the spec's fields).
- **`levels`**: `clio q levels choosing` has the questions; answer each against § 2, not from habit. A bug that would corrupt shared state, grant access or destroy something → `critical`. `mutation` is never added on your own: answer "Beyond critical", name the tasks that qualify with the four answers, **ASK**. A level whose trigger § 2 found but you said no to → an `na` entry with the reason; leaving it out silently is a claim `/clio:test` holds you to.
- **`tier`**: the same output has § Tier. All three yes and not critical → `light`, one level.
- **`touches`**: real paths from § 2. Every number, limit and default in `task` is **copied verbatim from `## Decisions`**; a value the spec does not state → no task, a ⚠️.
- **Only ✅ rows get tasks.** A ⚠️/❌ row is listed in the report with the debt `id` it waits on, never stored. A `spec-delta` with `blocked_by: null` → a task carrying its `id` in `delta`.
- No toolchain or scaffold tasks in an area (they are `infra`'s): a task needing the scaffold names the last infra task in `needs`. Order by dependency; `needs` holds task ids. Ids are `<row>.<n>`, unique across areas (`clio add` refuses a duplicate).

## 4. Show, ASK, write
Show one table — id, task, req, levels (critical first), tier, needs, touches — and the `na` lines. **ASK before writing**: the split is the user's to approve, and a wrong split is paid on every task. Declined → adjust, ask once more, then stop. On a yes, one call per area; a record names only what it sets:
```bash
clio add plan <area> <<'EOF'
{"type":"task","id":"3.1","task":"`GET /orders` returns 200 for an authenticated user","req":["3"],"levels":["unit","api"],"needs":["0.4"],"touches":["orders/handler.go"],"na":{"security":"3.2 proves the unauthenticated path"}}
{"type":"task","id":"3.2","task":"`GET /orders` returns 401 without a session","req":["3"],"levels":["api","security"],"critical":true,"needs":["3.1"],"touches":["orders/handler.go"]}
EOF
```
`FAIL` → nothing was written; fix those records and send the whole batch again. Never write the store any other way (a hook refuses it); a task becomes done only when `/clio:memo` ticks it after the gate.

## 5. Report
Tasks written, changed or dropped, and why · the first three ready (`clio q summary`) · ⚠️/❌ rows skipped and the debt `id` each waits on · any spec value you could not turn into a task. Next: `/clio:test <area>`.
