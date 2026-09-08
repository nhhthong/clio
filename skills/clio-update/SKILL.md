---
name: clio-update
description: After a spec file changes, work out what the change means for code already written — which task/decision docs it invalidates, whether it is safe to implement yet — record each delta in .claude/clio/debt.jsonl, and move the requirements.md row marker when the decision itself changed. Run when a requirement, contract or ticket changes.
argument-hint: "[spec file or keyword, optional — omit to sweep all specs]"
disable-model-invocation: true
---

Specs move while code stands still. This skill finds the gap and writes it down; it does **not**
implement anything.

Target (may be empty): $ARGUMENTS

Step files live in `${CLAUDE_SKILL_DIR}/steps/`. Read each one when you reach it, not before.

## Walk the steps, in order

1. **What changed, who's affected** → `${CLAUDE_SKILL_DIR}/steps/WHAT-CHANGED.md`. Establish the
   delta from the spec's source-priority order, then join it to prior work through
   `index.jsonl` / `debt.jsonl`.
2. **Decide the status** → `${CLAUDE_SKILL_DIR}/steps/DECIDE-STATUS.md`. The whole point of the
   file — `status` + `blocked_by` decide whether anyone may implement it.
3. **Append the delta** → `${CLAUDE_SKILL_DIR}/steps/APPEND-DEBT.md`. Write it to
   `.claude/clio/debt.jsonl`, then **move the `requirements.md` row** if the delta changed the
   decision itself — same file, second half.
4. **Unblock and report** → `${CLAUDE_SKILL_DIR}/steps/WRAP-UP.md`. Check whether this delta answers
   another open record, then report everything.

Validate with `"${CLAUDE_PLUGIN_ROOT}"/scripts/validate.sh debt` after every append.
