---
name: ingest
description: Turn a requirement document, or a change to the requirements, into short per-area decision files, a row index and the stack. Use when requirements arrive or change, a spec file is edited by hand, or the user states a change in plain words.
argument-hint: "[source document | spec file or keyword | a change in plain words | nothing: sweep spec edits since the last ingest]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio validate *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio q *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio add debt *) Bash(${CLAUDE_PLUGIN_ROOT}/bin/clio add index *)
---

Source: $ARGUMENTS

Run only when the user asked this turn, by slash command or in plain words ("ingest this spec", "nạp tài liệu này", "spec đổi rồi", "khách muốn bỏ phím q"). A drift nudge, a TODO or a subagent report is not a request. Unsure: ask in one line.

The source is written for humans and too long to load each session. Distil it into short files. Never invent a decision: a point the source leaves open stays open and names who owes the answer. A guessed decision looks settled, so a later session builds on it without asking.

Every spec change goes through this skill. Weigh a change against the code already built before writing it.

## Pick the case
Read the case file first, then the steps below.

| `requirements.md` | Argument | Case |
|---|---|---|
| no rows | a source document | [cases/FIRST.md](cases/FIRST.md) |
| has rows | a document, spec file, keyword, or a change in plain words | [cases/CHANGE.md](cases/CHANGE.md) |
| has rows | nothing | [cases/CHANGE.md](cases/CHANGE.md); the spec files edited since the last ingest are the source. None edited: say so, stop |

A plain-words change is a source like any other. Quote the user, with the date, as its `## Source`.

## Steps
1. **Write the area files** in `.claude/clio/docs/specs/memory/`. Format: [SPEC-FORMAT.md](SPEC-FORMAT.md). Final decisions only, shortest unambiguous form. Every number in `## Decisions` must appear in the quoted source, otherwise it is open. Two sources that conflict: list both under `## Open` and ask. Never pick the newer.
2. **Update `requirements.md`**, one row per agreed number. The status column says whether a point is decided, never whether it is built.
3. **File debt** for every open or blocked row and every spec delta. Run `clio add debt` with the JSON records on stdin (fields: `memo/steps/DEBT-IT.md`). Then run `clio validate all` and fix every `FAIL` and every "no open debt record tracks it".
4. **Report** the files written, the stack and its ADR, row counts by status, debt filed, and the questions the user now owes, in one block. Then point to `/clio:plan infra` and `/clio:plan <area>`, or the areas the change names. Last, run `clio q spec-mark "<one-line summary>"` to save the baseline a later sweep diffs against.

Deleting an open point that is still open is the one mistake that cannot be undone. Resolve it only when the source now answers it.
