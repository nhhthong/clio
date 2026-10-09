# Infra

Toolchain and scaffold, planned first. Read for `infra`, or when no `plan/infra.jsonl` exists (plan it first and say so). Then write as in `SKILL.md` step 4, with `clio add plan infra`.

## The stack is decided upstream
Never pick a stack here. Look in this order:
1. `memory/infra.md` (row 0, from `/clio:ingest`): its `## Decisions` and ADR.
2. No spec (Lite mode): the repo's manifests and lockfiles. `req` is `[]`.
3. Neither (empty repo, no spec): stop. Ask the user to `/clio:ingest` a brief or name the stack.

For each decided piece (toolchain, scaffold, build, test runner, formatter, linter), take the exact command from the repo's config, or from the tool's current docs via Context7 on an empty repo, with the version it needs. Every infra task has level `smoke`. The last one is the smoke suite that other areas name in `needs`. A typical chain: toolchain on PATH, then scaffold (`touches` the project root), then test runner and smoke suite running on the scaffold, each `needs` the one before.

## `.claude/rules/<stack>.md`
One file per stack, 10 to 20 lines, with `paths:` naming its extensions. A rule without `paths:` loads every session. Read every bullet off this repo and copy none from a template. An empty repo gets the file after the scaffold task ran. Add a bullet only if the repo shows it:
- Build, test, format, lint: the exact command, from manifest scripts or config on disk. If absent, no bullet.
- Generated versus source: a pair you can point at (generator config, output dir, regenerate command). `/clio:memo` drops build output with it.
- Frozen artefacts: applied migrations, lockfiles, vendored dirs.
- The one convention a new file must match, read from 2 or 3 existing files. Not a `Batch:` line, since `/clio:test` finds that.

A bullet the ecosystem would agree with but this repo does not show is noise. If nothing is verifiable, write no file. Show the draft and ask.

A file that exists belongs to the user. Never rewrite, reorder or trim it. Propose only missing bullets, as a diff. A bullet the repo now contradicts is its own diff line, with what changed and where you read it, and is never deleted silently. Keep its `paths:`. If there is nothing to add, leave it. A mechanical rule (format on save, lint before commit) works better as a hook: say so once and leave it to the user.

## Mutation testing, decided once
This is known only once an area is planned. The first time the user agrees to `mutation` for a task, and `clio q plan infra --all` shows no `mutation` record, look up the stack's mutation tool in Context7 (PIT, Stryker, mutmut, go-mutesting). Show the install step and the threshold flag, and ask. Record an ADR (`memo/steps/RARE.md`, indexed with `clio add index`, type `adr`, domain `infra`, req `["0"]`) and a `mutation` record ([../RECORDS.md](../RECORDS.md)).

- Yes: `threshold` null means 80 percent (or the project's own). Add an infra `smoke` task that installs the tool. The gate holds the command to the threshold.
- No: set `tool` to `none`. The area task drops `mutation`, none is proposed again, and the gate refuses a task that still names it.

Never ask twice.
