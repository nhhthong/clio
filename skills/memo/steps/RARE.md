# The uncommon paths of /clio:memo

Read only when the case calls for it.

## Backfill (Case D)
Nothing is uncommitted and every unrecorded commit names the docs covering its files: the work was recorded while uncommitted and has since been committed. For each such doc: `clio doc` with `"doc":…`, `"commit":"<hash>"`, `"changelog":"committed as <hash>"`; one `clio add index` call for all their records (`commits` = previous + the hash); `clio test tick <id> --commit <hash>` for each of their done tasks (on a done task it records the hash and runs nothing, and refuses to overwrite one). Nothing else is re-derived; say "backfill". A commit shown as `-` is work nobody recorded: Case C for its files, or a chore.

## Chore
A commit the user says is no task's work (CI config, tooling, a hand-made dependency bump) gets one record instead of a doc, so `q unrecorded` and the drift hook stop naming it. It is skipped, never a stopping point: older unrecorded work is still reported. Only on the user's word, one commit at a time, never to quiet the hook.
```bash
clio add index <<'EOF'
{"id":"<full hash>","type":"chore","commits":["<hash>"],"note":"<why no task owns it, in the user's words>"}
EOF
```

## A withdrawn task
`clio test withdraw` printed `doc: <path> [tasks] relabel …` for each doc describing it. A doc whose tasks are all withdrawn: `clio doc` with `"relabel":["Summary","Decisions"]`; a doc that also covers live tasks: only the bullets about the withdrawn ones. Each doc touched gets a `changelog` line and an index update; close the `spec-delta` the withdrawal answers.

## An ADR
A significant architectural decision made this run. Check `.claude/clio/docs/decisions/` for an existing one first (UPDATE before CREATE). Else create `decisions/<ts>_<keywords>.md` (`ts` = `date +%s`), index it with `"type":"adr"` and that `ts` as `id`, and link it from the task doc's `related`. ADRs stay in this one flat directory, never in a feature's folder: `ls` on it must keep answering "what has this project committed to?".
```markdown
# <Decision title>
Date: YYYY-MM-DD
Commit: <hash, or nothing until committed>
## Context
<The forces. What made the obvious choice wrong.>
## Decision
<What was chosen, stated so a future session applies it without re-deriving it.>
## Consequences
<What this makes easy, what it makes hard, what must never be done because of it.>
```

## Light work
Every plan task of the run is `"tier":"light"` (`clio q plan --id <id>`): step 2 is `clio doc` with `"light":true`, step 3 its index line, step 4 the gate and the tick. No Decisions, Files Changed or Testing Done bookkeeping, no wrap-up beyond the report. The gate is never skipped.
