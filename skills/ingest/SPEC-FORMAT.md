# Spec formats

Status markers in `requirements.md` and `## Open`: ✅ decided, ⚠️ open (a question is owed), ❌ blocked (an outside party owes it). Scripts read these three, so write them exactly.

## `memory/<area>.md`
```markdown
# <Area>
## Decisions
- <One decision per bullet, stated so a later session applies it without re-deriving it. Numbers, limits and defaults exactly as the source states them.>
## Open — ⚠️
- ⚠️ <what is undecided, as a question> — owed by <who>, since <YYYY-MM-DD>
## Source
> <verbatim quote>
— <source file and section, date>
```
A short file full of open points is correct when the source is silent. On a later run: append new decisions, mark a reversed one `Superseded YYYY-MM-DD: now <new>`.

## `requirements.md` rows
| # | Task | Spec file(s) | Decision status |
|---|------|--------------|-----------------|
| 0 | Stack and scaffold | [memory/infra.md](memory/infra.md) | ✅ ADR <ts>_stack |
| 7.1 | <requirement> | [memory/ocr.md](memory/ocr.md) | ⚠️ <what is open, date> |
| 11 | <requirement> | [memory/batch.md](memory/batch.md) | ❌ <what blocks it, who owes it> |

Dotted numbers like `7.1` are fine; dotted ranges are not. Under `## By topic keyword`, list the words a task would use and the file each leads to. The first entry of the source-priority list is the live decision channel.
