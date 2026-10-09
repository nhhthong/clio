# Hop 1: the requirement

File: `.claude/clio/docs/specs/requirements.md`.

Derive keywords from the task: business area, route path, model or table, module, feature name. `/account/orders` gives `account` and `order`. `infra/docker/entrypoint` gives `infra`. Search the file for each keyword, case-insensitive.

`requirements.md` maps requirement rows (contract tasks, epics or issue numbers, whatever `req` means in this project) and a topic-keyword table onto `memory/*.md` spec files. Read the mapped files in full. They are short and already distilled.

## Status markers decide what happens next
The markers are ✅ decided, ⚠️ open and ❌ blocked.
- Decided: build against it.
- Open or blocked: something on this row is undecided, conflicting or waiting on an answer. Default to stopping and asking. This is `requirements.md`'s own rule and outranks any inference from code. Say which row and what is unresolved.
- No row matches: say so (outside the contracted scope, or `requirements.md` lacks a row). Worth a sentence, not a reason to stop.

A row marker is coarse, and a `debt.jsonl` record is specific, so the specific one wins. An open marker means part of the row is open, not all of it. Before stopping, run [HOP3.md](HOP3.md) for that row. A record with `blocked_by: null` that covers your exact piece lets you build that piece. Say in the report which part of the row stays open and why. If no record covers it, or `blocked_by` is set, the marker stands: stop and ask. An open or blocked row with no debt record at all is a finding in its own right (see the Report section of `SKILL.md`) and still a stop.

Note the row numbers (`req`). Hop 2 reuses them, and `/clio:memo` needs them.

If the area has a plan, run `clio q summary` and read the area's `next:` line for the next ready task. Never derive it yourself from `clio q plan`, because a `needs` can name a task in a different area (`0.4` in `infra`), which only `clio q summary` resolves across all areas. Its cases (`clio q cases <task>`) are the success criterion. None yet: `/clio:test <task>` designs them before code. No plan for a decided row you are about to build: say `/clio:plan <area>` has not been run, and continue.
