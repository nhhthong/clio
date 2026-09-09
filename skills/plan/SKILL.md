---
name: plan
description: Break a spec area into the smallest independently testable tasks — one observable behaviour each, with the exact test that proves it — written to .claude/docs/plans/<area>.md in dependency order. Run after /clio:ingest, whenever the user asks Clio to read a spec and plan the work, and again after /clio:update moves a row.
argument-hint: "[memory/<area>.md, a requirements.md row number, or a keyword]"
disable-model-invocation: true
---

A spec says what must be true. This skill turns it into a list of things small enough that each one
is either proven by a named test or not done. It writes **only** `.claude/docs/plans/<area>.md`;
ledgers and specs stay untouched. Nothing is implemented here.

Target (may be empty — then ask which area): $ARGUMENTS

## 1. Load the area

Run the `clio:context` skill for the target first: the governing `memory/<area>.md` and its rows
(hop 1), what `index.jsonl` says is built (hop 2), what `debt.jsonl` says is open (hop 3). Read the
spec file in full. Existing `.claude/docs/plans/<area>.md` → read it in full; this is a re-plan.

## 2. Split

- **One task = one observable behaviour, proven by one test.** Cannot name the test → split
  further; still cannot → it is a ⚠️, not a task.
- **Smaller wins.** A task fits one session with room to run its test. "Add the orders endpoint" is
  four tasks: route returns 200 · rejects unauthenticated · paginates at the limit the spec names ·
  returns the fields the spec lists.
- **The test is exact**: a command (`go test ./orders -run TestListPaginates`), a request + the
  response expected, or numbered manual steps ending in what must be observed. "Works", "verified",
  "check it" are not tests.
- Every number, limit and default in a task is **copied verbatim from `## Decisions`** and appears in
  its test. A value the spec does not state → no task; it is a ⚠️ (file it via `/clio:memo`, or note
  the existing debt `id`).
- **Row 0 — foundation, before any spec row, any stack.** No index record for the area and the
  toolchain, scaffold or build is not proven on disk → emit `0.n` tasks first, always the same
  four: (1) toolchain on PATH at a named version, (2) scaffold run, (3) empty build exits 0,
  (4) test runner exits 0 on the scaffold. The stack and its commands come from, in order:
  `.claude/rules/<stack>.md` · the greenfield ADR · `CONTEXT.md` § Dev Environment · the manifest
  on disk (`go.mod`, `package.json`, …). None of those names a stack → **ASK**: propose 2–3
  stacks that fit the spec (each with the four commands and why it fits), let the user pick or
  name their own, then record the choice as an ADR before writing the plan. Never pick a stack
  silently. Skip a `0.n` whose proof already exists (manifest committed, `## Testing Done` names
  the build). `req` = `0`. `/clio:memo` records the scaffold as `files:["scaffold:<command>"]`,
  `req:[]`.
- **Only ✅ rows get tasks.** A ⚠️/❌ row gets one line naming the debt `id` it waits on, nothing
  under it. A `blocked_by: null` `spec-delta` record → that is a task; carry its `id`.
- Order by dependency. `Needs` names task ids, never prose.
- Built already (index record **and** a dated `## Testing Done` entry naming its test) → pre-tick
  with that date. Index record without a test → unticked, note `unverified`.

## 3. Write `.claude/docs/plans/<area>.md`

```markdown
# Plan — <area>
Spec: memory/<area>.md · rows <n>–<m> · Planned: YYYY-MM-DD · Re-planned: —

| # | Task | req | Test that proves it | Needs | Done |
|---|------|-----|---------------------|-------|------|
| 0.1 | Toolchain on PATH (example stack: Go 1.22+, Wails v2) | 0 | `go version && wails doctor` exit 0, Go ≥ 1.22 | – | [ ] |
| 0.2 | Scaffold run | 0 | `wails init -n app -t svelte-ts` exits 0, `go.mod` present | 0.1 | [ ] |
| 0.3 | Empty build passes | 0 | `wails build` exits 0 | 0.2 | [ ] |
| 0.4 | Test runner runs on the scaffold | 0 | `go test ./...` exits 0 | 0.3 | [ ] |
| 3.1 | `GET /orders` returns 200 for an authenticated user | 3 | `go test ./orders -run TestListOK` | 0.4 | [ ] |
| 3.2 | `GET /orders` returns 401 without a session | 3 | `go test ./orders -run TestListAuth` | 3.1 | [ ] |
| 3.3 | List paginates at 50 per page (spec: "50 items") | 3 | `go test ./orders -run TestListPage` | 3.1 | [ ] |
| 7.1 | — waits on `ocr-dpi-open` (⚠️ row) | 7.1 | – | – | – |
```

Ids are `<row>.<n>`. `Done` is `[x] YYYY-MM-DD <commit>` once `/clio:memo` records the test ran;
`[ ]` otherwise. **Show the full table and ASK before writing** — the split is the user's to
approve; a wrong split is paid on every task. Declined → adjust, ask once more, then stop.

Re-plan: never delete or edit a ticked row. An unticked task the spec no longer supports →
`~~task~~ superseded YYYY-MM-DD` in place and `Done` set to `–` (so it no longer counts as open).
New tasks append under their row; refresh `Re-planned:`.

## 4. Report

Tasks written / pre-ticked / superseded · the first three with `Needs` satisfied and `Done` empty
(the queue) · rows skipped as ⚠️/❌ and the debt `id` each waits on · any spec value you could not
turn into a test.
