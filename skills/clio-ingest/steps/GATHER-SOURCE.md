# Step 1 — Read the source, agree the split

**Read the source document in full.** It is long; that is the point of this command. Do not skim to
the headings — the expensive content is the sentence that contradicts a heading three sections later.

**ASK the user, don't guess:**
- Where requirements live besides this file (contract, tickets, chat, meeting recordings), and
  **which source wins on conflict**. This becomes the priority list in `requirements.md`.
- Whether the raw sources may be committed, and where they live.
- The `domain` vocabulary for this project — the same controlled list `index.jsonl` and
  `debt.jsonl` use. Propose one from the source's own structure, let the user correct it.

## Split into domain areas

One `memory/*.md` per area a task would plausibly be scoped to — not per source chapter. Aim for
4–10 files; a file nobody would open on its own is too small, a file covering two unrelated areas
is too big.

Propose the split and the row numbering **before writing any file**, in one message:

```
memory/viewer.md    ← source §3–5      rows 3–5
memory/ocr.md       ← source §7        rows 7.1–7.3
memory/privacy.md   ← source §9–10     rows 9–10
```

`req` row numbers come from the source's own numbering (section, contract task, epic, issue). Source
has no numbering → say so, number the rows sequentially, and record in `requirements.md` that the numbers
are local to this file.

Wait for the user's confirmation on the split. Getting it wrong is expensive: every later `req` tag
in both ledgers joins on these numbers.

Next: `WRITE-MEMORY.md`.
