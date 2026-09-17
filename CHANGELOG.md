# Changelog

## 3.0.0 — 2026-09-17

**Breaking: task docs move into a directory per feature, and `index.jsonl` keys on `id`.**
`/clio:audit` migrates an existing `.claude/`; nothing forces you to — a flat pre-3.0 doc still
resolves, and `validate.sh` names it without failing on it.

- **One directory per feature, one doc per sub-task.** `.claude/docs/tasks/<feature>/<id>_<name>.md`,
  plus an optional `summary.md` holding only what `ls` cannot say. A long-lived feature used to be
  one doc that grew every run, and `HOP2.md` told the reader to "read the load-bearing sections"
  without giving a command for it — so the whole file got opened. Now `ls` on either level is a free
  table of contents, and hop 2 ships the `sed` range that reads `## Decisions` / `## Side Effects` /
  `## Follow-up` alone.
- **`id` replaces `doc` as the ledger's key.** `id` is the doc's creation timestamp (`date +%s`) and
  its filename prefix; it never changes, so a moved or renamed doc keeps its history without the
  `supersedes` chain a path key needed. `validate.sh` enforces the binding — an `id` that is not the
  filename prefix is a FAIL, which is what keeps one id bound to one doc — under `docs/tasks/` and
  `docs/decisions/` only, since a ledger also indexes spec and `rules/` files, which are named by
  content and which `/clio:audit` gives an id without moving. Grouping bridges the migration: a path
  maps to the id that later claimed it, by `doc` or by `supersedes`, so a document's pre-3.0 records
  land in the same group as the record that completed them and a finished migration stops reporting
  itself as pending.
- **`plan_tasks` joins a doc to its plan rows.** `GATHER-FACTS.md` used to say "note the plan task
  id" with no way to find it and `<area>` left as a placeholder to guess; `DEBT-IT.md` § 2 then
  ticked `[x]` off that guess. Both steps now carry the command — plan ids are `<row>.<n>`, so the
  requirement row already found is enough — and `/clio:memo 3.3` resolves the doc through the field.
  An array for the same reason `req` is: a doc written before the one-doc-per-sub-task split covers
  a whole range of tasks. Unsure → leave the id out, because a wrong one ticks a row nobody tested;
  `validate.sh` rejects an id no plan table holds.
- **New: `/clio:audit`.** Reads all of `.claude/` — not just the ledgers — and brings its layout to
  the plugin's version: moves flat docs, assigns ids, appends full records where an old one is short,
  strips leftover HTML comments, and lifts a build checklist out of `requirements.md` into
  `docs/plans/<area>.md`. That last one is common in any repo set up before `/clio:plan` existed:
  `requirements.md` states that its status column never answers "is it built?" and then carries a
  phase-by-phase tick list anyway. Where the bullets carry the two markers Clio's own template
  produces — `Test:` and `Verified <date>:` — the checklist is **split**: the task, its test and its
  tick become a `/clio:plan` table row, and the verification prose is appended to the matching task
  doc's `## Testing Done`. Nothing is reworded or dropped either way. Leaving it as one blob is what
  made it unusable: 16 tasks came to 205 lines in a real repo, so "which task are we on?" paid for
  every verification paragraph in the area. A checklist without those markers moves verbatim and the
  report says which areas were split and which were not. The doc a bullet's prose belongs to is
  stated in prose, never in a field, so audit proposes the mapping and asks — and writes
  `plan_tasks` from the same answer.
  Dry-run unless `--fix`, which refuses to start unless `git status --porcelain .claude/` is clean,
  prints every change and asks once before writing. It never edits a ledger line (migration is an
  append), never invents a fact, and never re-implements `validate.sh` — it runs it. Ids for old docs
  come from `git log --diff-filter=A`, falling back to the filename date with a one-second bump per
  collision, and the run stops rather than shifting ids if duplicates survive.
- **`.claude/clio/VERSION`.** One line naming the layout version. Once migrations are idempotent a
  migrated repo and a fresh one are indistinguishable, so this is the one piece of state that cannot
  be derived.
- **The five writing skills are model-invocable again.** `disable-model-invocation: true` blocked
  them even when the user asked in plain words, since the flag cannot tell "the user said record
  this" from "the model decided to". Each skill now carries the distinction as a precondition that
  names the false triggers by name — the drift nudge, a TODO you wrote, a subagent's report, your own
  sense that the work looks done. `clio-nudge.sh` says outright that it is not permission to run.
- **`validate.sh` checks `plan_tasks` against the plan tables**, the way it already checked `req`
  against `requirements.md`. Without it the one field `/clio:memo` ticks a plan row from was the one
  field nothing verified. No plan file in the repo → nothing to check against, and the field passes.
- **`clio:context` hop 0 no longer assumes the plan is a table.** Its one-liner ended
  `cut -d'|' -f2,3,5`, so on a plan `/clio:audit` had just lifted out of `requirements.md` — still
  bullets until it is re-planned — the "next task" line printed the whole matched bullet instead of
  the task and its test. It now picks the shape per file. The counts are fixed by the split above
  rather than here: on a verbatim dump they are wrong too, since a note reading *"This row stays
  `[x]`"* counts as a finished task — a real repo reported `done=15` with 14 tasks ticked.
- **A rename no longer leaves dead references behind.** `.doc` and `.specs` are fields and follow
  the record; a path written into a sentence does not, and nothing checked those — one migration of a
  real repo left nine references across `CLAUDE.md` and two task docs still reading
  `docs/decisions/2026-09-15_…`. `/clio:audit` now rewrites every occurrence when it moves a file
  (an exact string swap, no judgement), and `validate.sh` warns `dead link in a document: <path>`
  for any reference with no file behind it. Markdown only — a ledger is append-only, so its older
  records name the old path on purpose.
- **`/clio:audit` writes a `summary.md` for every feature directory**, and the step says outright
  that it is never skipped — the first run of the migration created the directories and forgot it,
  which is the whole reason a feature directory beats a flat list. It fills only what is derivable:
  the domain from the records, the plan and spec paths that exist, and the ADRs the docs in that
  directory link to, by grep. `What this is` stays unwritten and says so rather than inventing a
  description of work nobody read.
- **`validate.sh`: the orphan check is recursive.** Its glob was `docs/tasks/*.md`, which would have
  made every 3.0 task doc invisible to the one check that exists to catch a skipped `/clio:memo`.
  `summary.md` is exempt — it is feature blurb, never an indexed doc.
- **`INDEX-IT.md` prints the existing keyword vocabulary before you pick one.** `keywords` had no
  controlled vocabulary, so `loyalty` / `loyalty-program` / one-off variants accumulated and hop 2's
  exact-match search quietly stopped finding things. No new file to keep in sync: the vocabulary is
  `jq -s -r 'group_by(.id // .doc)[] | last | .keywords[]?' index.jsonl | sort | uniq -c`, which
  cannot drift because it *is* the ledger. Prevention only — a validator rule was tried and dropped:
  keywords are per-doc by design, so "only one doc uses it" fires on most of a real ledger, and
  `wails` vs `wails-ipc` is not something a string comparison can tell from a variant spelling.
- `/clio:setup` writes `.claude/.gitattributes` with `clio/*.jsonl merge=union` when you choose to
  commit `.claude/`, so two branches appending records stop colliding. The limit is stated where it
  is written: union keeps both sides but does not order them, and readers take the last line per key.
- **Removed the shipped stack-rule starters** (`skills/setup/rules/{php,go,java,dart}.md`).
  `/clio:setup` step 4 already had to verify every seeded bullet against the repo, then write one
  from scratch for any stack the four did not cover — which was JS/TS, Python, Rust, Ruby, C# and the
  rest. Step 4 now takes that path for every stack: read the manifest, the formatter config, the
  generator output actually on disk, and 2–3 existing files, and write only bullets this repo shows.
  A rule the whole ecosystem agrees with but this repo does not demonstrate belongs in `CLAUDE.md`
  § Rules, which is the user's to state. Step 1's detection widened to match.
- **Removed CI** (`.github/workflows/ci.yml`) and the README build badge. The plugin is one
  person's, not promoted, and a workflow that only ever ran two shell scripts was a moving part to
  keep alive rather than a safety net. What it checked beyond those scripts — the manifests parse,
  the hooks file they name exists, and the four places the version lives agree — moved into
  `skills/memo/scripts/test.sh`, so nothing is lost as long as that is run before tagging.
  `CONTRIBUTING.md` now says outright that nothing runs the tests for you.
- Removed `skills/setup/permissions.json` — orphaned since 2.1.0 dropped the settings merge from
  setup; nothing read it. Claude Code's `/fewer-permission-prompts` scopes an allowlist from your own
  transcripts instead.
- Removed the `update` field from `index.jsonl`. It was written on every run and read by nothing, and
  it restated what the ledger already shows: a doc with more than one record has been updated.
  Records that still carry it are ignored, not rejected.

## 2.1.0 — 2026-09-14

- **New: a drift nudge.** `hooks/clio-nudge.sh` runs on `UserPromptSubmit` and, at most once per
  session, tells Claude to mention that `/clio:memo` is owed — when the working tree has
  uncommitted changes (a never-added new file counts), or `HEAD` appears in no `index.jsonl` record. It reads git and `index.jsonl` only:
  it writes no ledger, invokes no skill, and stays silent in a repo with no `.claude/clio/`, in one
  whose `index.jsonl` is still empty, and whose only changes are under `.claude/` (memo's own
  output). Covered by `hooks/test-nudge.sh`. Skipping `/clio:memo` is still allowed — it is now
  visible instead of silent.
- **`/clio:setup` writes only under `.claude/`.** Step 5 no longer installs anything: the MCP
  servers, the plugins and the permissions merge into `~/.claude/settings.json` are gone from
  setup, along with the per-repo ponytail/caveman switches. None of them is something Clio needs;
  they serve rules the template `CLAUDE.md` states, and the README now lists each with the one
  command that adds it. Batch 3 keeps its two in-repo choices — commit `.claude/` or ignore the
  ledgers, and the formatter hook. Two gaps that predate 2.1: the "ignore `.claude/`" choice
  now says what happens (setup prints the two `.gitignore` lines — the file is outside `.claude/`,
  so the user adds them), and the greenfield `doc-stale` record is given as a full 14-field line
  with a `validate.sh debt` after it, where the old five-field sketch produced a line step 7
  rejected for missing `id` and `status`.
- **`skills/memo/scripts/test.sh` is back in the repository** — 2.0.1 deleted it and added it to
  `.gitignore` while `CONTRIBUTING.md` still told contributors to run it, so nobody outside this
  machine could verify `validate.sh`. It now also covers the group-aware `spec-blocked` check in
  `debt` mode, which shipped in 2.0.1 untested.
- **CI.** `.github/workflows/ci.yml` runs both test scripts on every push and PR, checks the
  manifests parse and that the hooks file they name exists, and fails when `plugin.json`,
  `marketplace.json`, the README badge and the `CHANGELOG.md` heading disagree about the version.
- **`validate.sh`: the `spec-blocked` rule is one check in one place again.** 2.0.1 added a
  second, approximate copy inside `check_debt_line`, so `all` reported a wrongly-filed record
  twice while `debt` mode still missed the case where a later record supplies the blocker the
  filing record lacked. Both modes now run the same group-aware check — `debt` for the id it just
  appended, `all` for every id — and `debt` reads the ledger with `fromjson?`, so one malformed
  line no longer aborts it.
- `/clio:memo` step 1 finds the existing doc with `git diff --name-only HEAD`: without `HEAD`, a
  staged edit was invisible, so a feature with staged files got a second doc and a forked history.
- `clio:context` hop 2: a `jq: error` on a ledger is a malformed line, not an empty ledger — the
  hop now says so and points at `validate.sh all` instead of reporting "nothing on record".
- `/clio:ask` no longer says "nothing reminds you"; the nudge does, once per session.
- **`validate.sh` now checks every field the schema calls always-present** — all 14 of a debt
  record, all 9 of an index record — where before it checked 8 and 8, so a record without
  `domain` passed and then fell out of every `clio:context` query that filters on it. The write
  path (`index` / `debt` mode) refuses such a line; `all` only warns on one, naming the fields,
  because the fix under append-only is to append a full record, never to edit the old one.
- `permissions.json`: `git commit` moves from deny to ask (a human can undo a commit; a denied
  one only pushed Claude into leaving work uncommitted), and `git restore` joins the ask list — it
  discards uncommitted work and was not listed at all.
- `/clio:update` step 4 asks before flipping a row ⚠️/❌ → ✅. That flip is the one move that
  removes a stop — `clio:context` stops asking about the point — so it is now shown per row with
  its source and written only on a yes; the three moves that keep or add a stop still write
  without asking.

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
