---
name: ingest
description: Turn a long requirement document (contract, PRD, spec.md, ticket export) into the distilled spec layer — one .claude/docs/specs/memory/*.md per domain area plus the requirements.md row table — marking every undecided point ⚠️ instead of inventing an answer. Run once after /clio:setup when the project has a requirement source, and again whenever a new source arrives.
argument-hint: "[path to the source requirement doc, or a keyword to re-ingest one area]"
disable-model-invocation: true
---

The source is written for humans and far too long to load every session. This skill distils it once
into short per-domain files an agent can read, and an index mapping requirement rows onto them.
**It never invents a decision.** A point the source leaves open becomes ⚠️ with the name of whoever
owes the answer.

Source (may be empty — then ask): $ARGUMENTS

## 1. Read the source, agree the split

Read the whole document. The expensive content is the sentence that contradicts a heading three
sections later. Then **ASK**, in one batch:
- Where else requirements live (contract, tickets, chat, recordings) and **which source wins on
  conflict** — this becomes the priority list in `requirements.md`.
- Whether raw sources may be committed, and where they live.
- The `domain` vocabulary if `CLAUDE.md` does not have one yet.

Propose one `memory/<area>.md` per area a task would plausibly be scoped to — 4–10 files, not one
per chapter — with row numbers from the source's own numbering (section, contract task, epic,
issue). No numbering → number sequentially and say in `requirements.md` that the numbers are local.

```
memory/viewer.md    ← source §3–5      rows 3–5
memory/ocr.md       ← source §7        rows 7.1–7.3
```
**Wait for the user's confirmation.** Every later `req` tag in both ledgers joins on these numbers.

## 2. Write `.claude/docs/specs/memory/*.md`

Final decisions only, shortest unambiguous form, no implementation history.

```markdown
# <Area>

## Decisions
- <One decision per bullet, stated so a future session applies it without re-deriving it.>
- <Numbers, limits, defaults exactly as the source states them — never rounded, never inferred.>

## Open — ⚠️
- ⚠️ <what is undecided, as a question> — owed by <who>, since <YYYY-MM-DD>

## Source
> <verbatim quote>
— <source file/section, date>
```
- Source silent or self-contradicting → ⚠️ naming exactly what is missing and who owes it. A short
  file full of ⚠️ is a correct file. Two conflicting statements → record both under `## Open`, ask;
  never pick the newer one.
- A number in `## Decisions` must appear in the quoted source; otherwise it is a ⚠️.
- Re-ingest: append new decisions, keep old ones, resolve a ⚠️ only when the source now answers
  it. Deleting a still-open ⚠️ is the one unrecoverable mistake here.

## 3. Write `.claude/docs/specs/requirements.md`

Its status column answers only "has this been decided?", never "is it built?".

| # | Task | Spec file(s) | Decision status (NOT build status) |
|---|------|--------------|-------------|
| 3 | <requirement, one line> | [memory/viewer.md](memory/viewer.md) | ✅ |
| 7.1 | <requirement> | [memory/ocr.md](memory/ocr.md) | ⚠️ <what is open, + date> |
| 11 | <requirement> | [memory/batch.md](memory/batch.md) | ❌ <what blocks it, + who owes it> |

One row per number agreed in step 1; dotted numbers (`7.1`) are fine, dotted *ranges* are not.
Fill `## By topic keyword` with the words a task would actually use ("ocr", "hotkey", "exif") → file.
Fill the source-priority list; the top entry is the live decision channel.

## 4. File every ⚠️/❌ row as debt

Each open point needs a record, or `clio:context` keeps stopping future sessions with nothing
explaining why. Schema and validation → `${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/DEBT-IT.md`.
```bash
echo '{"date":"YYYY-MM-DD","id":"<kebab-key>","kind":"spec-blocked","status":"pending","domain":"<domain>","what":["<what is undecided>"],"req":[7.1],"specs":[".claude/docs/specs/memory/ocr.md"],"docs":[],"code":[],"action":"<what unblocks it>","source":"<source §n>","blocked_by":"<who owes what>","issue":null}' >> .claude/clio/debt.jsonl
"${CLAUDE_PLUGIN_ROOT}"/skills/memo/scripts/validate.sh all
```
Fix every `FAIL` and every "no open debt record tracks it" before reporting.

## 5. Report

Files written, row count, how many ✅ / ⚠️ / ❌, debt records filed, and — most useful — **the list
of questions the user now owes an answer to**, in one block they can act on.
