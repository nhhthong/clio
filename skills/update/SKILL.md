---
name: update
description: After a spec file changes, work out what the change means for code already written — which task/decision docs it invalidates, whether it is safe to implement yet — record each delta in .claude/clio/debt.jsonl, and move the requirements.md row marker when the decision itself changed. Run when a requirement, contract or ticket changes.
argument-hint: "[spec file or keyword, optional — omit to sweep all specs]"
disable-model-invocation: true
---

Specs move while code stands still. This skill finds the gap and writes it down; it does **not**
implement anything.

Target (may be empty): $ARGUMENTS

## 1. What changed, who is affected

Argument given → that spec file, or the `requirements.md` row matching the keyword. Nothing given →
sweep `.claude/docs/specs/memory/*.md` and `requirements.md`.

Establish the *delta* — what is different now — working through the source-priority list
`requirements.md` declares, highest first; the live decision channel outranks every distilled file.
Old wording gone → reconstruct it from dated notes ("supersedes …", "reversed YYYY-MM-DD", the row's
status text) and what the task docs assumed at the time. Cannot state the before-state → write the
delta as new-rule-only and flag it in the report.

Join the delta to prior work:
```bash
jq -s -c 'group_by(.doc)[] | last | select((.req[]? == <N>) or (.specs[]? | contains("<spec>")))' .claude/clio/index.jsonl
jq -s -c 'group_by(.id)[] | last
  | select(.status!="done" and ((.req[]? == <N>) or (.specs[]? | contains("<spec>"))))' .claude/clio/debt.jsonl
```
Open the matching docs and read `## Decisions`, `## Side Effects`, `## Follow-up` — that is what a
spec change invalidates. Note the code paths named there for `code[]`.

## 2. Decide the status

`blocked_by` is decisive, not `status`: `status` says how far the work got, `blocked_by` says whether
anyone may start.

| `status` | `blocked_by` | Meaning | May implement? |
|---|---|---|---|
| `pending` | `null` | settled, code doesn't match yet, nothing external missing | **yes — the queue** |
| `pending` | a string | still open, or depends on something outside (upstream field, sample, undecided rule) | no |
| `in-process` | either | workaround shipped, root cause open | only to continue, only if `blocked_by` is `null` |
| `done` | `null` | code already matches, or no code needed | no — don't redo it |

Write `blocked_by` as the concrete missing thing ("no sample file received"), never "pending
confirmation"; `null` the moment nothing external is missing. A ✅ row means a decision exists, not
that it is built (✅ + mismatch = `pending` + `blocked_by: null`). A decision confirmed only
second-hand, or carrying a "re-verify" note in the live channel, keeps a non-null `blocked_by`.

## 3. Append the delta

`kind` is always `spec-delta`. Full 14-field schema, append-only rule and validation →
`${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/DEBT-IT.md`. Reuse an existing `id` for the same delta
(`jq -c --arg i "<id>" 'select(.id==$i)' .claude/clio/debt.jsonl`), then:
```bash
echo '{"date":"YYYY-MM-DD","id":"<kebab-key>","kind":"spec-delta","status":"pending","domain":"checkout","what":["…"],"req":[18],"specs":[".claude/docs/specs/memory/<file>.md"],"docs":["…"],"code":["…"],"action":"…","source":"…","blocked_by":null,"issue":null}' >> .claude/clio/debt.jsonl
"${CLAUDE_PLUGIN_ROOT}"/skills/memo/scripts/validate.sh debt
```

## 4. Move the `requirements.md` row if the *decision* changed

You are the only writer of `.claude/docs/specs/`; a stale marker keeps `clio:context` stopping
future sessions to ask about a settled point.

| Marker now | Delta means | Do |
|---|---|---|
| ⚠️ / ❌ | the open point got decided | flip to ✅, reason text = decision + date |
| ⚠️ / ❌ | a different part of the row is still open | keep marker, rewrite the reason to name what is open |
| ✅ | a settled point was re-opened or reversed | flip to ⚠️, say what re-opened it and where |
| ✅ | refinement of a decided point | keep ✅, append the new decision + date |

Decisions only, never build state. Never flip ⚠️→✅ off a low-priority source; marker and
`blocked_by` must tell the same story — say so in the report if you cannot reconcile them.

## 5. Unblock and report

A delta you just recorded may be the answer another open record on the same rows was waiting on.
For each one it resolves, append a new line under that record's `id`, in full, with `blocked_by:
null` — never edit the old line, never change its `kind` (re-filing `spec-blocked` as `code-debt`
is `/clio:memo`'s call). `index.jsonl` is not yours: a wrong `req`/`specs` there is reported, not
fixed.

Report each delta as `id` · `status` · `blocked_by` · row · one-line action, queue (`blocked_by:
null`) first. Then: deltas you could not date, what is blocked on exactly what, records you
unblocked, every row moved (old → new, and the source that justified it), rows deliberately left
⚠️, and any `index.jsonl` record this delta shows to be wrong. A moved row that has a
`.claude/docs/plans/<area>.md` → say to re-run `/clio:plan <area>`; its tasks may be superseded.
