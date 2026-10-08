---
name: ingest
description: The only writer of the spec layer — turns a requirement document into short per-area decision files, a row index and the stack (row 0), marking every undecided point ⚠️; on every later change, a new document, a hand edit or a change said in plain words, it shows what the change would invalidate before writing anything. Run when requirements arrive or change.
argument-hint: "[source document | spec file or keyword | a change in plain words | nothing: sweep spec edits since the last ingest]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio validate *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio q *)
---

**Run only when the user asked for it, this turn** — by slash command, or in plain words ("ingest this spec", "nạp tài liệu này", "spec đổi rồi", "khách muốn bỏ phím q"). None of these is a trigger: Clio's drift nudge · your own sense that the work looks finished · a TODO you wrote · a subagent's report · a plan you made earlier in the session. Unsure → ask in one line, don't run.

The source is written for humans and far too long to load every session. This skill distils it into
short per-area files an agent can read, and an index mapping requirement rows onto them. **It never
invents a decision.** A point the source leaves open becomes ⚠️ with the name of whoever owes the
answer. Every spec change goes through here, so this is also where a change is weighed against the
code already built — before it is written.

Source: $ARGUMENTS

`clio` is `${CLAUDE_PLUGIN_ROOT}/bin/clio`; each Bash call is a fresh shell, so write the full path.

## Which run

| `requirements.md` | Argument | Read, then come back for §§ 1–4 |
|---|---|---|
| no rows yet | a source document | [cases/FIRST.md](cases/FIRST.md) |
| rows exist | a document, spec file, keyword, or a change in plain words ("bỏ phím q", "search bar lên trên") | [cases/CHANGE.md](cases/CHANGE.md) |
| rows exist | nothing | [cases/CHANGE.md](cases/CHANGE.md), the spec files edited since the last ingest as the source; nothing edited → say so, stop |

A plain-words change is a source like any other: quote the user, dated, as its `## Source`.

## 1. `.claude/clio/docs/specs/memory/*.md`

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
- A later change: append new decisions, mark a reversed one `Superseded YYYY-MM-DD: now <new>`,
  resolve a ⚠️ only when the source now answers it. Deleting a still-open ⚠️ is the one
  unrecoverable mistake.

## 2. `.claude/clio/docs/specs/requirements.md`

Its status column answers only "has this been decided?", never "is it built?".

| # | Task | Spec file(s) | Decision status (NOT build status) |
|---|------|--------------|-------------|
| 0 | Stack and scaffold | [memory/infra.md](memory/infra.md) | ✅ ADR <ts>_stack |
| 3 | <requirement, one line> | [memory/viewer.md](memory/viewer.md) | ✅ |
| 7.1 | <requirement> | [memory/ocr.md](memory/ocr.md) | ⚠️ <what is open, + date> |
| 11 | <requirement> | [memory/batch.md](memory/batch.md) | ❌ <what blocks it, + who owes it> |

One row per agreed number; dotted numbers (`7.1`) are fine, dotted *ranges* are not. Fill
`## By topic keyword` with the words a task would actually use ("ocr", "hotkey", "exif") → file.
Fill the source-priority list; the top entry is the live decision channel.

## 3. File every ⚠️/❌ row and every delta as debt

Each open point needs a record, or `clio:context` keeps stopping future sessions with nothing
explaining why. Schema → `${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/DEBT-IT.md`. Append, then validate
exactly as many records as you appended:
```bash
cat >> .claude/clio/database/debt.jsonl <<'EOF'
{"date":"YYYY-MM-DD","id":"<kebab-key>","kind":"spec-blocked","status":"pending","domain":"<domain>","what":["<what is undecided>"],"req":["7.1"],"specs":[".claude/clio/docs/specs/memory/ocr.md"],"docs":[],"code":[],"action":"<what unblocks it>","source":"<source §n>","blocked_by":"<who owes what>","issue":null}
EOF
clio validate debt <N records appended> && clio validate all
```
Fix every `FAIL` and every "no open debt record tracks it" before reporting.

## 4. Report, then take the baseline

Files written, the stack chosen (or read off the repo) and its ADR, row count, how many ✅ / ⚠️ / ❌,
debt records filed, and — most useful — **the list of questions the user now owes an answer to**, in
one block they can act on. A change adds what [cases/CHANGE.md](cases/CHANGE.md) § Report lists.
Close with the plan commands: first run → `/clio:plan infra`, then `/clio:plan <area>` per area;
later runs → the areas the change names.

Last, take the baseline a sweep diffs against — a snapshot of the spec files as this run left them,
under the local ref `refs/clio/ingest` (never pushed, never a line inside a spec file), with this
report's one-line summary:
```bash
clio q spec-mark "<the one-line summary>"
```
Its output (`Baseline: <hash>` · `Last ingest: <when> — <summary>`) is the only record of when ingest
last ran; `git log -1 refs/clio/ingest` shows it again without moving it.
