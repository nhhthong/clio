# Infra — toolchain and scaffold, planned first

For `infra`, or when no `plan/infra.jsonl` exists (plan it first and say so). Then `SKILL.md` § 4, with `clio add plan infra`.

## The stack is decided upstream; never pick one here
1. `memory/infra.md` (row `0`, from `/clio:ingest`): its `## Decisions` and ADR.
2. No spec (Lite mode) → the repo's manifests and lockfiles; `req` is `[]`.
3. Neither (empty repo, no spec) → stop: `/clio:ingest` a brief, or have the user name the stack.

For each decided piece (toolchain, scaffold, build, test runner, formatter, linter): the exact command from the repo's config, or from the tool's current docs via Context7 (empty repo), with the version it needs. Every infra task's level is `smoke`; the last is the smoke suite other areas name in `needs`.
```bash
clio add plan infra <<'EOF'
{"type":"task","id":"0.1","task":"Toolchain on PATH: Go 1.22+, Wails v2","req":["0"],"levels":["smoke"]}
{"type":"task","id":"0.2","task":"Scaffold: `wails init -n app -t svelte-ts`","req":["0"],"levels":["smoke"],"needs":["0.1"],"touches":["./"]}
{"type":"task","id":"0.3","task":"Test runner and smoke suite run on the scaffold","req":["0"],"levels":["smoke"],"needs":["0.2"]}
EOF
```

## `.claude/rules/<stack>.md`
One per stack, 10–20 lines, `paths:` naming its extensions (a rule without `paths:` loads every session). Every bullet is read off this repo, none copied from a template; an empty repo gets it after the scaffold task ran. A bullet only if the repo shows it:
- **Build, test, format, lint**: the exact command, from the manifest scripts or config on disk. Not present → no bullet.
- **Generated vs source**: a pair you can point at: generator config, output dir, regenerate command (`/clio:memo` drops build output with it).
- **Frozen artefacts**: applied migrations, lockfiles, vendored dirs. **The one convention** a new file must match, read from 2–3 existing files. Not a `Batch:` line (`/clio:test` finds that).

Never a bullet the ecosystem would agree with but this repo does not show; none verifiable → no file. Show the draft, **ASK**. **A file that exists is the user's**: never rewrite, reorder or trim; propose only missing bullets, as a diff; a bullet the repo now contradicts is its own diff line with what changed and where you read it, never deleted silently; keep its `paths:`. Nothing to add → leave it. A mechanical rule (format on save, lint before commit) is better as a hook: say so once, leave it to the user.

## Mutation testing, decided once
Known only once an area is planned. The first time the user agrees to `mutation` for a task and `clio q plan infra --all` shows no `mutation` record: look up the stack's tester in Context7 (PIT, Stryker, mutmut, go-mutesting…), show install and threshold flag, **ASK**. Record an ADR (`memo/steps/RARE.md`, `clio add index`, `"type":"adr"`, `"domain":"infra"`, `"req":["0"]`) and the decision:
```bash
clio add plan infra <<'EOF'
{"type":"mutation","tool":"stryker","threshold":null,"adr":".claude/clio/docs/decisions/<ts>_mutation.md"}
EOF
```
Yes → `threshold` null = 80 % (or the project's), plus an infra `smoke` task installing the tool; the gate holds the command to it. No → `"tool":"none"`: the area task drops `mutation`, none is proposed again, the gate refuses a task still naming it. Not asked twice.
