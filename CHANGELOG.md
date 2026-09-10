# Changelog

## 2.0.1 — 2026-09-10

- `validate.sh`: the schema check now also requires `commits` to be an array, so a line still
  carrying the removed scalar `commit` (or omitting `commits`) no longer passes.
- `validate.sh all`: one malformed line in a ledger no longer makes `jq` abort and misfire every
  other check — the per-record schema checks, orphan / supersedes trail, and the requirements.md
  markers all run against the parseable lines now; the bad line is still its own FAIL.
- `validate.sh all`: the "pre-2.0 delta ledger" warning fires only when a record actually looks
  pre-2.0 (scalar `commit`, or no `commits`). A clean 2.0 doc that drops a reverted file from
  `files` — allowed by `INDEX-IT.md` — is no longer nagged.
- `validate.sh`: a `spec-blocked` record may carry a null `blocked_by` once it has been unblocked
  (`DEBT-IT.md` § 1). The "needs a non-null blocked_by" check is now group-aware — it looks at the
  record that *files* the id, so `/clio:update` unblocking one no longer leaves a permanent FAIL.
- `/clio:setup` step 1: the `CLAUDE.md` block now `cp`s the template itself when no file exists,
  instead of leaving a stub with the title and `## Architecture` / `## Code style` sections missing.

## 2.0.0 — 2026-09-10

**Breaking — `index.jsonl` is last-wins in every field.** A doc's last record is its full current
state: `files`, `keywords` and the new `commits` array are restated in full every run, like `req`
and `specs` already were. One read rule instead of two; `debt.jsonl` and `index.jsonl` now behave
the same. Scalar `commit` is gone. Migrate a pre-2.0 ledger once (keeps a backup, collapses each
doc's delta records into one full-state record):

```bash
cp .claude/clio/index.jsonl .claude/clio/index.jsonl.pre2
jq -s -c 'group_by(.doc)[] | last + {files:(map(.files[]?)|unique), keywords:(map(.keywords[]?)|unique),
  commits:([.[] | .commit, .commits[]?] | map(values) | unique)} | del(.commit)' \
  .claude/clio/index.jsonl.pre2 > .claude/clio/index.jsonl
```
`validate.sh all` warns when a doc's last record drops files an earlier record named.

- `validate.sh` now checks what the schema states: `kind` and `status` enums, `type` ∈ task/adr,
  `spec-blocked` must carry a `blocked_by`, debt `req` rows must exist. Orphan and supersedes
  checks use `jq`, not `grep` on formatting. `validate.sh index` no longer errors on an invalid last
  line. Warns on HTML comments in `CLAUDE.md` as well as `CONTEXT.md`.
- New `skills/memo/scripts/test.sh`: fixture-based check of the validator.
- `permissions.json`: `Read`/`Edit` rules for keys, certs and `.env` now match nested paths
  (`**/*.key`); dead `Bash(> /dev:*)` rule removed.
- `/clio:setup` checks for `sed` (README already required it). Batch 3 names the Clio rule each tool
  serves; `ponytail` / `caveman` sit in a separate "optional, taste" group.
- `CLAUDE.md` template: dropped the claim that the harness strips HTML comments; both files are
  filled from their comments and then stripped, same rule.
- `clio:context` description cut to two sentences (it loads every session).
- README: what Clio is (a project-memory kit: layout, ledgers, loop — and which layers stand alone), what it is not, how it differs from auto-memory and skills packs;
  the loop diagram now shows the three ledgers and `/clio:update` → `/clio:plan`; star-history link
  fixed.

## 1.1.0 — 2026-09-09

- New `/clio:plan <area>`: splits a spec area's ✅ rows into the smallest tasks that each name the
  test proving them, written to `.claude/docs/plans/<area>.md`. `clio:context` reads the plan to
  pick the next task; `/clio:memo` ticks a task only when its test ran.
- `clio:context` has two depths: no target → hop 0, an overview from counts only (per plan
  done/open + next task, debt queue vs blocked, last memo), nothing opened; a target or a question
  → hops 1–3, then only the docs those records name, answered with `file:line` quotes. Takes an
  argument now: `/clio:context checkout`, `/clio:context 18`, `/clio:context cart-rounding`.
- `/clio:setup` drafts `CLAUDE.md` and `CONTEXT.md`, shows both in full and asks before writing —
  never writes either file on a guess. Existing `CLAUDE.md` / `CONTEXT.md` / `rules/` get only the
  import and the `## Project memory` block appended, plus one question: bring them to Clio's
  template format and line budget? Yes → diff shown, asked again. `CLIO-CONTEXT.md` is gone.
- Fixed: `sed -i '$d'` in the memo steps failed on macOS (BSD sed); now `sed -i.bak`, and `gnu-sed`
  is no longer required.
- Fixed: `validate.sh` matched requirement row `3` against `"req":[13]` when checking for index
  records; now compares whole values via `jq`.
- Fixed: `permissions.json` rule `Bash(mv /* :*)` had a stray space and never matched.
- `validate.sh all` no longer warns "`.files` is empty" on every doc whose last run was docs-only;
  the warning is kept for `validate.sh index` only. `requirements.md` is parsed once per run.
- Every path is now `${CLAUDE_PLUGIN_ROOT}/…`; `CLAUDE_SKILL_DIR` is no longer used.
- `/clio:memo` falls back to `git status --porcelain` (was `git diff HEAD`, which missed new
  untracked files).

## 1.0.2 — 2026-09-08

- Skills renamed to `setup`, `context`, `memo`, `update`, `ingest`, `debt`, `ask`. Plugin skills are
  namespaced by Claude Code, so the commands are `/clio:memo`, `/clio:debt` and so on; the old
  `clio-` prefix doubled the name.
- `/clio:setup` keeps an existing `CLAUDE.md` (root or `.claude/`) and appends only what Clio
  needs; asks what to do with an existing `.claude/CONTEXT.md`; three question batches instead of
  six; greenfield fills context from the requirement document itself; real install commands and
  per-repo off switches for `ponytail` and `caveman`.
- `validate.sh` no longer counts CLAUDE.md lines or needs perl.

## 1.0.1 — 2026-09-08

- `/clio:setup` gained a tooling step: it lists missing MCP servers and plugins once and installs
  only what you pick.
- No hooks; one script (the validator); no test suite. The strict permission list is back as an
  opt-in ASK inside the tooling step. `clio:update` and
  `clio:ingest` are single files.

## 1.0.0 — 2026-09-08

First release as a Claude Code plugin.
