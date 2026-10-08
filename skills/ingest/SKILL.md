---
name: ingest
description: The only writer of the spec layer — turns a requirement document into short per-area decision files, a row index and the stack (row 0), marking every undecided point ⚠️; on every later change, a new document, a hand edit or a change said in plain words, it shows what the change would invalidate before writing anything. Run when requirements arrive or change.
argument-hint: "[source document | spec file or keyword | a change in plain words | nothing: sweep spec edits since the last ingest]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio validate *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio q *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio add debt *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio add index *)
---

**Run only when the user asked, this turn** — by slash command or in plain words ("ingest this spec", "nạp tài liệu này", "spec đổi rồi", "khách muốn bỏ phím q"). Not triggers: the drift nudge, your sense that work looks finished, a TODO, a subagent's report, an earlier plan. Unsure → ask in one line, don't run.

The source is written for humans and too long to load every session. This skill distils it into short per-area files and a row index. **It never invents a decision**: a point the source leaves open becomes ⚠️ naming whoever owes the answer. Every spec change goes through here, so a change is also weighed against the code already built — before it is written. `clio` = `${CLAUDE_PLUGIN_ROOT}/bin/clio`, full path every call. Source: $ARGUMENTS

| `requirements.md` | Argument | Read first, then §§ 1–4 |
|---|---|---|
| no rows yet | a source document | [cases/FIRST.md](cases/FIRST.md) |
| rows exist | a document, spec file, keyword, or a change in plain words ("bỏ phím q") | [cases/CHANGE.md](cases/CHANGE.md) |
| rows exist | nothing | [cases/CHANGE.md](cases/CHANGE.md), the spec files edited since the last ingest being the source; none edited → say so, stop |

A plain-words change is a source like any other: quote the user, dated, as its `## Source`.

## 1. `.claude/clio/docs/specs/memory/*.md`
Final decisions only, shortest unambiguous form, no implementation history.
```markdown
# <Area>
## Decisions
- <One decision per bullet, stated so a future session applies it without re-deriving it. Numbers, limits, defaults exactly as the source states them.>
## Open — ⚠️
- ⚠️ <what is undecided, as a question> — owed by <who>, since <YYYY-MM-DD>
## Source
> <verbatim quote>
— <source file/section, date>
```
- Source silent or self-contradicting → ⚠️ naming what is missing and who owes it; a short file full of ⚠️ is correct. Two conflicting statements → both under `## Open`, ask; never pick the newer.
- A number in `## Decisions` must appear in the quoted source, else it is a ⚠️.
- Later: append new decisions, mark a reversed one `Superseded YYYY-MM-DD: now <new>`, resolve a ⚠️ only when the source now answers it. Deleting a still-open ⚠️ is the one unrecoverable mistake.

## 2. `.claude/clio/docs/specs/requirements.md`
The status column answers only "has this been decided?", never "is it built?".

| # | Task | Spec file(s) | Decision status (NOT build status) |
|---|------|--------------|-------------|
| 0 | Stack and scaffold | [memory/infra.md](memory/infra.md) | ✅ ADR <ts>_stack |
| 7.1 | <requirement> | [memory/ocr.md](memory/ocr.md) | ⚠️ <what is open, + date> |
| 11 | <requirement> | [memory/batch.md](memory/batch.md) | ❌ <what blocks it, + who owes it> |

One row per agreed number (dotted `7.1` fine, dotted *ranges* not). `## By topic keyword`: the words a task would use → file. The source-priority list: its top entry is the live decision channel.

## 3. Every ⚠️/❌ row and every delta becomes debt
Or `clio:context` keeps stopping future sessions with nothing explaining why. Schema: `memo/steps/DEBT-IT.md`. One command writes, checks, and takes back a refused record; then audit once:
```bash
clio add debt <<'EOF'
{"id":"<kebab-key>","kind":"spec-blocked","domain":"<domain>","what":["<what is undecided>"],"req":["7.1"],"specs":[".claude/clio/docs/specs/memory/ocr.md"],"action":"<what unblocks it>","source":"<source §n>","blocked_by":"<who owes what>"}
EOF
clio validate all
```
Fix every `FAIL` and every "no open debt record tracks it" before reporting.

## 4. Report, then the baseline
Files written · the stack and its ADR · row count, ✅ / ⚠️ / ❌ · debt filed · and, most useful, **the questions the user now owes an answer to**, in one block. A change adds what `cases/CHANGE.md` § Report lists. Then `/clio:plan infra` and `/clio:plan <area>` (first run), or the areas the change names. Last, the baseline a sweep diffs against (a snapshot of the spec files under the local, unpushed ref `refs/clio/ingest`), with this report's one-line summary:
```bash
clio q spec-mark "<the one-line summary>"
```
