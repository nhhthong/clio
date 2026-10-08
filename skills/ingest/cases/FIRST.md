# First run — `requirements.md` has no rows yet

Read by `/clio:ingest` on the first source. Then back to `SKILL.md` §§ 1–4.

## Read the source, agree the split

Read the whole document. The expensive content is the sentence that contradicts a heading three
sections later. Then **ASK**, in one batch:
- Where else requirements live (contract, tickets, chat, recordings) and **which source wins on
  conflict** — this becomes the priority list in `requirements.md`.
- Whether raw sources may be committed, and where they live.
- The `domain` vocabulary, if the `Domains:` line of `requirements.md` is still a placeholder.

Propose one `memory/<area>.md` per area a task would plausibly be scoped to — 4–10 files, not one
per chapter — with row numbers from the source's own numbering (section, contract task, epic,
issue). No numbering → number sequentially and say in `requirements.md` that the numbers are local.
Row `0` is reserved for `memory/infra.md` ([STACK.md](STACK.md)).

```
memory/infra.md     ← source §1–2 constraints + the repo     row 0
memory/viewer.md    ← source §3–5      rows 3–5
memory/ocr.md       ← source §7        rows 7.1–7.3
```
**Wait for the user's confirmation.** Every later `req` tag in the ledgers and the plan joins on
these numbers.

Then write the area files (`SKILL.md` § 1), the stack ([STACK.md](STACK.md)), `requirements.md`
(§ 2), and the debt (§ 3).
