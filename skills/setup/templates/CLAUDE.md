<!-- HOW TO FILL THIS FILE
     This file loads every session. Fill each section from its comment, then DELETE every HTML
     comment (this one included) — /clio:setup does this, validate.sh warns while any remain.
     Target under ~80 lines. Record only what the code cannot tell you. -->

# CLAUDE.md

@CONTEXT.md

<!-- One paragraph: what this project is, stack + versions, and the constraint that shapes it
     (legacy port, multi-tenant, regulated data, offline-first…). -->

## Architecture

<!-- 10–20 line directory tree, one comment per top-level dir. Name the seam that matters — which
     dir is the thin framework layer, which holds the business logic. Delete if obvious. -->

## Code style

<!-- Formatter + its config file, and what is excluded from it. Delete if the repo has no formatter. -->

## Project memory — how this repo records work

| Question | Home | Written by |
|---|---|---|
| Has it been *decided*? | `.claude/docs/specs/requirements.md` status column | humans + `/clio:update` |
| What was *built*, when? | `.claude/clio/index.jsonl` | `/clio:memo` |
| What is still *owed*? | `.claude/clio/debt.jsonl` | `/clio:memo`, `/clio:update` |

✅ means decided, never built. Never write build progress into a spec file, or a spec decision into
the ledgers.

Domains — the only values allowed in the `domain` field of both ledgers, by business area served,
never by directory: <!-- fill at setup, e.g. `account` `checkout` `billing` `infra` `all` -->

- Before non-trivial work in an area → run the `clio:context` skill.
- Building a spec area → `/clio:plan <area>` first; one task at a time, its `Test` column is the
  success criterion.
- After finishing a piece of work → `/clio:memo`. What is owed → `clio:context`, which reads it.
- A spec changed but the code hasn't → `/clio:update`; it records the delta and names the plans built
  against the old decision. `/clio:ingest` and `/clio:update` are the only writers of `docs/specs/`.
- Keep the `@CONTEXT.md` line above; keep this file and CONTEXT.md free of HTML comments.
- New file in `.claude/rules/` → start it with `paths:` frontmatter, or it loads in every session.

## Rules

- IMPORTANT: **Verify, or say "unverified" and ask.** Anything a tool can check — a route, a config
  key, a method signature, a column, a proto field, a number — gets checked before you state it.
  Read the migration or the schema; never infer a field from a similar one. An ambiguous requirement
  gets a question, not a guess: wrong-per-spec costs more than incomplete. Several readings → give
  them all.
- **Minimal scope.** Every changed line traces to the request. Match the surrounding style. Delete
  only what your own change orphaned; mention other dead code. A simpler approach exists → say so
  first.
- **Name the success criterion before starting** — "tests for invalid inputs pass", "a test
  reproduces the bug, then passes". That is what `## Testing Done` records; nothing ran → say so,
  and `/clio:memo` files it `unverified`.
- IMPORTANT: Write code comments only when the user asks for them.

<!-- Project rules go here, as bullets above. Ask, don't guess: money/payment/auth/deletion →
     state assumptions and ask · i18n call · timezone · money representation · generated paths and
     their real source. -->
