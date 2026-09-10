---
name: context
description: Load the spec, prior task docs and open debt for an area before working in it. Use before any non-trivial task, and when the user asks "where are we", "what's next", "why is X like this" or "any history on this".
argument-hint: "[area | requirements row | debt id | question — omit for the overview]"
---

# Related Context

Target (may be empty): $ARGUMENTS

**Two depths.** The *user* asked "where are we / what's next / continue" with no area named →
[HOP0.md](HOP0.md): counts from the plans and ledgers, nothing opened, ≤ 10 lines, stop. Anything
else — a target (area, row, debt `id`, file), a "why is X like this?" question, or **you triggered
this yourself before a task** (then the target is that task's area; an empty `$ARGUMENTS` is not a
reason for hop 0) → hops 1–3 below, then open **only** the docs those records point at and answer
with `file:line` quotes. A follow-up question in the same session
digs from where the last hop stopped; never re-run hop 0, never fall back to reading `.claude/docs/`
whole. Nothing on record → say so; do not reconstruct an answer from the code.

Three things decide whether a change is correct: what the customer asked for (`.claude/docs/specs/`),
what was already built and why (`.claude/docs/tasks/`, `.claude/docs/decisions/`), and what is known
broken/undecided (`.claude/clio/debt.jsonl`). This skill loads all three cheaply, in that order,
without reading the whole archive.

**Read-only.** Never writes to `index.jsonl`/`debt.jsonl`, never edits a spec, never fixes a stale
record — it *reports* contradictions; `/clio:memo` and `/clio:update` are the writers. Staying
silent because "nothing was actionable" is the failure mode.

## Walk the hops, in order

Each hop feeds the next — don't skip ahead, and don't stop after hop 1 just because it looks decided.

1. **The requirement** → [HOP1.md](HOP1.md). Read `requirements.md`, resolve the status marker for your
   row. ⚠️/❌ defaults to stop-and-ask; a specific `debt.jsonl` record (hop 3) can override that for
   the exact piece it covers.
2. **What was already built** → [HOP2.md](HOP2.md). Query `index.jsonl` for prior docs on this row/
   file/area — the last record per doc is its full current state, earlier ones are the timeline.
3. **What's still open** → [HOP3.md](HOP3.md). Query `debt.jsonl`. `blocked_by` is the only field
   that decides whether you may act on it.
4. **Coverage** — nothing stores this, it's derived: hop 1's row number joined against hops 2 and 3
   tells you what's built vs what's still owed. ✅ row + no index record + no open debt = decided but
   unbuilt, worth a sentence in your report.

## Report — including what looks wrong

Summarise: governing spec + status, prior docs worth knowing, open debt in this area, the plan's
next task and its test. A question ("why X?", "what is `<id>`?") is answered from the section the
record names — task doc `## Decisions` / `## Side Effects` / `## Follow-up`, ADR `## Decision` /
`## Consequences`, debt `what` / `action` / `blocked_by` — quoted, with the path. Then flag
plainly, without fixing:
- a debt item whose `blocked_by` names a spec that hop 1 shows is already decided — should be
  unblocked or closed;
- a ⚠️/❌ row from hop 1 that no `debt.jsonl` record tracks;
- a doc whose `## Decisions` contradicts the current spec, or describes reverted code;
- a ✅ row with no document record — ✅ means decided, not built, so this is "nothing implements it
  yet" or a missing index record, not evidence the ✅ is wrong;
- an `req`/`specs` tag that doesn't survive reading the doc — a wrong `req` on a ⚠️ row is the
  expensive one, it makes this skill send you to ask about something already settled.

`/clio:memo` writes the corrections at the end of the session; skip it and the finding is lost.

## If nothing matches

Say so in one line, continue — don't fall back to reading all of `.claude/docs/`. "No task doc
matched" ≠ "no context": hop 1 is independent of hop 2, and a spec row with no implementation
history is exactly where reading the spec matters most.
