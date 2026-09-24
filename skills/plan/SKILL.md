---
name: plan
description: Break a spec area into the smallest independently testable tasks — one observable behaviour each, researched against the code and the library docs, with the test levels it needs (unit, api, security, concurrency…) — written to .claude/clio/docs/plans/<area>.md in dependency order. `infra` goes first: it turns the stack /clio:ingest decided (memory/infra.md), or the stack the repo already has, into toolchain and scaffold tasks and writes .claude/rules/<stack>.md. Never chooses a stack. Run `infra` after /clio:ingest, an area after that, and again after /clio:ingest moves a row.
argument-hint: "[infra | memory/<area>.md | a requirements.md row number | a keyword]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/skills/context/scripts/q.sh *) Bash(${CLAUDE_PLUGIN_ROOT}/skills/test/scripts/clio-test.sh coverage *)
---

**Run only when the user asked for it, this turn** — by slash command, or in plain words ("plan the checkout area", "chia nhỏ task đi").
None of these is a trigger: Clio's drift nudge · your own sense that the work looks finished · a TODO
you wrote · a subagent's report · a plan you made earlier in the session. Unsure → ask in one line,
don't run.

A spec says what must be true. This skill turns it into tasks small enough to prove one at a time.
*Which kinds* of proof a task needs is decided here; the cases themselves are `/clio:test`'s. It
writes `.claude/clio/docs/plans/<area>.md`, and for `infra` also `.claude/rules/<stack>.md`; ledgers,
specs and settings stay untouched. Nothing is implemented here.

Target (may be empty — then ask which area): $ARGUMENTS

## 1. Load the area

Run the `clio:context` skill for the target first: the governing `memory/<area>.md` and its rows
(hop 1), what `index.jsonl` says is built (hop 2), what `debt.jsonl` says is open (hop 3). Read the
spec file in full. Existing `.claude/clio/docs/plans/<area>.md` → read it in full; this is a re-plan.
No `plans/infra.md` yet and the target is not `infra` → stop, say `/clio:plan infra` comes first.

## 2. Dig into each row before splitting

`/clio:ingest` wrote each row at the size of a contract line. Before cutting it, find out what it
actually touches — a task list written from the spec alone names files that do not exist. Per ✅ row:

- **The code.** Grep for the routes, models, tables, components and config keys the row names. Note
  what exists, what the row changes, and what it must not break. Nothing found → the row starts from
  nothing; say so.
- **The library.** A row that leans on a framework or library feature → look up the *current* API in
  Context7 (fall back to web search, say which). A task built on a function the docs do not have
  fails on day one.
- **The gaps.** Anything the row needs that neither the spec nor the code settles → a ⚠️, filed via
  `/clio:memo` or noted against an existing debt `id`. Never fill it with the obvious default.

Keep the findings short; they become each task's `Touches` and `Levels` cells, nothing else.

## 3. Split

- **One task = one observable behaviour.** Cannot say what would be observed → split further; still
  cannot → it is a ⚠️, not a task.
- **Smaller wins.** A task fits one session with room to prove it. "Add the orders endpoint" is
  four tasks: route returns 200 · rejects unauthenticated · paginates at the limit the spec names ·
  returns the fields the spec lists.
- **`Levels` names every kind of test the task needs**, from: `unit` `integration` `api` `e2e`
  `contract` `perf` `load` `stress` `security` `concurrency` `regression` `smoke` `mutation`. Judge
  from what § 2 found, not from habit: a DB write → `integration`; a route → `api`; input from outside
  or an access rule → `security`; two actors on one resource → `concurrency`; a bug fix →
  `regression`; another service calls it → `contract`; `perf`/`load`/`stress` only when the spec
  states a number. Money, auth, concurrency or deleting data → prefix `critical ·` (it then needs
  `mutation` too). Leaving a level out is a claim it does not apply — `/clio:test` holds you to it.
- **`Touches` names real paths** from § 2 — the file to change or the directory a new file goes in.
- Every number, limit and default in a task is **copied verbatim from `## Decisions`** and appears in
  its `Task` cell. A value the spec does not state → no task; it is a ⚠️.
- **Only ✅ rows get tasks.** A ⚠️/❌ row gets one line naming the debt `id` it waits on, nothing
  under it. A `blocked_by: null` `spec-delta` record → that is a task; carry its `id`.
- Area plans carry no toolchain or scaffold rows — those live in `infra.md` (§ 3b). An area task that
  needs the scaffold names the last `infra` task in `Needs`.
- Order by dependency. `Needs` names task ids, never prose.
- Built already → leave `[ ]`; `/clio:memo` ticks it once `/clio:test`'s gate passes.

## 3b. `infra`: `.claude/clio/docs/plans/infra.md`

The stack is decided upstream; this skill never picks one. Source, in order:
1. `memory/infra.md` (row `0`, written by `/clio:ingest`) — its `## Decisions` and the ADR it names.
2. No spec (Lite mode) → the repo's own manifests and lockfiles. `req` column is `–`.
3. Neither — an empty repo with no infra spec → stop: `/clio:ingest` a brief, or have the user name
   the stack and record it with `/clio:ingest`. Do not research one here.

Then dig into it the way § 2 digs into a row: for each decided piece — toolchain, scaffold, build,
test runner, formatter, linter — the exact command from the repo's config (repo has code) or from the
tool's current docs via Context7 (empty repo), with the version it needs. Those commands go into
`rules/<stack>.md` below, where `/clio:test` reads them. Every infra task's level is `smoke`; the last
one is the smoke suite every other area's tasks build on.

```markdown
| # | Task | req | Levels | Needs | Touches | Done |
|---|------|-----|--------|-------|---------|------|
| 0.1 | Toolchain on PATH: Go 1.22+, Wails v2 | 0 | smoke | – | – | [ ] |
| 0.2 | Scaffold: `wails init -n app -t svelte-ts` | 0 | smoke | 0.1 | `./` | [ ] |
| 0.3 | Empty build passes | 0 | smoke | 0.2 | – | [ ] |
| 0.4 | Test runner and smoke suite run on the scaffold | 0 | smoke | 0.3 | – | [ ] |
```

### Then: `.claude/rules/<stack>.md`

One per stack, 10–20 lines, `paths:` frontmatter naming that stack's extensions — **or none at all**.
A rule without `paths:` loads every session. Nothing is copied from a template: every bullet is read
off this repo, so a rule is true here or it is not written. Empty repo → write it after the scaffold
task ran, not before; there is nothing to read until then.

For each bullet the repo has to show it:
- **Build, test, format, lint** — the exact command, from the manifest's script block or the config
  on disk (`.prettierrc`, `pint.json`, `.golangci.yml`, `pyproject.toml`). Not present → no bullet.
- **Generated vs source** — only pairs you can point at: the generator config, the output directory,
  and the command that regenerates it. `/clio:memo` reads this to drop build output.
- **Frozen artefacts** — applied migrations, committed lockfiles, vendored directories.
- **The one convention this repo already follows** that a new file must match; read 2–3 existing
  files rather than stating the language's general advice.

Never write a bullet the ecosystem would agree with but this repo does not show. A short file is a
correct file; no verifiable bullet, no file. Show the draft and **ASK** before writing it.

**The file already exists** — a re-plan, an older Clio, or the user wrote it. It is theirs now:
never rewrite, reorder or trim it, and the 10–20 line target is for a new file only.
- Check each bullet you would write against it; propose only the missing ones, as a diff, under the
  section they belong to.
- A bullet the repo now contradicts — a command renamed, a tool removed, a version moved — is
  proposed as its own diff line with what changed and where you read it. Never delete it silently.
- Its `paths:` frontmatter is kept; widen it only when a new bullet needs a path it doesn't cover,
  and say so. A file with no `paths:` loads every session — point that out, don't add one yourself.
- Nothing to add or correct → say so and leave the file untouched.

### Mutation testing, decided once

Critical tasks need a mutation case (`/clio:test`), so settle the tool here rather than per task:
look up this stack's mutation tester in Context7 (PIT for JVM, Stryker for JS/TS/.NET, mutmut for
Python, go-mutesting…), show the install and the threshold flag, and **ASK**. Yes → an ADR and an
infra row installing it, `Levels` `smoke`. No → an ADR saying so, and the line `Mutation: none (ADR
<file>)` under the plan's header — the gate reads it and stops requiring mutation cases. Either way,
the question is not asked again. An infra plan written before this rule has neither — ask on its
next re-plan.

A mechanical rule — format on save, lint before commit — is better as a hook than a bullet. Say so
once and leave the hook to the user; this skill writes no settings file.

## 4. Write `.claude/clio/docs/plans/<area>.md`

```markdown
# Plan — <area>
Spec: memory/<area>.md · rows <n>–<m> · Planned: YYYY-MM-DD · Re-planned: —

| # | Task | req | Levels | Needs | Touches | Done |
|---|------|-----|--------|-------|---------|------|
| 3.1 | `GET /orders` returns 200 for an authenticated user | 3 | unit, api | 0.4 | `orders/handler.go` | [ ] |
| 3.2 | `GET /orders` returns 401 without a session | 3 | critical · api, security | 3.1 | `orders/handler.go` | [ ] |
| 3.3 | List paginates at 50 per page (spec: "50 items") | 3 | unit, integration, api, concurrency | 3.1 | `orders/repo.go` | [ ] |
| 7.1 | — waits on `ocr-dpi-open` (⚠️ row) | 7.1 | – | – | – | – |
```

Ids are `<row>.<n>`. `Done` is `[x] YYYY-MM-DD` (+ the commit, if any) once `/clio:memo` sees
`/clio:test`'s gate pass; `[ ]` otherwise. **Show the full table and ASK before writing** — the split is the user's to
approve; a wrong split is paid on every task. Declined → adjust, ask once more, then stop.

### Re-plan

**Rows already in the file are history.** Never edit, delete, reorder or untick one — not its task,
its `Levels` or `Test` cell, not the header of a pre-4.0 table (`Test that proves it` where
`Levels` now is). The only cell that ever changes is `Done`: `/clio:memo` ticks it, and a re-plan may
set an unticked one to `superseded YYYY-MM-DD → <new id>`, which counts as neither open nor done.

Every improvement is a new row, in a new table appended at the bottom (today's format), and the
header line's `Re-planned:` date is refreshed:

```markdown
## Re-planned YYYY-MM-DD

| # | Task | req | Levels | Needs | Touches | Done |
|---|------|-----|--------|-------|---------|------|
| 3.1.1 | Harden 3.1: security (was: `go test ./orders -run TestListOK`) | 3 | security | 3.1 | `orders/handler.go` | [ ] |
| 4.3.1 | Harden checkout doc (4.1–4.3): integration, concurrency | 4 | critical · integration, concurrency | 4.1, 4.2, 4.3 | `checkout/service.go` | [ ] |
| 3.2.1 | `GET /orders` returns 401 without a session (replaces pre-4.0 row 3.2) | 3 | critical · api, security | 3.1 | `orders/handler.go` | [ ] |
| 3.3.1 | Pagination: 50 → 25 per page (spec-delta `orders-page-25`) | 3 | unit, api | 3.3 | `orders/repo.go` | [ ] |
```
The pre-4.0 row 3.2 above it keeps its task and `Test` cells; only its `Done` becomes
`superseded YYYY-MM-DD → 3.2.1`.

For each existing row, check both causes, and write what the table says:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/context/scripts/q.sh owed --req <row's req>          # spec moved?
${CLAUDE_PLUGIN_ROOT}/skills/test/scripts/clio-test.sh coverage <row id>          # tests enough?
```

| Row | Finding | Write |
|---|---|---|
| ticked | an open `spec-delta` changes its behaviour | sub-task: the new behaviour, `Levels` for it, the delta's `id` in the task |
| ticked | a `spec-delta` drops it, the code is still there | sub-task: revert it, `regression` in `Levels` — the route 404s, the control is gone |
| ticked | tests fall short: `coverage` says `no cases` (every pre-4.0 row), or lacks a level § 3 requires of this code today, or shows a case whose last run was `fail` | a "Harden" sub-task — **one per task doc, not per row** (below); `Levels` = the missing levels, plus `regression` for a failing case; a pre-4.0 row's old `Test` cell quoted in the task |
| ticked | none of the above | nothing — it stays done |
| unticked | the spec no longer wants it | `Done` → `superseded YYYY-MM-DD` |
| unticked, pre-4.0 | still wanted | `Done` → `superseded YYYY-MM-DD → <old id>.<n>`, and the same task as that new row here, with `Levels` — the gate cannot run a `Test`-column row |
| unticked | still wanted | leave it; it is still the plan |

- **Harden by doc.** Group the rows that fall short by the task doc that built them
  (`q.sh built --task <row>`, `type` `task` only — an ADR is not a unit of work). One sub-task per
  doc: its id is `<highest row id it covers>.<n>`, its `Needs` lists every row it covers, and
  `/clio:memo` finds that doc through the id's parent. A row no task doc claims hardens alone.
  Deltas and reverts stay one per row — each is its own behaviour change.
- Any other new row's id is `<old id>.<n>`, the next free `n`. A sub-task's `Needs` names the old
  id; a replacement keeps the old row's `Needs`. Each is gated and ticked on its own.
- A `spec-delta` is carried by `id` in the sub-task: an open delta named in no plan is what
  `validate.sh all` warns about, and carrying the id silences it.
- A revert or a hardening is a task like any other. Its cases must fail while the gap is there, or
  nobody can tell a fix from a claim of one.
- `clio-test.sh gate` refuses a pre-4.0 row; its sub-task is what gets gated.

## 5. Report

Tasks written / superseded / sub-tasks added and why (spec or tests) · the first three with `Needs`
satisfied and `Done` empty (the queue) · rows skipped as ⚠️/❌ and the debt `id` each waits on · any spec value you could not
turn into a task. Next: `/clio:test <task>` for the first task in the queue.
