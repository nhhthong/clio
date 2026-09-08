# Spec Routes — requirement → spec file index

Self-contained requirement specs, distilled to final decisions. **When starting a task whose context
is ambiguous, find the matching row below and read the mapped file(s) under `memory/`. If no row
matches, or the row is marked ⚠️/❌ (undecided/pending), ask the user before implementing.**

Raw source docs (<contract, Q&A, meeting notes, PDFs…>) live at `<path>` (<committed / gitignored,
local-only>). Each `memory/*.md` cites its source verbatim in a `## Source` section; on a ⚠️/❌ point,
grep those raw files before asking — the exact wording may already resolve it.

**Source priority — highest first:** <adapt to this project; the top entry must be the LIVE decision
channel, whatever it is (customer chat, PO's issue comments, meeting recordings).>
1. `memory/<live-channel>.md` + the recordings/threads it cites — **outranks every other file**; its
   "Open items" can re-open a point another file states as settled.
2. <signed-off Q&A / accepted tickets>
3. The other `memory/*.md` files.
4. <original estimate / contract scope> — loses to anything above it.

**On conflict, do not auto-resolve — ask the user.** Never assume the newest-looking source wins.
Once the user picks, delete the losing decision from its file (git history already keeps the old
version).

**This file is an index and a decision register — it never records implementation state.** The
status column answers only *"has this been decided?"*, never *"is it built?"*:

| Question | Where |
|---|---|
| Has it been decided? | this file's status column |
| What was built against it, and when? | `.claude/clio/index.jsonl` (`req` = row #), `/clio-memo` |
| What is still owed — spec gap, code debt, untested? | `.claude/clio/debt.jsonl` (`req` = row #), `/clio-update` + `/clio-memo` |

So never read ✅ as "done", and never add a build-progress note to a row here.

## By requirement number

| # | Task | Spec file(s) | Decision status (NOT build status) |
|---|------|--------------|-------------|
| 1 | <requirement> | [memory/<file>.md](memory/<file>.md) | ✅ |
| 2 | <requirement> | [memory/<file>.md](memory/<file>.md) | ⚠️ <what exactly is still open, + date> |
| 3 | <requirement> | [memory/<file>.md](memory/<file>.md) | ❌ <what is blocking, + who owes it> |

Each `memory/*.md`: final decisions only, shortest unambiguous form, undecided points marked ⚠️ with
who owes the answer, and a `## Source` section quoting the origin verbatim with a date. No
implementation history — that lives in `docs/tasks/`, `docs/decisions/` and `clio/debt.jsonl`.

## By topic keyword

| Task mentions | Read |
|---|---|
| <keyword> / <keyword> | memory/<file>.md |
