---
name: audit
description: Check the three layers against each other — requirement rows, plan tasks and the ledgers — and name every place they have drifted apart. A spec that moved after its area was planned is the common one, and nothing else notices it. Read-only by default; --fix re-plans the areas that drifted. Run when a spec changed, or any time you want to know whether the plans still match what was decided.
argument-hint: "[--fix, optional — omit for a report]"
---

**Run only when the user asked for it, this turn** — by slash command, or in plain words ("is the
plan still right?", "check the specs against the plans"). Clio's drift nudge is about `/clio:memo`
and is not a trigger for this. Unsure → ask in one line, don't run.

Mode (may be empty): $ARGUMENTS — anything other than `--fix` is a **report**.

`requirements.md` says what was decided. `docs/plans/*.md` says how it gets built. The ledgers say
what was built and what is owed. Each is written by a different command at a different time, so they
drift, and the drift is silent: a spec row can move months after its area was planned and every later
session will read a plan that no longer matches the decision.

This skill finds that. It **writes no plan itself** — `/clio:plan` is the only writer of
`docs/plans/*.md`, and the rules for re-planning around a ticked row live there. With `--fix` this
skill runs `/clio:plan <area>` for the areas that drifted, and only those.

## 1. Read the three layers

```bash
"${CLAUDE_PLUGIN_ROOT}"/skills/memo/scripts/validate.sh all     # schema first; a FAIL here outranks any drift
awk -F'|' 'NF>4 && $2 ~ /^ *[0-9.]+ *$/ {gsub(/^ +| +$/,"",$2); print $2"\t"$5}' \
  .claude/docs/specs/requirements.md                            # row → decision marker
awk -F'|' 'NF>5 && $2 ~ /^ *[0-9.]+ *$/ {gsub(/^ +| +$/,"",$2); print FILENAME"\t"$2"\t"$4"\t"$7}' \
  .claude/docs/plans/*.md                                       # plan → id, req, Done
jq -s -c 'group_by(.id)[] | last | select(.status!="done")' .claude/clio/debt.jsonl
```
`validate.sh` FAILs → stop and report those. A malformed ledger makes every join below unreliable.

## 2. The five drifts

| What you find | What it means |
|---|---|
| Open `spec-delta` whose `id` appears in no plan file | the spec moved and no plan absorbed it — **the one this skill exists for** |
| Plan task ticked, its `req` row's marker changed date after the tick | built against a decision that has since moved |
| `requirements.md` row ✅, no plan task carries that `req` | decided, never planned |
| Plan task whose `req` matches no row in `requirements.md` | planning something no row decides |
| Plan task under a ⚠️/❌ row, with no debt `id` named on the row | planning something still undecided |
| The same task id twice in one plan file | a re-plan appended a superseded copy instead of striking the row in place; `validate.sh` FAILs on it |

The first two are the expensive ones, because work has already happened. The rest are gaps, not
mistakes, and a ✅ row with no plan is often just an area nobody has started.

`/clio:update` is what writes a `spec-delta` when a spec moves. A repo where the spec changed and
`/clio:update` never ran has no delta record to find, so say so rather than reporting it clean: a
`memory/*.md` newer than every record naming it is worth one line in the report.

## 3. Report

Per area, one block. Name the row, the task id, and the exact command that would fix it:

```text
checkout   row 12 ✅ narrowed 2026-09-17 · task 3.2 [x] 2026-09-02   built against the old decision
           spec-delta checkout-loyalty-added · in no plan            →  /clio:plan checkout
ocr        row 20 ⚠️ · plan task 4.9 exists                          →  row is undecided, ask first
product    clean
```

Nothing drifted → one line. Never propose a rewrite here; the split is `/clio:plan`'s to show and
the user's to approve.

## 4. `--fix`

Run `/clio:plan <area>` for each drifted area, one at a time, skipping the clean ones. Nothing else
changes: `/clio:plan` reads the existing file, applies its own re-plan rules — a ticked row is never
edited or unticked — shows the full table, and asks before writing. `--fix` saves you typing the
commands, not the approval.

A drift the report marked *ask first* (a ⚠️/❌ row) is **not** re-planned. An undecided row has no
task to write; it needs an answer, and `/clio:update` is what records one.

Afterwards, run this skill again: the areas you fixed must come back clean.
