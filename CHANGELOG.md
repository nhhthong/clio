# Changelog

## 4.0.0 — 2026-09-24

Breaking. Layout moved, `/clio:update` merged into `/clio:ingest`, new `/clio:test`, `req` now strings.

**Migrate 3.x by hand** — `/clio:setup` stops on old layout:
```bash
mkdir -p .claude/clio/database
git mv .claude/clio/index.jsonl .claude/clio/debt.jsonl .claude/clio/database/
git mv .claude/docs .claude/clio/docs
mkdir -p .claude/clio/docs/tests && touch .claude/clio/database/runs.jsonl
```
Then:
- Append one restated record per `id` with new paths. Never edit a line.
- Move `Domains` line `CLAUDE.md` → `requirements.md`, add `Last ingest:` under its title, run `q.sh spec-mark` once.
- `.gitattributes` → `.claude/clio/.gitattributes`: `database/*.jsonl merge=union`.
- Old numeric `req` still resolve. Plans with `Test` column stay; `/clio:plan <area>` re-plans them into sub-tasks.

Changes:
- **Layout.** All under `.claude/clio/`: `docs/` (specs, plans, tests, tasks, decisions), `database/` (`index`, `debt`, `runs`). Setup no longer writes `CLAUDE.md` / `CONTEXT.md`.
- **New `/clio:test`.** Agree seams → cases per level (`LEVELS.md`), expected values from spec → red → green one case at a time. `clio-test.sh run` only writer of `runs.jsonl`. `gate` passes task only when every case passed on current content fingerprint. Flaky = fail. Critical task: mutation case (unless `Mutation: none`), every case seen red. Concurrency ≥ 20 repeats.
- **Ingest** proposes stack as `memory/infra.md` (row `0`, ADR). Does old `/clio:update` job: re-ingest or sweep (diff vs spec snapshot) → `spec-delta`, row markers, areas to re-plan.
- **Plan** never picks stack, writes no settings, researches each row first, names test `Levels`. Re-plan never edits a row: improvements = sub-tasks in `## Re-planned`, hardening one per task doc. Never rewrites existing `rules/<stack>.md`.
- **Memo** ticks only on passing gate. Uncommitted work → empty commit, hash backfilled later. Lesson goes to lowest level it recurs in: task doc → feature `summary.md` § General Memory → path-scoped rule → `CONTEXT.md` / `CLAUDE.md` (ask first).
- **`req` = strings.** As numbers `7.1` and `7.10` collided.
- **`q.sh`** holds every ledger read. Context gains rules hop.
- **Scripts called by full path from `SKILL.md`.** `${CLAUDE_PLUGIN_ROOT}` not substituted in step files, not exported to Bash. `allowed-tools` pre-approves scripts.
- **Fixed after real 3.x repo run:** validate failed moved doc on its history; post-migration sweep saw every spec as new; memo made new doc for re-plan sub-task; hook nudged for already-memo'd files.

## 3.2.0 — 2026-09-18

- README 255 → 180 lines.
- **Fixed:** drift nudge never loaded. `plugin.json` named conventional `hooks/hooks.json`, loader refused duplicate. Dead since 2.1.0.
- Ten skills → six. `/clio:debt` → hop 3, `/clio:audit` checks → `validate.sh`, `/clio:migrate` + `VERSION` + `/clio:ask` removed.
- `/clio:memo` five steps, not six.
- `CLAUDE.md` template `## Rules` trimmed.
- `validate.sh` joins `requirements.md` to plan tables.
- `/clio:update` names stale plans; `--fix` re-plans.

## 3.1.0 — 2026-09-17

- New `/clio:audit` (drift between layers). Old `audit` → `/clio:migrate`.
- Doc sections invalidated by closed `spec-delta` marked superseded.
- `validate.sh`: FAIL on duplicate task id in plan; WARN on open `spec-delta` in no plan.
- Ticked row whose spec moved: new task or revert task, tick never edited.
- `/clio:plan` owns stack, setup stops touching it. New `docs/plans/infra.md`; rows ticked by running command.
- Hop 3 surfaces `spec-delta` `docs[]`.

## 3.0.0 — 2026-09-17

Breaking: task docs per feature directory, `index.jsonl` keys on `id`.

- One directory per feature, one doc per sub-task (`<id>_<name>.md`), optional `summary.md`.
- `id` = creation timestamp = filename prefix. Never changes.
- `plan_tasks` joins doc to plan rows.
- New `/clio:audit` migration (renamed `/clio:migrate` 3.1, removed 3.2).
- Writing skills model-invocable again; guard in prose, not `disable-model-invocation`.
- Readers bridge pre-3.0 records.
- `validate.sh`: checks `plan_tasks`, dead links, recursive orphan check.
- Keyword vocabulary printed before picking one.
- Setup writes `merge=union` `.gitattributes`.
- Removed: stack-rule starters, CI, `permissions.json`, `update` field.

## 2.1.0 — 2026-09-14

- New drift nudge: `UserPromptSubmit` hook, once per session.
- Setup writes only under `.claude/`, installs nothing.
- `test.sh` back. CI added.
- `validate.sh`: one group-aware `spec-blocked` check; every schema field required.
- `/clio:update` asks before ⚠️/❌ → ✅.

## 2.0.1 — 2026-09-10

- `validate.sh`: `commits` must be array; malformed line no longer aborts `all`; pre-2.0 warning precise; unblocked `spec-blocked` allowed.
- Setup copies full `CLAUDE.md` template.

## 2.0.0 — 2026-09-10

Breaking: `index.jsonl` last-wins in every field; scalar `commit` → `commits` array. Migrate once (keeps backup):
```bash
cp .claude/clio/index.jsonl .claude/clio/index.jsonl.pre2
jq -s -c 'group_by(.doc)[] | last + {files:(map(.files[]?)|unique), keywords:(map(.keywords[]?)|unique),
  commits:([.[] | .commit, .commits[]?] | map(values) | unique)} | del(.commit)' \
  .claude/clio/index.jsonl.pre2 > .claude/clio/index.jsonl
```
- `validate.sh` checks enums, types, `spec-blocked` blocker, debt rows.
- New `test.sh`.
- README rewrite.

## 1.1.0 — 2026-09-09

- New `/clio:plan <area>`.
- `clio:context` two depths: hop 0 overview, hops 1–3 for a target.
- Setup drafts `CLAUDE.md` / `CONTEXT.md`, asks before writing.
- Fixed: BSD `sed -i`, `validate.sh` req match, permission rule.

## 1.0.2 — 2026-09-08

- Skills renamed (`/clio:memo`, …).
- Setup keeps existing `CLAUDE.md`.

## 1.0.1 — 2026-09-08

- Setup tooling step.

## 1.0.0 — 2026-09-08

First release as Claude Code plugin.
