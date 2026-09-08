# Step 3 — Write `.claude/docs/specs/requirements.md`, then file the ⚠️ rows as debt

`requirements.md` is an index and a decision register. Its status column answers **only** "has this been
decided?" — never "is it built?".

## The row table

| # | Task | Spec file(s) | Decision status (NOT build status) |
|---|------|--------------|-------------|
| 3 | <requirement, one line> | [memory/viewer.md](memory/viewer.md) | ✅ |
| 7.1 | <requirement> | [memory/ocr.md](memory/ocr.md) | ⚠️ <what is open, + date> |
| 11 | <requirement> | [memory/batch.md](memory/batch.md) | ❌ <what blocks it, + who owes it> |

- `✅` — decided. Never means built.
- `⚠️` — part of the row is open. Name the part and the date, not just the symbol.
- `❌` — blocked on something outside the team. Name the blocker and who owes it.
- One row per `req` number agreed in step 1. Row numbers with dots (`7.1`) are fine; a dotted
  *range* is not — `validate.sh` only resolves its endpoints.

## The keyword table

Fill `## By topic keyword` with the words a task would actually be phrased in ("ocr", "hotkey",
"thumbnail", "exif"), mapped to the memory file. This is how `clio-context` hop 1 finds the row
when the task mentions no number.

## Source priority

Fill the priority list with what step 1 established. The top entry must be the **live** decision
channel, whatever it is — its open items can re-open a point another file states as settled.

## File every ⚠️/❌ row as debt

Each open point needs a record, or `clio-context` will keep stopping future sessions with no
record explaining why. Append-only, all 14 fields (schema →
`${CLAUDE_PLUGIN_ROOT}/skills/clio-memo/steps/DEBT-IT.md`):

```bash
echo '{"date":"YYYY-MM-DD","id":"<kebab-key>","kind":"spec-blocked","status":"pending","domain":"<domain>","what":["<what is undecided>"],"req":[7.1],"specs":[".claude/docs/specs/memory/ocr.md"],"docs":[],"code":[],"action":"<what unblocks it>","source":"<source file §n>","blocked_by":"<who owes what>","issue":null}' >> .claude/clio/debt.jsonl
```

## Verify before reporting done

```bash
"${CLAUDE_PLUGIN_ROOT}"/scripts/validate.sh all
```
`BAD req` / `no open debt record tracks it` → fix before finishing.

## Report

Files written, row count, how many rows are ✅ / ⚠️ / ❌, the debt records filed, and — most
important — **the list of questions the user now owes an answer to**, in one block they can act on.
