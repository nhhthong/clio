---
name: plan
description: Break a spec area into the smallest independently testable tasks, each with the test levels it needs, and change that plan when the spec moves or the user changes their mind. Use after /clio:ingest, or when the user asks to plan, re-plan, drop or change a task. Plan `infra` first.
argument-hint: "[infra | area | requirements row | task id | a change in plain words]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio q *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio add plan *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio add index *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio test coverage *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio validate *)
---

Target: $ARGUMENTS

Run only when the user asked this turn, by slash command or in plain words ("plan the checkout area", "chia nhỏ task đi", "bỏ task 3.2", "đổi lại layout"). A drift nudge, a TODO, a subagent report or an earlier plan is not a request. Unsure: ask in one line.

A spec says what must be true. This skill turns it into tasks small enough to prove one at a time, and decides which kinds of proof each needs. The test cases belong to `/clio:test`. Nothing is implemented here.

Write only through `clio add plan <area>`, with the records on stdin ([RECORDS.md](RECORDS.md)). For `infra`, also write `.claude/rules/<stack>.md`. A hook refuses any other write to the store.

## Pick the case
Read the case file first, then the steps below.

| Target | Case |
|---|---|
| `infra`, or no `plan/infra.jsonl` yet | [cases/INFRA.md](cases/INFRA.md). Nothing is planned before it |
| An area with no tasks yet (`clio q plan <area> --all` prints `no tasks`) | None |
| An area with tasks: a spec delta, a change of mind, a task to drop, tests that fall short | [cases/CHANGE.md](cases/CHANGE.md) |

## Steps
1. **Load.** Run `clio q context <area>`, then read the spec file in full. List every task of the area with `clio q plan <area> --all`. Never read a store file.
2. **Dig into each decided row before splitting.** A row is the size of a contract line, and a list written from the spec alone names files that do not exist.
   - Code: grep the routes, models, tables, components and config keys the row names. Note what exists, what the row changes and what it must not break.
   - Shared values: when a row changes a constant, width, type or config key, grep every use. Decouple each other user in an earlier task (`needs`), or let it follow on purpose. A test asserting the old value gets its own task, because a done task's test cannot be edited.
   - Library: for a framework feature, read the current API in Context7 (web search if absent; say which).
   - Gaps: anything neither spec nor code settles is an open point. Note it on the debt `id` or through `/clio:memo`. Never fill it with the obvious default, because the default looks decided and nobody asks again.
3. **Split.**
   - One task is one observable behaviour. If you cannot say what would be observed, split further. Still cannot: it is an open point, not a task. Example: "add the orders endpoint" is four tasks (200, 401 unauthenticated, pages at the spec's limit, returns the spec's fields).
   - `levels`: answer the questions from `clio q levels choosing` against step 2, not from habit. A bug that would corrupt shared state, grant access or destroy data makes the task `critical`. Never add `mutation` on your own: name the tasks that qualify and ask. When step 2 found a trigger for a level and you said no, add an `na` entry with the reason. Leaving it out is a claim `/clio:test` holds you to.
   - `tier`: the same output has the tier rules. If all three answers are yes and the task is not critical, use `light` with one level.
   - `touches`: real paths from step 2. Copy every number, limit and default in `task` verbatim from `## Decisions`. A value the spec does not state means no task and an open point.
   - Only decided rows get tasks. List an open or blocked row in the report with the debt `id` it waits on. A `spec-delta` with `blocked_by` null becomes a task carrying its `id` in `delta`.
   - Scaffold and toolchain tasks belong to `infra`. A task that needs the scaffold names the last infra task in `needs`. Order by dependency. Ids are `<row>.<n>` and unique across areas.
4. **Show, ask, write.** Show one table: id, task, req, levels (critical first), tier, needs, touches, and the `na` lines. Ask before writing, because a wrong split costs on every task. If declined, adjust, ask once more, then stop. On a yes, write one call per area. A record names only the fields it sets. If the call prints `FAIL`, nothing was written: fix those records and send the whole batch again.
5. **Report.** Tasks written, changed or dropped, and why. The first three ready tasks (`clio q summary`). Open or blocked rows skipped, with their debt `id`. Any spec value you could not turn into a task. Next step: `/clio:test <area>`.

A task becomes done only when `/clio:memo` ticks it after the test gate passes.
