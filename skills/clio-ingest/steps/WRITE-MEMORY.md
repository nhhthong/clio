# Step 2 — Write `.claude/docs/specs/memory/*.md`

One file per area agreed in step 1. **Final decisions only, shortest unambiguous form.** No
implementation history — that lives in `docs/tasks/`, `docs/decisions/` and `clio/debt.jsonl`.

```markdown
# <Area>

## Decisions
- <One decision per bullet, stated so a future session applies it without re-deriving it.>
- <Numbers, limits and defaults exactly as the source states them — never rounded, never inferred.>

## Open — ⚠️
- ⚠️ <what is undecided, stated as a question> — owed by <who>, since <YYYY-MM-DD>

## Source
> <verbatim quote from the origin>
— <source file/section, date>
```

**Rules that keep this layer trustworthy:**

- **Never invent a decision to make a section look complete.** Source is silent or contradicts
  itself → `⚠️` naming exactly what is missing and who owes it. A short file full of ⚠️ is a correct
  file.
- Quote verbatim in `## Source`, with a date. A paraphrase loses the wording a later dispute turns on.
- A number in `## Decisions` must appear in the quoted source. Cannot find it → it is a ⚠️.
- Source says two different things in two places → do not pick the newer one. Record both under
  `## Open`, and ask the user.
- Re-ingest of an existing file: append new decisions, keep old ones, and resolve a ⚠️ only when the
  source now answers it. Deleting a still-open ⚠️ is the one unrecoverable mistake here.

Every `⚠️` written in this step needs a matching `debt.jsonl` record with `kind:"spec-blocked"` —
write them at the end of step 3, once row numbers exist.

Next: `WRITE-INDEX.md`.
