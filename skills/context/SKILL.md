---
name: context
description: Load the spec, prior task docs and open debt for an area before working in it. Use before any non-trivial task, and when the user asks "where are we", "what's next", "what should I do now", "which clio skill", "why is X like this" or "any history on this".
argument-hint: "[area | requirements row | task id | debt id | file | word — omit for the overview]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio q *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio validate all)
---

Target (may be empty): $ARGUMENTS

**One call:** `${CLAUDE_PLUGIN_ROOT}/bin/clio q context $ARGUMENTS` (~50 ms). It gives the requirement rows and their spec files, what was built (the last docs' `Decisions`, `Side Effects`, `Follow-up`), the feature's shared memory, what is owed, the rules that bind the files, the plan, and a `looks wrong:` list. Several targets merge (`q context 3.5 ui`); none prints the overview.

- **Overview** (the user asked "where are we / what's next / continue", no area): run it with no target and report in ≤ 10 lines: per area `done/open` and the first open task with its levels · debt `queue` vs `blocked` · last memo. A `next:` whose `needs` are not done is not next: say what it waits on. End with the `suggest:` lines **verbatim**: a script computed them from the ledgers and git, so do not reword them or add your own; they are how a user who does not know which skill fits finds out.
- **A target** (an area, row, task, debt id, file or word; or you triggered this before a task, then its area or rows): run it and answer from the report. Open a spec file or doc **only** when the report points at a decision you need whole. A follow-up digs from where the report stopped; never re-run the overview, never read `.claude/clio/docs/` whole. Nothing on record → say so in a line; do not rebuild an answer from the code.

## Reading the report
- **A row marker decides what happens next.** ✅ → a decision exists, build against it. ⚠️/❌ → something is undecided: stop and ask, naming the row. A debt record overrides the coarse marker for its own piece: `actionable now` lets you build that piece, `BLOCKED by …` keeps the stop. `blocked_by` is the only field that says whether you may act.
- **`built`**: docs newest first. A section marked `[SUPERSEDED …] — do not follow` is reverted work, never the pattern.
- **`owed`**: actionable first. A `code-debt` or `spec-delta` that is `actionable now` in your area is a live landmine and your work queue at once: surface it before you start.
- **`rules`** bind this task; one with no `paths:` loads every session. **`plan`** shows each open task `ready` or `waits on …`, and `no cases yet` before `/clio:test`; its cases are the success criterion.

## Report, including what looks wrong
Summarise the governing rows and status, the docs worth knowing, the feature's memory, the area's debt, the rules, the next task. A question ("why X?", "what is `<id>`?") is answered from the section the report quotes, with the path. Then the `looks wrong:` list, **without fixing it**: a debt waiting on a row that already reads ✅; a ⚠️/❌ row no debt tracks; a ✅ row nothing implements. Add what only reading shows: a doc whose `## Decisions` contradicts the spec, or a `req` tag that does not survive reading the doc (a wrong `req` on a ⚠️ row sends the next session to ask about something settled). Never write a ledger or a spec: `/clio:memo` and `/clio:ingest` write, and a finding nobody carries there is lost.

Field meanings, only if the report leaves one unclear: [HOP1.md](HOP1.md) (rows and markers), [HOP2.md](HOP2.md) (index records, docs), [HOP3.md](HOP3.md) (debt kinds, `blocked_by`); they also list the single queries (`clio q built|owed|history|plan|cases`).
