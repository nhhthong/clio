# Requirements — row → spec file index

Distilled requirement specs, final decisions only. **Starting a task whose context is ambiguous:
find the matching row below, read the mapped file(s) under `memory/`. No row, or a row marked
⚠️/❌: ask the user before implementing.**

Raw sources (<contract, Q&A, meeting notes…>) live at `<path>` (<committed / local-only>). Each
`memory/*.md` quotes its source verbatim in `## Source`.

**Source priority — highest first** (<adapt; the top entry must be the LIVE decision channel>):
1. `memory/<live-channel>.md` — outranks every other file; its open items can re-open a settled point.
2. <signed-off Q&A / accepted tickets>
3. The other `memory/*.md` files.
4. <original estimate / contract scope> — loses to anything above.

**On conflict, ask the user — never assume the newest source wins.** Once decided, delete the losing
version (git history keeps it).

**The status column answers only "has this been decided?", never "is it built?"** — build state is
`.claude/clio/index.jsonl`, open items `.claude/clio/debt.jsonl`, both joined on `req` = row `#`.

## By requirement number

| # | Task | Spec file(s) | Decision status (NOT build status) |
|---|------|--------------|-------------|
| 1 | <requirement> | [memory/<file>.md](memory/<file>.md) | ✅ |
| 2 | <requirement> | [memory/<file>.md](memory/<file>.md) | ⚠️ <what is still open, + date> |
| 3 | <requirement> | [memory/<file>.md](memory/<file>.md) | ❌ <what is blocking, + who owes it> |

## By topic keyword

| Task mentions | Read |
|---|---|
| <keyword> / <keyword> | memory/<file>.md |
