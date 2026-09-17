---
name: migrate
description: Migrate .claude/ onto the layout this plugin version expects — move task docs into their feature directory, give pre-3.0 docs an id, append full records where an old one is short, strip leftover HTML comments. Dry-run by default; --fix asks before it writes anything. Run after upgrading the Clio plugin, or when validate.sh keeps naming the same old records.
argument-hint: "[--fix, optional — omit for a dry run]"
---

**Run only when the user asked for it, this turn** — by slash command, or in plain words ("tidy up
.claude", "migrate the ledgers", "dọn lại .claude"). None of these is a trigger: Clio's drift nudge ·
`validate.sh` output you saw while doing something else · a plan you made earlier in the session.
Unsure → ask in one line, don't run.

Mode (may be empty): $ARGUMENTS — anything other than `--fix` is a **dry run**.

This is the only Clio skill that writes across the whole memory layer, so it is also the only one
with a rollback story. Three rules, none of them negotiable:

1. **Never edit, reorder or delete a line in `index.jsonl` or `debt.jsonl`.** Migration is an
   **append** of a full record under the same key; readers take the last line per key. This is the
   same rule `/clio:memo` follows, and it is what makes the ledgers history rather than state.
2. **Never invent content.** You may move a file, append a record, add an empty heading and strip a
   comment. Anything that needs a *fact* you do not have — which `req` a doc serves, who owes an
   answer on a ⚠️ row, what a missing `## Testing Done` should say — is reported and asked, never
   filled in. A memory layer with invented facts is worse than one with gaps.
3. **Never re-implement `validate.sh`.** It is the diagnosis engine; this skill runs it and acts on
   what it says.

## 1. Preconditions

```bash
[ -d .claude/clio ] || { echo "no .claude/clio — run /clio:setup first"; exit 1; }
cat .claude/clio/VERSION 2>/dev/null || echo "(no VERSION — pre-3.0 layout)"
```
For `--fix` only, the working tree under `.claude/` must be clean:
```bash
git status --porcelain .claude/
```
Anything printed → **stop** and say so. Everything below is undone with
`git checkout .claude/`, and that only works if there was nothing else in there to lose. Not a git
repo → say the rollback does not exist here and ask before continuing.

## 2. Diagnose

```bash
"${CLAUDE_PLUGIN_ROOT}"/skills/memo/scripts/validate.sh all
shopt -s globstar nullglob
ls -1 .claude/docs/tasks/*.md 2>/dev/null          # flat docs — pre-3.0 layout
jq -s -r 'map(select(.id == null)) | length' .claude/clio/index.jsonl   # records with no id
```
`validate.sh` covers: malformed JSON · records missing schema fields · `.doc` pointing at a file
that is gone · orphan docs · pre-2.0 delta ledgers · leftover HTML comments · `requirements.md`
markers with no matching debt · keywords used exactly once. Add only what it cannot see: the flat-vs-
nested layout, the filename convention, and whether `VERSION` exists.

## 2b. Read the rest of `.claude/`, not just the ledgers

`validate.sh` checks records. It does not read what is *inside* the documents, and layout drift
hides there. Walk every file once:

- **`docs/specs/requirements.md` carrying build state.** Its own header says the status column
  answers "has this been decided?", never "is it built?" — so a `## Implementation tasks` section,
  a phase breakdown, tick boxes or "Verified <date>" notes in that file are in the wrong home.
  They belong in `.claude/docs/plans/<area>.md`. Common in anything set up before `/clio:plan`
  existed, and the file usually states the rule and breaks it sixty lines later.
- **`CLAUDE.md` / `CONTEXT.md`** — leftover `<!--` template instructions (`validate.sh` warns),
  task history that belongs in a task doc, path-specific bullets that belong in `rules/`.
- **`rules/*.md`** without `paths:` frontmatter: they load in every session instead of for the
  files they name.
- **`docs/specs/memory/*.md`** whose `## Open — ⚠️` points have no `debt.jsonl` record.
- **`docs/tasks/`** flat, or docs whose filename carries no id.

## 3. Classify

| Group | What it is | What you do |
|---|---|---|
| **Mechanical** | flat doc → `tasks/<feature>/<id>_<name>.md`, plus the `summary.md` that directory needs and the prose references the rename breaks · a build checklist inside `requirements.md` → `docs/plans/<area>.md` · pre-3.0 record (no `id`/`plan_tasks`) · pre-2.0 record (scalar `commit`) · debt record short of its 14 fields · HTML comments left in `CLAUDE.md`/`CONTEXT.md` · task doc missing a heading | fix, after the step 4 yes |
| **Needs a human** | a `CLAUDE.md`/`CONTEXT.md` passage the move made false — audit drafts it and writes on a yes · orphan doc (its real `req`/`files`/`commits` are not derivable) · record whose `.doc` is gone with no `supersedes` · ⚠️/❌ row with no debt record | propose, ask, never decide |
| **Report only** | ✅ row with no index record (decided-but-unbuilt is legitimate) · near-duplicate keywords | print, change nothing |

Merging keyword variants (`loyalty-program` → `loyalty`) is **never** mechanical: it is a semantic
judgement, and getting it wrong breaks the exact-match lookup in `HOP2.md`. `wails` and `wails-ipc`
look like the same mistake and are not. List what you noticed and leave it alone.

## 4. Show the whole plan, then ask once

Print every intended change — each file move as `old → new`, each record to be appended in full,
each heading to be added — then **one `AskUserQuestion`**: apply all · apply only the file moves ·
cancel. Nothing is written before that answer, and a dry run stops here regardless.

## 5. Apply

### Giving a pre-3.0 doc its `id`

`id` is the doc's creation timestamp and its filename prefix. Old docs have neither, so derive it —
**in this order**, and never from "today":

1. **The date in the old filename** (`2026-09-15_login.md` → `2026-09-15 00:00:00` local). Pre-3.0
   docs are named for the day they were created and were never renamed, so this is the creation date
   on record.
2. **No date in the name** — spec files, `rules/*.md`, anything not named by Clio — then the file's
   first commit:
   ```bash
   git log --diff-filter=A --format=%at -- "$f" | tail -1
   ```
3. Never committed → `stat -c %Y "$f"` (mtime).

Do **not** lead with the git timestamp. A `.claude/` that was copied in, cloned fresh, squashed, or
un-gitignored has one add-commit for the whole directory — on a real repo that hands every document
the same second. Checked on a 16-document ledger: the filename dates gave three distinct days, the
git timestamps gave one value for all sixteen.

**Two docs must never end up with the same `id`.** Day granularity collides by construction, so
within each colliding group order by git first-add time, then by filename, and add one second to
each after the first. Then check the whole ledger before writing anything:
```bash
jq -r '.id // empty' .claude/clio/index.jsonl | sort | uniq -d      # must print nothing
```
Still duplicated → **stop and report**; do not shift ids to make it fit.

### What moves, and what only gets an `id`

**Only `.claude/docs/tasks/*.md` moves.** A ledger also indexes things Clio did not name: spec files
under `docs/specs/memory/`, `rules/*.md`, anything else a `/clio:memo` run documented. Those keep
their path and their filename — they are named by content, the timestamp prefix means nothing for
them, and moving one would tear a hole in the spec layer. They still get an `id` so they key like
everything else; `validate.sh` applies the filename-prefix rule only under `docs/tasks/` and
`docs/decisions/`.

ADRs already sit flat in `docs/decisions/` and stay there — rename only to add the prefix.

```bash
git mv .claude/docs/tasks/2026-09-15_login.md .claude/docs/tasks/login/1789430400_login.md
```
Feature directory: kebab-case, the business area the doc serves (`WRITE-DOC.md` § Where docs live).
Not obvious from the doc → ask; do not invent a grouping.

Then append one record carrying the doc's **current full state**, copied from its own last record
plus the new `id`, `doc` and `plan_tasks`:
```bash
jq -s -c --arg d "<old path>" 'map(select(.doc==$d)) | last' .claude/clio/index.jsonl
```
Because the old records key on `doc` and the new one keys on `id`, the moved doc's old path is left
pointing at nothing — so this one record also carries `"supersedes":"<old path>"`, which is what
`validate.sh` looks for before it FAILs a record whose file is gone. Docs born at 3.0 never need it:
their `id` does not change when they move.

`plan_tasks`: fill it only with ids that `grep -n "^| <row>\." .claude/docs/plans/*.md` matches and
that the doc's own text claims. Anything less → `[]`. A doc written before `/clio:plan` existed often
covers a whole range of tasks and says so in prose; reading that range out of the prose is judgement,
so propose it and ask rather than filling it in. A wrong id makes `/clio:memo` tick a plan row nobody
tested, which is worse than an empty field.

### Moving a build checklist out of `requirements.md`

Split on the existing phase/area headings, one `.claude/docs/plans/<area>.md` per heading. Nothing is
reworded or dropped anywhere below — the notes are the only record that the work was checked, and
most of them are human verification nobody can re-derive.

A checklist Clio's own template produced carries two literal markers, and only those two are
load-bearing:

```
- [x] **1.8** Zoom: in/out buttons … (req #6, #29). Test: each control changes the rendered scale.
  Verified 2026-09-16 by the user: `+`/`-` move the percentage and the rendered size together …
      ↑ id      ↑ task text            ↑ req       ↑ Test:                ↑ Verified <date>: prose
```

**Both present → split into two destinations.** Leaving it as one blob makes the file unusable at
the hot path: 16 tasks came to 205 lines in a real repo, so "which task are we on?" pays for every
verification paragraph in the area.

| Destination | What goes there |
|---|---|
| `docs/plans/<area>.md`, `/clio:plan`'s table | `#` ← the bold id · `Task` ← text before `Test:` · `Test` ← the sentence after `Test:` · `req` ← the `(req #N)` already in the bullet · `Done` ← the `[x]`/`[ ]`/`–` exactly as it stands, plus the date the prose names · `Needs` ← `–` unless the bullet names one |
| the matching task doc's `## Testing Done` | everything from `Verified <date>:` to the end of the bullet, unchanged, dates intact |

**Either marker missing, or the section is not a bullet list → move that area verbatim and stop
there.** A checklist Clio did not write has no guarantee of this shape, and guessing where a task
ends and its verification starts is exactly the judgement this skill does not make. Say which areas
were split and which were left whole.

`/clio:plan <area>` re-lays a verbatim area into the table later, and asks before writing.

Setup tasks that precede any requirement row (toolchain, scaffold, first green build) are `/clio:plan`'s
row `0` — keep them together in one plan file rather than splitting them across areas.

### Which task doc a bullet's prose belongs to — propose, never infer

The mapping is stated in prose, not in a field: *"Split: tasks 1.8-1.12 moved to
2026-09-16_viewer-display-controls.md"*, *"content relocated verbatim, not new work"*. Reading a
range out of a sentence is judgement, so this skill reads it and then **asks**:

- list each plan id, the doc you believe owns it, and the sentence you read that from;
- one `AskUserQuestion`: accept all · accept per area · skip, and the prose stays in the plan file;
- on a yes, write `plan_tasks` on those docs in the same pass — it is the same mapping and the same
  answer, and leaving it for later means asking twice.

An id nothing claims keeps its prose in the plan file, in a `## Notes` section **below** the table,
one `### <id>` block each. Below, because everything that reads a plan cheaply — `HOP0.md`'s
counts and its "next task" line — greps the table, and prose above or inside it is what broke them:
on the verbatim dump of a real repo, hop 0 reported `done=15` where 14 tasks were ticked, because a
note reading *"This row stays `[x]`"* counted as a finished task. Never attach prose to a doc on a
resemblance.

Then: `requirements.md` keeps the row table and loses the checklist, and anything pointing at the
old location — typically a bullet in `CLAUDE.md` § Project memory telling the reader to tick items
there — now points at nothing. Draft the replacement line, show it, and ask. That pointer is the
user's text, not yours.

### Rewrite what pointed at the old path

A rename does not only move a file — it breaks every sentence that named it. `.doc` and `.specs` are
fields and follow the record; a path written into prose does not, and nothing else in Clio checks
those. On a real repo one migration left **nine** dead references across `CLAUDE.md` and two task
docs, all reading `.claude/docs/decisions/2026-09-15_…`.

For every move, replace the old path with the new one wherever it appears, across `.claude/**/*.md`
and a root `CLAUDE.md`. It is an exact string swap — no judgement, so just do it:

```bash
grep -rl '<old path>' .claude/ CLAUDE.md 2>/dev/null
```

Then confirm none is left: `validate.sh all` warns `dead link in a document: <path>` for every
reference with no file behind it.

### `CLAUDE.md` and `CONTEXT.md` — what audit may change there

Audit moved the layout, so audit fixes what described it. Two kinds, two rules:

**A path audit itself moved → rewrite it, no asking.** Covered by the step above; an exact string
swap is not an edit to the file's meaning.

**A passage whose *meaning* the move invalidated → draft it, show the diff, ask once, then write.**
A bullet reading *"Finishing a checklist item under `requirements.md` § Implementation tasks → tick
it `[x]` there"* is not a bad path — it is an instruction that is now false three ways over: the
checklist is in `docs/plans/`, `/clio:memo` does tick it, and there is no longer a second place to
tick. Rewriting that is authoring policy into a file that loads in **every** session, which is why
`/clio:setup` § 2 and `WRAP-UP.md` § CONTEXT.md gate the same two files the same way.

**Never touch, whatever the migration did:** the `## Rules` bullets, the domain vocabulary, the
`@CONTEXT.md` import line, the project description, anything under `## Architecture`. Those are the
user's, and none of them is about where Clio keeps files. Audit's licence here is exactly this wide:
the passages that describe Clio's own layout, because audit is what moved it.

### `summary.md` for every feature directory

Each `docs/tasks/<feature>/` gets one — `WRITE-DOC.md` § Where docs live requires it, and a feature
directory without one is a folder you have to open three files to understand. Create it when the
directory is created, refresh it when a doc moves in or out. **Never skip this step**; it is the
whole reason the directory beats a flat list.

Fill only what the ledger and the files already state:

```markdown
# <Feature>
Domain: <the domain its records share> · Plan: `docs/plans/<area>.md` · Spec: `docs/specs/memory/<area>.md`

## What this is
<One or two sentences. Nothing here yet → leave the heading and say "not written" — never invent a
description of work you did not read.>

## Decisions that constrain this feature
<Every `docs/decisions/*.md` the docs in this directory link to, by path, one line each. This is a
grep, not a judgement — and it is what keeps a cross-cutting ADR findable from the feature that
obeys it, without a copy of it living here.>

## History
jq -s 'group_by(.id)[] | last | select(.doc | startswith(".claude/docs/tasks/<feature>/"))' \
  .claude/clio/index.jsonl

## Cross-cutting side effects
<Only what a doc in this directory already recorded under `## Side Effects` as reaching beyond it.
Nothing → leave empty.>
```

`Domain`, `Plan`, `Spec` and the decision list are all derivable — read them off the records and the
links. `What this is` and the side effects are not: take them from what the docs say, or leave them
unwritten and say so in the report.

### Short records

A record missing schema fields is not edited — append a new one under the same key restating
everything it had plus what it lacked, with `null`/`[]` for anything genuinely unknown. Validate each
append as you go:
```bash
"${CLAUDE_PLUGIN_ROOT}"/skills/memo/scripts/validate.sh index   # or: debt
```

### VERSION

Last, once everything above is clean:
```bash
echo 3.0 > .claude/clio/VERSION
```
One line, plain text. It records the layout version this `.claude/` has been brought to — not
derivable from the files once a migration is idempotent, which is the whole reason it is stored.

## 6. Verify and report

```bash
"${CLAUDE_PLUGIN_ROOT}"/skills/memo/scripts/validate.sh all
ls .claude/docs/tasks/*/summary.md     # one per feature directory, no exceptions
git status --porcelain .claude/
```
No `dead link in a document` warning may survive — one means a rename left a sentence pointing at a
file that is gone.
Run this skill again straight away: the second run must find nothing to do. It does not, say so
plainly rather than fixing the same thing twice — a migration that is not idempotent is a bug here,
not a chore for the user.

Report: files moved (`old → new`) · records appended, by key · headings added · comments stripped ·
**everything in "needs a human", as questions the user can answer in one pass** · what `validate.sh`
still says. Nothing to do → one line.
