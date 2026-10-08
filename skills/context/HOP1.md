# Hop 1 — the requirement (`.claude/clio/docs/specs/requirements.md`)

Derive keywords from the task: domain area/domain, route path, model/table, module, feature name.
`/account/orders` → `account`, `order`. `infra/docker/entrypoint` → `infra`.
```bash
grep -in "<keyword>" .claude/clio/docs/specs/requirements.md
```
`requirements.md` maps requirement rows (contract tasks, epics, or issue numbers — whatever `req` means in
this project) + a topic-keyword table onto `memory/*.md` spec files. Read the mapped file(s) in
full — they're short and already distilled.

**Status markers decide what happens next:**
- ✅ → decision exists. Build against it.
- ⚠️ / ❌ → something on this row is undecided/conflicting/waiting on an answer. Default to stopping
  and asking — this is `requirements.md`'s own rule, outranks any inference from code. Say which row, what
  is unresolved.

  **A row marker is coarse; a `debt.jsonl` record is specific, and specific wins.** ⚠️ means part of
  the row is open, not all — before stopping, run [HOP3.md](HOP3.md) for that row: a record with
  `blocked_by: null` covering your exact piece → you may build that piece, say in your report which
  part of the row stays ⚠️ and why. No record covers it, or `blocked_by` is non-null → the ⚠️ stands,
  stop and ask. A ⚠️/❌ row with **no** debt record at all is a finding in its own right (main file's
  Report section) and still a stop.
- No row matches → say so (outside contracted scope, or `requirements.md` missing a row). Worth a sentence,
  not a reason to stop.

Note the row number(s) (`req`) — reused in [HOP2.md](HOP2.md), and `/clio:memo` needs them.

The area has a plan → run `clio q summary` and read this area's `next:` line for the next ready
task — **never derive it yourself** from `clio q plan`: a `needs` can name a task in a *different*
area (`0.4` in `infra`), which only `clio q summary` resolves across every area at once. Its cases
(`clio q cases <task>`) are the success criterion; none yet → `/clio:test <task>` designs them
before code. No plan for a ✅ row you are about to build → say `/clio:plan <area>` has not been
run, continue.
