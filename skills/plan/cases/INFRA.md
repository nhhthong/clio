# Infra — the toolchain and scaffold, planned first

Read by `/clio:plan` for the `infra` target, or when no `plan/infra.jsonl` exists yet (then plan
`infra` first and say so). Then back to `SKILL.md` § 4 to show, ask and write — with
`clio add plan infra`.

## Where the stack comes from

The stack is decided upstream; this skill never picks one. In order:
1. `memory/infra.md` (row `0`, written by `/clio:ingest`) — its `## Decisions` and the ADR it names.
2. No spec (Lite mode) → the repo's own manifests and lockfiles. `req` is `[]`.
3. Neither — an empty repo with no infra spec → stop: `/clio:ingest` a brief, or have the user name
   the stack and record it with `/clio:ingest`. Do not research one here.

For each decided piece — toolchain, scaffold, build, test runner, formatter, linter — the exact
command from the repo's config (repo has code) or from the tool's current docs via Context7 (empty
repo), with the version it needs. Every infra task's level is `smoke`; the last one is the smoke
suite every other area's tasks name in `needs`.

```bash
clio add plan infra <<'EOF'
{"type":"task","id":"0.1","task":"Toolchain on PATH: Go 1.22+, Wails v2","req":["0"],"levels":["smoke"]}
{"type":"task","id":"0.2","task":"Scaffold: `wails init -n app -t svelte-ts`","req":["0"],"levels":["smoke"],"needs":["0.1"],"touches":["./"]}
{"type":"task","id":"0.3","task":"Test runner and smoke suite run on the scaffold","req":["0"],"levels":["smoke"],"needs":["0.2"]}
EOF
```

## `.claude/rules/<stack>.md`

One per stack, 10–20 lines, `paths:` frontmatter naming that stack's extensions — or none at all (a
rule without `paths:` loads every session). Nothing is copied from a template: every bullet is read
off this repo. Empty repo → write it after the scaffold task ran, not before.

For each bullet the repo has to show it:
- **Build, test, format, lint** — the exact command, from the manifest's script block or the config
  on disk (`.prettierrc`, `pint.json`, `.golangci.yml`, `pyproject.toml`). Not present → no bullet.
- **Generated vs source** — only pairs you can point at: the generator config, the output directory,
  and the command that regenerates it. `/clio:memo` reads this to drop build output.
- **Frozen artefacts** — applied migrations, committed lockfiles, vendored directories.
- Not a `Batch:` line — `/clio:test` researches, measures and proposes that one itself.
- **The one convention this repo already follows** that a new file must match; read 2–3 existing
  files rather than stating the language's general advice.

Never write a bullet the ecosystem would agree with but this repo does not show. No verifiable
bullet, no file. Show the draft and **ASK** before writing it.

**The file already exists** — it is the user's now: never rewrite, reorder or trim it. Propose only
the missing bullets, as a diff under the section they belong to. A bullet the repo now contradicts
(a command renamed, a tool removed) is proposed as its own diff line with what changed and where you
read it — never deleted silently. Keep its `paths:`; widen it only when a new bullet needs it, and
say so. Nothing to add → leave it untouched.

A mechanical rule — format on save, lint before commit — is better as a hook than a bullet. Say so
once and leave the hook to the user; this skill writes no settings file.

## Mutation testing, decided once

Not asked in `infra` — whether any task needs mutation is known only once an area is planned. The
first time the user agrees to `mutation` for a task and `clio q plan infra --all` shows no mutation
decision, settle the tool for the whole project there: look up this stack's mutation tester in
Context7 (PIT for JVM, Stryker for JS/TS/.NET, mutmut for Python, go-mutesting…), show the install
and the threshold flag, and **ASK**. Record the choice as an ADR
(`${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/WRAP-UP.md` § ADR, indexed `"type":"adr"`,
`"domain":"infra"`, `"req":["0"]`, then `clio validate index`), and as the project's record:
```bash
clio add plan infra <<'EOF'
{"type":"mutation","tool":"stryker","threshold":null,"adr":".claude/clio/docs/decisions/<ts>_mutation.md"}
EOF
```
- Yes → `threshold` stays `null` for LEVELS.md's 80 %, or the project's number; plus an infra task
  installing the tool (`levels` `smoke`). The area task keeps `mutation`; the gate holds its
  command to the threshold.
- No → `"tool":"none"`; the area task drops `mutation`. From then on no task is proposed it, and the
  gate refuses a task that still names it.

Either way the question is not asked again.
