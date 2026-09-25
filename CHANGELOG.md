# Changelog

## 4.1.0 — 2026-09-25

Breaking for the gate: **every task needs `clio-test.sh approve <task>` once** before its gate can pass
again. Show the task's case table to the user, then approve it. Nothing else to migrate. Old plans
without a `Not applicable` list stay valid.

Changes:
- **Levels chosen by risk.** `LEVELS.md` § Choosing: 13 questions (risk → question → level), when a yes
  still does not earn a level (contract for public APIs, e2e outside the key flows, perf/resilience
  with no number or behaviour in the spec). Sources: Microsoft ISE Playbook, OWASP WSTG, Pact docs.
  `/clio:plan` answers them per task.
- **New levels `idempotency`, `resilience`.** Transaction/isolation folded into `integration` and
  `concurrency`. Security cases follow OWASP WSTG (session, SSRF, uploads, business-logic replay).
- **Critical narrowed**: money, auth, deleting data, or two writers able to corrupt one record. It was
  "runs concurrently". Critical now means only "every case seen red".
- **Mutation only for tasks beyond critical**: `/clio:plan` assesses each critical task with four
  questions (wrong state that compounds? silent? hard to undo? held by hand-written logic?), not a
  list of domains — so stock drift or an oversold booking is caught like money is. It gives its
  answers as the reason and asks; the user decides. `critical` no longer implies it. Auth, deletes and races hinge on annotations, SQL constraints, config and locking,
  which a mutation tester does not mutate — their own cases prove them. Mutation runs over classes
  with logic, never with PIT `withHistory` as evidence (experimental, ignores dependency changes).
  An existing critical task whose plan row does not name `mutation` no longer needs a mutation case.
- **`Not applicable`** list under a plan table: a level whose trigger the code shows, answered no, with
  the reason. Re-plan can supersede an unticked row whose `Levels` were wrong.
- **Gate: flaky bound to the code.** A fail on the same fingerprint after a pass fails the case;
  re-running to green no longer clears it.
- **Gate: red bound to the command and the code.** A regression or critical case counts as seen red
  only when the same command failed on other code before a pass on this code.
- **Gate: approved case table.** New `clio-test.sh approve <task>` records a hash of the task's case
  rows in `runs.jsonl`; the gate fails when the rows change after it (a case deleted, Repeat lowered).
- **Gate: strict rows.** A row split by `|`, a non-numeric `Repeat`, a level outside the 15 names or a
  superseded plan row now fail instead of being read loosely. Rows inside `<!-- -->` are not read.
- **Gate: one case, one command.** Two cases of a task running the same command fail — relabelling
  one test as a second level no longer "covers" it.
- **Case table holds only cases that run.** No more `–` rows per LEVELS.md bullet that does not
  apply; a bullet whose risk the code shows, left out anyway, goes in `/clio:test`'s report with its
  reason. An old table's `–` rows still parse and are skipped.
- **Fingerprint: test artifacts are files, not directories.** A directory a run created used to be
  excluded whole, so code written into it later never voided a pass. Directory entries in older
  `runs.jsonl` lines are ignored.
- **New `hooks/clio-guard.sh` (`PreToolUse`).** Refuses Edit/Write on `runs.jsonl` and shell
  commands that write, delete or revert it (redirect, `tee`, `sed -i`, `rm`, `mv`, `cp` onto it,
  `git restore`/`checkout`) unless they go through `clio-test.sh`; reads and copies *from* it pass.
  Acts only in a repo with `.claude/clio`. Pattern match: it stops the shortcut, not a script
  opening the file itself.
- **Mutation tool asked lazily.** `/clio:plan infra` no longer asks; the first task the user agrees
  is beyond critical settles it for the project. A plan row naming `mutation` against
  `Mutation: none` now fails the gate instead of being waived.
- **Fixed: a ledger under `.claude/` could move the fingerprint.** `git rm --cached` refuses a file
  staged and then edited again (`runs.jsonl` mid-memo) without `-f`; the error was silenced, the
  staged copy stayed in the tree, and every `git add` of it voided every pass of every task.
- **Fixed:** an empty table cell shifted every cell after it; `comm` saw unsorted input under some
  locales (script now runs with `LC_ALL=C`).
- `/clio:test` says what it writes: the tests, and the least code that turns an approved case green.

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
