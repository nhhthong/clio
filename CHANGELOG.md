# Changelog

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
