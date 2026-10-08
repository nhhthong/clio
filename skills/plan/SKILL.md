---
name: plan
description: "Break a spec area into the smallest independently testable tasks, each with the test levels it needs, stored in .claude/clio/database/plan/<area>.jsonl — and change that plan when the spec moves or the user changes their mind. `infra` goes first. Run after /clio:ingest, or when the user asks to plan, re-plan, drop or change a task."
argument-hint: "[infra | area | requirements row | task id | a change in plain words]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio q *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio add plan *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test coverage *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test migrate) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio validate *)
---

**Run only when the user asked for it, this turn** — by slash command, or in plain words ("plan the checkout area", "chia nhỏ task đi", "bỏ task 3.2", "đổi lại layout"). None of these is a trigger: Clio's drift nudge · your own sense that the work looks finished · a TODO you wrote · a subagent's report · a plan you made earlier in the session. Unsure → ask in one line, don't run.

A spec says what must be true. This skill turns it into tasks small enough to prove one at a time,
and decides *which kinds* of proof each needs; the cases are `/clio:test`'s. It writes only through
`clio add plan <area>` — for `infra` also `.claude/rules/<stack>.md`. Nothing is implemented here.

Target: $ARGUMENTS

Every Bash call is a fresh shell: call the script by its full path, `${CLAUDE_PLUGIN_ROOT}/bin/clio`,
written `clio` below.

## Which case

| The target | Read, then come back for § 4 |
|---|---|
| any — while `clio q summary` reports 4.x Markdown plans (a 4.x project) | [cases/MIGRATE.md](cases/MIGRATE.md) first, whatever was asked |
| `infra`, or no `plan/infra.jsonl` yet | [cases/INFRA.md](cases/INFRA.md) — no area is planned before it |
| an area with no tasks yet | nothing — §§ 1–4 below |
| an area, task or change where tasks exist — a spec-delta, a change of mind, a task to drop, tests that fall short | [cases/CHANGE.md](cases/CHANGE.md) |

`clio q plan <area> --all` tells which: it prints every task of the area, or `no tasks`.

## 1. Load the area

Run the `clio:context` skill for the target: the governing `memory/<area>.md` and its rows, what is
built, what is owed. Read the spec file in full. Read the area's tasks with `clio q plan <area> --all`,
never the store file itself.

## 2. Dig into each row before splitting

`/clio:ingest` wrote each row at the size of a contract line. A task list written from the spec alone
names files that do not exist. Per ✅ row:
- **The code.** Grep for the routes, models, tables, components and config keys the row names: what
  exists, what the row changes, what it must not break. Nothing found → say the row starts from nothing.
- **The shared values.** A row that changes a constant, a width, a type or a config key → grep every
  use of it, not only the files the row names. Each other user is either decoupled first (that task
  comes earlier in `needs`) or follows the change on purpose; and every test asserting the old value
  is a task of its own — a done task's test cannot be edited, its new expectation is a sub-task. Found
  late, this reorders the plan: while the tasks are still open that is an edit in place.
- **The library.** A row leaning on a framework or library feature → its *current* API in Context7
  (fall back to web search, say which).
- **The gaps.** Anything neither spec nor code settles → a ⚠️, filed via `/clio:memo` or noted
  against an existing debt `id`. Never fill it with the obvious default.

The findings become each task's `touches` and `levels`, nothing else.

## 3. Split

- **One task = one observable behaviour.** Cannot say what would be observed → split further; still
  cannot → it is a ⚠️, not a task. A task fits one session with room to prove it: "add the orders
  endpoint" is four tasks — returns 200 · rejects unauthenticated · paginates at the spec's limit ·
  returns the spec's fields.
- **`levels`**: answer every question of `${CLAUDE_PLUGIN_ROOT}/skills/test/LEVELS.md` § Choosing
  against what § 2 found, not from habit. Each yes is a level unless that section says it does not
  earn it. A bug that would corrupt shared state, grant access or destroy something → `critical`.
  `mutation` is never added on your own: answer § Choosing "Beyond critical", name the tasks that
  qualify with the four answers, and **ASK**. A level whose trigger § 2 found and you still said no
  to → an `na` entry with the reason; leaving it out silently is a claim `/clio:test` holds you to.
- **`tier`**: answer LEVELS.md § Tier. All three yes and not critical → `light`, one level. Most UI
  polish is light; most logic is not.
- **`touches`** names real paths from § 2 — the file to change or the directory a new file goes in.
- Every number, limit and default in a task is **copied verbatim from `## Decisions`** into `task`.
  A value the spec does not state → no task; a ⚠️.
- **Only ✅ rows get tasks.** A ⚠️/❌ row is listed in the report with the debt `id` it waits on,
  never stored. A `blocked_by: null` `spec-delta` → a task carrying its `id` in `delta`.
- Area plans carry no toolchain or scaffold tasks; a task needing the scaffold names the last
  `infra` task in `needs`. Order by dependency; `needs` holds task ids, never prose.
- Ids are `<row>.<n>`, unique across every area — `clio add` refuses a duplicate.

## 4. Show, ASK, write

Show the tasks as one table — id, task, req, levels (critical first), tier, needs, touches — and the
`na` lines under it. **ASK before writing**: the split is the user's to approve; a wrong split is paid
on every task. Declined → adjust, ask once more, then stop.

On a yes, one call for the area — a record names only what it sets, the rest takes its default:
```bash
clio add plan <area> <<'EOF'
{"type":"task","id":"3.1","task":"`GET /orders` returns 200 for an authenticated user","req":["3"],"levels":["unit","api"],"needs":["0.4"],"touches":["orders/handler.go"],"na":{"security":"3.2 proves the unauthenticated path"}}
{"type":"task","id":"3.2","task":"`GET /orders` returns 401 without a session","req":["3"],"levels":["api","security"],"critical":true,"needs":["3.1"],"touches":["orders/handler.go"]}
EOF
```
`FAIL` lines → nothing was written; fix those records and send the whole batch again. Never write
the store any other way — a hook refuses it, and a task becomes done only through the gate, when `/clio:memo` ticks it.

## 5. Report

Tasks written, changed or dropped and why · the first three ready tasks (`clio q summary` computes
the queue) · ⚠️/❌ rows skipped and the debt `id` each waits on · any spec value you could not turn
into a task. Next: `/clio:test <area>` — it designs the ready tasks as one batch and asks once.
