# Scaffold and toolchain

There is no separate infra plan. Every area plan diagnoses the toolchain itself in step 2, so nothing is built before an area needs it, and a spec that moves leaves no scaffold to delete.

## Diagnose
Look in this order:
1. The repo's manifests, lockfiles and CI config: build, test runner, formatter, linter, with the exact commands.
2. `memory/infra.md` (row 0): the constraints the source states, and the stack if one is chosen.
3. Neither (empty repo, no stack): the stack is open. Research 2 or 3 candidates that fit the constraints in Context7 (web search if absent; say which), show them side by side, and ask. Never pick silently. Record the choice as an ADR (`memo/steps/RARE.md`, indexed with `clio add index`, type `adr`, domain `infra`, req `["0"]`).

Ask of what you found: can this area's first task be built and tested as the repo stands? Yes: no scaffold task, write nothing here. No: the gap is a task of this area.

## The scaffold task
The first task of the first area that needs it, id `<row>.0`, holding only what that area needs (toolchain on PATH, project root, test runner). It is a `none` tier task ([../../test/LEVELS.md](../../test/LEVELS.md) § Tier) whose `check` is the build or test-runner command that proves the scaffold runs. Every other task of the area names it in `needs`. A later area finds the toolchain in place and adds nothing. Libraries for one domain (OCR, imaging, an HTTP client) belong to the task that uses them.

## `.claude/rules/<stack>.md`
Written after the scaffold task ran, when the repo can show the bullets. One file per stack, 10 to 20 lines, with `paths:` naming its extensions. A rule without `paths:` loads every session. Read every bullet off this repo and copy none from a template. Add a bullet only if the repo shows it:
- Build, test, format, lint: the exact command, from manifest scripts or config on disk. If absent, no bullet.
- Generated versus source: a pair you can point at (generator config, output dir, regenerate command). `/clio:memo` drops build output with it.
- Frozen artefacts: applied migrations, lockfiles, vendored dirs.
- The one convention a new file must match, read from 2 or 3 existing files. Not a `Batch:` line, since `/clio:test` finds that.

A bullet the ecosystem would agree with but this repo does not show is noise. If nothing is verifiable, write no file. Show the draft and ask.

A file that exists belongs to the user. Never rewrite, reorder or trim it. Propose only missing bullets, as a diff. A bullet the repo now contradicts is its own diff line, with what changed and where you read it, and is never deleted silently. Keep its `paths:`. If there is nothing to add, leave it. A mechanical rule (format on save, lint before commit) works better as a hook: say so once and leave it to the user.

## Mutation testing, decided once
Known only once a task qualifies. The first time the user agrees to `mutation` for a task, and `clio q plan --all` shows no `mutation` record, look up the stack's mutation tool in Context7 (PIT, Stryker, mutmut, go-mutesting). Show the install step and the threshold flag, and ask. Record an ADR (`memo/steps/RARE.md`, indexed with `clio add index`, type `adr`, domain `infra`, req `["0"]`) and a `mutation` record ([../RECORDS.md](../RECORDS.md)).

- Yes: `threshold` null means 80 percent (or the project's own). Add a `none` tier task of that area that installs the tool, with the install check as its `check`. The gate holds the mutation command to the threshold.
- No: set `tool` to `none`. The area task drops `mutation`, none is proposed again, and the gate refuses a task that still names it.

Never ask twice.
