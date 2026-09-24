---
name: ingest
description: The only writer of the spec layer. First run — turn a requirement document (contract, PRD, spec.md, ticket export) into one .claude/clio/docs/specs/memory/*.md per area, the requirements.md row table, and the stack as memory/infra.md (row 0, ADR), marking every undecided point ⚠️. Every later run — a new source, or no argument to sweep spec files edited by hand — also works out what the change invalidates in code already built, files spec-delta records, moves row markers and names the areas to re-plan. Run when requirements arrive or change.
argument-hint: "[source document | spec file or keyword | nothing: sweep spec edits since the last ingest]"
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/skills/memo/scripts/validate.sh *) Bash(${CLAUDE_PLUGIN_ROOT}/skills/context/scripts/q.sh *)
---

**Run only when the user asked for it, this turn** — by slash command, or in plain words ("ingest this spec", "nạp tài liệu này", "spec đổi rồi").
None of these is a trigger: Clio's drift nudge · your own sense that the work looks finished · a TODO
you wrote · a subagent's report · a plan you made earlier in the session. Unsure → ask in one line,
don't run.

The source is written for humans and far too long to load every session. This skill distils it into
short per-area files an agent can read, and an index mapping requirement rows onto them. **It never
invents a decision.** A point the source leaves open becomes ⚠️ with the name of whoever owes the
answer. Every spec change goes through here, so this is also where a change is weighed against the
code already built.

Source: $ARGUMENTS

| Run | When | Does |
|---|---|---|
| **first** | `requirements.md` has no rows yet | §§ 1–5 |
| **re-ingest** | a source, spec file or keyword given; rows exist | § 1 for new areas and rows only, §§ 2–4 for what the source changes, § 6, § 5 |
| **sweep** | no argument; rows exist | the spec files edited since `Last ingest:` are the source: § 6, § 5. Nothing edited → say so, stop |

`Last ingest: YYYY-MM-DD <commit>` is the line under the title of `requirements.md`. Every run ends by
rewriting it — the commit is `git rev-parse --short HEAD`, empty outside git or before the first
commit. It is the before-state a sweep diffs against.

## 1. Read the source, agree the split

Read the whole document. The expensive content is the sentence that contradicts a heading three
sections later. Then **ASK**, in one batch:
- Where else requirements live (contract, tickets, chat, recordings) and **which source wins on
  conflict** — this becomes the priority list in `requirements.md`.
- Whether raw sources may be committed, and where they live.
- The `domain` vocabulary, if the `Domains:` line of `requirements.md` is still a placeholder.

Propose one `memory/<area>.md` per area a task would plausibly be scoped to — 4–10 files, not one
per chapter — with row numbers from the source's own numbering (section, contract task, epic,
issue). No numbering → number sequentially and say in `requirements.md` that the numbers are local.
Row `0` is reserved for `memory/infra.md` (§ 2b).

```
memory/infra.md     ← source §1–2 constraints + the repo     row 0
memory/viewer.md    ← source §3–5      rows 3–5
memory/ocr.md       ← source §7        rows 7.1–7.3
```
**Wait for the user's confirmation.** Every later `req` tag in both ledgers joins on these numbers.

## 2. Write `.claude/clio/docs/specs/memory/*.md`

Final decisions only, shortest unambiguous form, no implementation history.

```markdown
# <Area>

## Decisions
- <One decision per bullet, stated so a future session applies it without re-deriving it.>
- <Numbers, limits, defaults exactly as the source states them — never rounded, never inferred.>

## Open — ⚠️
- ⚠️ <what is undecided, as a question> — owed by <who>, since <YYYY-MM-DD>

## Source
> <verbatim quote>
— <source file/section, date>
```
- Source silent or self-contradicting → ⚠️ naming exactly what is missing and who owes it. A short
  file full of ⚠️ is a correct file. Two conflicting statements → record both under `## Open`, ask;
  never pick the newer one.
- A number in `## Decisions` must appear in the quoted source; otherwise it is a ⚠️.
- Re-ingest: append new decisions, mark a reversed one `Superseded YYYY-MM-DD: now <new>`, resolve a
  ⚠️ only when the source now answers it. Deleting a still-open ⚠️ is the one unrecoverable mistake.

## 2b. Propose the infra: `memory/infra.md`, row `0`

A spec says what the product must do; it rarely says what it is built with, yet every area plan needs
that settled first. This skill decides the stack **at decision level** — language, framework, build
tool, test runner, and the constraints behind them. `/clio:plan infra` later turns it into the
scaffold and toolchain tasks; it does not choose.

Collect the constraints the source states that bind the stack — platform (web, desktop, mobile),
offline, data volume, latency, hosting, licence, a stack the customer already mandates — each with its
quote. Then one of:

**The repo has code.** Read the manifests and lockfiles; the stack is whatever they pin. Propose
nothing. Write it as `## Decisions` with the exact versions, and every source constraint the current
stack does not visibly meet as a ⚠️.

**The repo is empty.** Research 2–3 candidate stacks that fit the constraints. **Prefer Context7**
(fall back to web search, say which). From each stack's own docs: the scaffold command, build and
test commands, the version they need, the layout they recommend — each with source and the date
read. Show them side by side against the constraints, then **ASK**: the user picks one or names their
own. Never pick silently. Record the choice as an ADR (`${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/WRAP-UP.md`
§ ADR, indexed with `"type":"adr"`, `"domain":"infra"`, `"req":["0"]`, then
`${CLAUDE_PLUGIN_ROOT}/skills/memo/scripts/validate.sh index`).

Scope stops at what the scaffold needs. A library for a domain — OCR, image processing, an HTTP
client — is chosen in that area's spec or plan, not here; the rows it serves are often still ⚠️.

`memory/infra.md` uses the same template; `## Decisions` holds the chosen stack and the commands
the docs gave, `## Source` quotes the constraints and names the ADR.

## 3. Write `.claude/clio/docs/specs/requirements.md`

Its status column answers only "has this been decided?", never "is it built?".

| # | Task | Spec file(s) | Decision status (NOT build status) |
|---|------|--------------|-------------|
| 0 | Stack and scaffold | [memory/infra.md](memory/infra.md) | ✅ ADR <ts>_stack |
| 3 | <requirement, one line> | [memory/viewer.md](memory/viewer.md) | ✅ |
| 7.1 | <requirement> | [memory/ocr.md](memory/ocr.md) | ⚠️ <what is open, + date> |
| 11 | <requirement> | [memory/batch.md](memory/batch.md) | ❌ <what blocks it, + who owes it> |

One row per number agreed in step 1; dotted numbers (`7.1`) are fine, dotted *ranges* are not.
Fill `## By topic keyword` with the words a task would actually use ("ocr", "hotkey", "exif") → file.
Fill the source-priority list; the top entry is the live decision channel.

## 4. File every ⚠️/❌ row as debt

Each open point needs a record, or `clio:context` keeps stopping future sessions with nothing
explaining why. Schema → `${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/DEBT-IT.md`.
```bash
cat >> .claude/clio/database/debt.jsonl <<'EOF'
{"date":"YYYY-MM-DD","id":"<kebab-key>","kind":"spec-blocked","status":"pending","domain":"<domain>","what":["<what is undecided>"],"req":["7.1"],"specs":[".claude/clio/docs/specs/memory/ocr.md"],"docs":[],"code":[],"action":"<what unblocks it>","source":"<source §n>","blocked_by":"<who owes what>","issue":null}
EOF
${CLAUDE_PLUGIN_ROOT}/skills/memo/scripts/validate.sh all
```
Fix every `FAIL` and every "no open debt record tracks it" before reporting.

## 5. Report

Files written, the stack chosen (or read off the repo) and its ADR, row count, how many ✅ / ⚠️ / ❌,
debt records filed, and — most useful — **the list of questions the user now owes an answer to**, in
one block they can act on. After § 6: each delta as `id` · `blocked_by` · row · action, queue first;
rows moved (old → new, and the source that decided it); records unblocked; any `index.jsonl` record
the change shows to be wrong — reported, never fixed, it is `/clio:memo`'s. Close with the plan
commands: first run → `/clio:plan infra`, then `/clio:plan <area>` per area; later runs → the areas
§ 6 names. Rewrite the `Last ingest:` line last.

## 6. What the change invalidates — re-ingest and sweep

Specs move while code stands still. For every decision this run added, altered, reversed or resolved:

**Before and after.** A change this run wrote is known. A hand edit is in git:
```bash
git diff <Last ingest commit> -- .claude/clio/docs/specs/     # committed and uncommitted since
git log -p -3 --format='%h %ad %s' --date=short -- .claude/clio/docs/specs/memory/<file>.md
```
No commit on the `Last ingest:` line, or `.claude/clio/` not in git → reconstruct from dated notes
("Superseded YYYY-MM-DD", the row's status text) and what the task docs assumed. Still cannot state
the before-state → write the delta as new-rule-only and say so in the report.

**Who built against it.**
```bash
${CLAUDE_PLUGIN_ROOT}/skills/context/scripts/q.sh built --req <row> --spec <file>
${CLAUDE_PLUGIN_ROOT}/skills/context/scripts/q.sh owed --req <row> --spec <file>
```
Read those docs' `## Decisions`, `## Side Effects`, `## Follow-up`: the code paths named there go in
`code[]`, the docs themselves in `docs[]`. That list is how `/clio:memo` later marks their sections
superseded; without it `clio:context` keeps serving a doc the change made untrue.

**What to write.**

| The change | Write |
|---|---|
| something was built against the old decision | a `spec-delta`; reuse an existing `id` for the same delta. `blocked_by: null` once the new decision is settled — that is the work queue; the concrete missing thing while it is second-hand or awaits a "re-verify" |
| nothing built against it yet | no delta — `/clio:plan` reads the spec itself |
| it answers what an open `spec-blocked` waited on | a new line under that record's `id`, in full, `blocked_by: null`; never edit the old line or change its `kind` |

```bash
cat >> .claude/clio/database/debt.jsonl <<'EOF'
{"date":"YYYY-MM-DD","id":"<kebab-key>","kind":"spec-delta","status":"pending","domain":"checkout","what":["<old> → <new>"],"req":["18"],"specs":[".claude/clio/docs/specs/memory/<file>.md"],"docs":["<task docs built on the old decision>"],"code":["<paths they name>"],"action":"<the rework>","source":"<source §n, date>","blocked_by":null,"issue":null}
EOF
${CLAUDE_PLUGIN_ROOT}/skills/memo/scripts/validate.sh debt
```

**The row marker**, when the *decision* changed — decisions only, never build state:

| Marker now | The change | Do |
|---|---|---|
| ⚠️ / ❌ | the open point got decided | → ✅, reason = decision + date |
| ⚠️ / ❌ | a different part is still open | keep, rewrite the reason |
| ✅ | reopened or reversed | → ⚠️, say what reopened it |
| ✅ | refined | keep ✅, append the decision + date |

**Moving toward ✅ removes a stop, so it asks first**: every such row in one `AskUserQuestion` as
`row · old reason → new decision · deciding source`; write only the approved ones. The other moves
add or keep a stop — write them. Never flip on a low-priority source; the marker and `blocked_by`
must tell the same story.

**The areas to re-plan.** One line per area whose rows moved, `memory/infra.md` (row `0`) first — it
invalidates `plans/infra.md` and the `rules/` commands `/clio:test` runs:
```text
infra     row 0 · Go 1.22 → 1.23 · rules/go.md names `go test ./...`        →  /clio:plan infra
checkout  row 12 · 3.2 [x] built on the old rule · spec-delta checkout-loyalty
          · cases 3.2-a1, 3.2-s1 test the old rule                           →  /clio:plan checkout
ocr       row 20 still ⚠️                                                      →  nothing to plan yet
```
`/clio:plan` turns each delta into a sub-task and never edits an existing row; `/clio:test`
re-designs the stale cases on that sub-task. This skill writes neither plans nor cases.
