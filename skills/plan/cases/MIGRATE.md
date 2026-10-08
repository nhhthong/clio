# Migrate — a 4.x project's Markdown plans and case tables

Read by `/clio:plan` while `.claude/clio/docs/plans/*.md` or `docs/tests/*.md` exist. Since 5.0 the
plan and the cases live in `database/plan|test/<area>.jsonl`; nothing reads the Markdown any more,
so a project is migrated once, before any other plan work. The user asked for a plan; this comes
first, and says so.

```bash
clio test migrate            # dry run: what moves where, which approvals carry over — writes nothing
```
Show its output and **ASK** before writing. Read it for:
- `FAIL` lines — an id in two plan files, an unticked pre-4.0 row with no levels, a case row split
  by a `|`. Nothing is written while any remains. Each is the user's call: which id to rename, which
  old row to drop. Fix the Markdown with them, then run the dry run again.
- `skipped:` — ⚠️ placeholder rows; they are not tasks, and the report still names their debt.
- `not carried` — approvals whose table changed after the yes. Those tasks are approved again the
  next time `/clio:test` runs them; say which.

On a yes:
```bash
clio test migrate --write
clio validate all
```
Evidence already recorded keeps counting — it is keyed by case id and command, which move unchanged.
The Markdown goes to `docs/archive/v4/` for comparison; tell the user it may be deleted once
`clio q plan --all` reads right. `validate all` names any task whose `needs` point at nothing — a
task that lived only in a deleted plan — for `cases/CHANGE.md` to settle.

Then carry on with what the user asked.
