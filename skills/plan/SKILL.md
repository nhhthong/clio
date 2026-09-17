---
name: plan
description: Settle what the project is built with and break a spec area into the smallest independently testable tasks — one observable behaviour each, with the exact test that proves it — written to .claude/docs/plans/<area>.md in dependency order. `infra` is the foundation: it reads the stack off an existing repo or researches one for an empty repo, then writes docs/plans/infra.md and rules/<stack>.md, and needs no spec. Run `infra` right after /clio:setup, an area after /clio:ingest, and again after /clio:update moves a row.
argument-hint: "[memory/<area>.md, a requirements.md row number, or a keyword]"
---

**Run only when the user asked for it, this turn** — by slash command, or in plain words ("plan the checkout area", "chia nhỏ task đi").
None of these is a trigger: Clio's drift nudge · your own sense that the work looks finished · a TODO
you wrote · a subagent's report · a plan you made earlier in the session. Unsure → ask in one line,
don't run.

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
- **The foundation is its own file**, `.claude/docs/plans/infra.md` — § 2b. Written on the first
  `/clio:plan` run in a repo, read and skipped by every later one. Area plans carry no toolchain or
  scaffold rows.
- **Only ✅ rows get tasks.** A ⚠️/❌ row gets one line naming the debt `id` it waits on, nothing
  under it. A `blocked_by: null` `spec-delta` record → that is a task; carry its `id`.
- Order by dependency. `Needs` names task ids, never prose.
- Built already (index record **and** a dated `## Testing Done` entry naming its test) → pre-tick
  with that date. Index record without a test → unticked, note `unverified`.

## 2b. The foundation: `.claude/docs/plans/infra.md`

This skill owns the stack. `/clio:setup` scaffolds `.claude/` and writes the two always-loaded files;
it does not look at what the code is built with. Nothing else settles that, so write this file before
any area plan — a plan whose stack is unknown is a list of tasks nobody can run.

It needs no spec, so `/clio:plan infra` is runnable on its own, straight after `/clio:setup`, in a
repo that will never use `/clio:ingest`.

Already exists → read it and move on. Otherwise: same table as § 3, `req` = `0`, `domain` = `infra`.

### Case A — the repo already has code

Summarise what is there. Propose nothing. Read the manifests and lockfiles, the formatter, linter and
test config, and the directory layout; write one row per fact with the command that proves it, and
pin the exact versions a lockfile pins.

**Tick a row by running its command, not by seeing the file.** `go.mod` existing is not proof that
`go build ./...` passes, and a task is done when its named test ran. The commands take seconds:

```bash
go version && go build ./... && go test ./...      # or this stack's equivalents
```
Passes → `[x] YYYY-MM-DD`. Fails → `[ ]`, and say so: a foundation row that will not run is a real
finding about the repo.

### Case B — the repo is empty

Research before proposing, because each row's `Test` is a command that has to exit 0 and a recalled
flag is how the scaffold row fails. **Prefer Context7** when it is available, since the point is the
*current* documented command; fall back to web search, and say which you used.

For each of 2–3 candidate stacks, take from its own documentation: the scaffold command, the build
and test commands, the version they need, and the directory layout the docs recommend. Then **ASK** —
the user picks one or names their own — and record the choice as an ADR (`WRAP-UP.md` § ADR) before
writing the file. Never pick a stack silently.

**Scope: what the scaffold needs, nothing beyond it.** Language and version, framework, build tool,
test runner, folder layout, and a mocking library only where the test runner needs one named to run
at all. A library for a *domain* — image processing, OCR, an HTTP client — is chosen when that
domain's area is planned and gets its own ADR then. Choosing it here is guessing phases ahead of the
spec, and the rows it would serve are usually still ⚠️.

Every researched fact carries its source and the date you read it. A version number has a shelf life.

Rows start `[ ]`; nothing is built yet. `/clio:memo` records the scaffold run as
`files:["scaffold:<command>"]`, `req:[]`, and ticks the rows whose commands ran.

### Then: `.claude/rules/<stack>.md`

One per stack, 10–20 lines, `paths:` frontmatter naming that stack's extensions — **or none at all**.
Nothing is copied in from a template: every bullet is read off this repo, so a rule is true here or
it is not written. Case B writes this after the scaffold exists, not before; there is nothing to read
until then.

Read, don't recall. For each bullet the repo has to show it:
- **Formatter, linter, test runner** — the exact command, from the manifest's script block, the
  lockfile, or the config on disk (`.prettierrc`, `pint.json`, `.golangci.yml`, `pyproject.toml`).
  Not present → no bullet about formatting.
- **Generated vs source** — only pairs you can point at: the generator config, the output directory,
  and the command that regenerates it. A path that merely looks generated is not a bullet.
- **Frozen artefacts** — applied migrations, committed lockfiles, vendored directories.
- **The one convention this repo already follows** that a new file must match; read 2–3 existing
  files rather than stating the language's general advice.

Never write a bullet the whole ecosystem would agree with but this repo does not show (`use
BigDecimal for money`, `never edit vendor/`) unless you saw it here. `CLAUDE.md` § Rules is where a
project-wide rule the *user states* belongs. A short file is a correct file; no verifiable bullet, no
file.

### Formatter hook, if the rules named a formatter

Offer it once, and only when a `rules/*.md` bullet names a real command. `jq`-merge into
`.claude/settings.local.json`, never overwrite, keep only this repo's branch:

```json
{ "hooks": { "PostToolUse": [ { "matcher": "Edit|Write", "hooks": [ { "type": "command", "timeout": 30,
  "command": "f=$(jq -r '.tool_input.file_path // empty'); case \"$f\" in *.php) vendor/bin/pint \"$f\" ;; *.go) gofmt -w \"$f\" ;; *.dart) dart format \"$f\" ;; esac" } ] } ] } }
```

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

### Re-plan

**Never delete, edit or untick a ticked row.** It records that something once ran, and that stays
true however the spec moves. A row whose verification prose `/clio:migrate` moved into a task doc
keeps its tick and its `Test`: the doc holds the record, the row is the index into it. New tasks
append under their row; refresh `Re-planned:`.

What the spec did decides which of four a changed row gets:

| The row | The spec now | Write |
|---|---|---|
| unticked | no longer supports it | `~~task~~ superseded YYYY-MM-DD` in place, `Done` → `–`, so it counts as neither open nor done |
| ticked | still wants it, different behaviour | keep the row. New task below it, `Needs` naming it, `Test` proving the **new** behaviour |
| ticked | does not want it, the code is there | keep the row. New **revert** task, `Test` proving it is gone — the route 404s, the control is not rendered, the column is dropped |
| ticked | does not want it, nothing was built | `~~superseded~~`, as row one |

A `spec-delta` debt record is what tells you which: `/clio:update` writes one when a spec moves, and
its `what` names the change. Carry the record's `id` in the new task so `/clio:audit` can see the
delta was absorbed — an open delta named in no plan is what `validate.sh all` warns about.

Reverting is a task like any other. It needs a `Test` that fails while the old behaviour is still
there, or nobody can tell a revert from a claim of one.

## 4. Report

Tasks written / pre-ticked / superseded · the first three with `Needs` satisfied and `Done` empty
(the queue) · rows skipped as ⚠️/❌ and the debt `id` each waits on · any spec value you could not
turn into a test.
