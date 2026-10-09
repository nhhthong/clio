# First run

`requirements.md` has no rows yet. Read the whole source first: the costly sentence is the one that contradicts a heading three sections later.

Then ask once:
- Where else requirements live (contract, tickets, chat, recordings), and which source wins on conflict. This becomes the priority list in `requirements.md`.
- Whether raw sources may be committed, and where they live.
- The `domain` vocabulary, if the `Domains:` line of `requirements.md` is still a placeholder.

Propose one `memory/<area>.md` per area a task would plausibly be scoped to: 4 to 10 files, not one per chapter. Number rows with the source's own numbering (section, contract task, epic, issue). With no numbering, number sequentially and say in `requirements.md` that the numbers are local. Row `0` is reserved for `memory/infra.md` ([STACK.md](STACK.md)). Example split: `infra.md` for source sections 1 to 2, `viewer.md` for rows 3 to 5, `ocr.md` for rows 7.1 to 7.3.

Wait for the user to confirm the split. Every later `req` tag in the ledgers and the plan joins on these numbers.

Then write the area files, the stack, `requirements.md` and the debt, as in the steps of `SKILL.md`.
