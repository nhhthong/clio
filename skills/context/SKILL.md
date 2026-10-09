---
name: context
description: Load the spec, prior task docs and open debt for an area before working in it. Use before any non-trivial task, and when the user asks "where are we", "what's next", "what should I do now", "which clio skill", "why is X like this" or "any history on this".
argument-hint: "[area | requirements row | task id | debt id | file | word — omit for the overview]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio q *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio validate all)
---

Target (may be empty): $ARGUMENTS

Make one call: `${CLAUDE_PLUGIN_ROOT}/bin/clio q context $ARGUMENTS` (about 50 ms). It reports the requirement rows and their spec files, what was built (the last docs' `Decisions`, `Side Effects`, `Follow-up`), the feature's shared memory, what is owed, the rules that bind the files, the plan, and a `looks wrong:` list. Several targets merge (`q context 3.5 ui`). No target prints the overview.

- **Overview** (the user asked "where are we", "what's next" or "continue", with no area): run it with no target and report in 10 lines or fewer. Give per area the done and open counts and the first open task with its levels, then debt as queue versus blocked, then the last memo. A `next:` whose `needs` are not done is not next: say what it waits on. End with the `suggest:` lines verbatim. A script computed them from the ledgers and git, and they are how a user who does not know which skill fits finds out, so do not reword them or add your own.
- **A target** (an area, row, task, debt id, file or word; or you triggered this before a task, so its area or rows): run it and answer from the report. Open a spec file or doc only when the report points at a decision you need whole. A follow-up digs from where the report stopped. Never re-run the overview, and never read `.claude/clio/docs/` whole. If nothing is on record, say so in a line and do not rebuild an answer from the code.

## Reading the report
- A row marker decides what happens next (✅ decided, ⚠️ open, ❌ blocked). Decided: build against it. Open or blocked: something is undecided, so stop and ask, naming the row. A debt record overrides the coarse marker for its own piece. `actionable now` lets you build that piece, and `BLOCKED by ...` keeps the stop. `blocked_by` is the only field that says whether you may act.
- `built` lists docs newest first. A section marked `[SUPERSEDED ...] — do not follow` is reverted work, never the pattern.
- `owed` lists actionable items first. A `code-debt` or `spec-delta` that is `actionable now` in your area is a live landmine and your work queue at once. Surface it before you start.
- `rules` bind this task. One with no `paths:` loads every session. `plan` shows each open task as `ready` or `waits on ...`, and `no cases yet` before `/clio:test`. Its cases are the success criterion.

## Report, including what looks wrong
Summarise the governing rows and their status, the docs worth knowing, the feature's memory, the area's debt, the rules and the next task. Answer a question ("why X?", "what is `<id>`?") from the section the report quotes, with the path.

Then give the `looks wrong:` list without fixing it: a debt waiting on a row that already reads decided, an open or blocked row no debt tracks, a decided row nothing implements. Add what only reading shows: a doc whose `## Decisions` contradicts the spec, or a `req` tag that does not survive reading the doc (a wrong `req` on an open row sends the next session to ask about something settled).

Never write a ledger or a spec here. `/clio:memo` and `/clio:ingest` write, and a finding nobody carries there is lost.

Field meanings, only if the report leaves one unclear: [HOP1.md](HOP1.md) (rows and markers), [HOP2.md](HOP2.md) (index records, docs), [HOP3.md](HOP3.md) (debt kinds, `blocked_by`). They also list the single queries (`clio q built|owed|history|plan|cases`).
