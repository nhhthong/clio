<!-- HOW TO FILL THIS FILE
     These HTML comments are stripped before the file enters a session's context, but stay visible
     when the file is opened with Read. Fill the sections, leave the comments where they are.
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
| Has it been *decided*? | `.claude/docs/specs/requirements.md` status column | humans + `/clio-update` |
| What was *built*, when? | `.claude/clio/index.jsonl` | `/clio-memo` |
| What is still *owed*? | `.claude/clio/debt.jsonl` | `/clio-memo`, `/clio-update` |

✅ means decided, never built. Never write build progress into a spec file, or a spec decision into
the ledgers.

Domains — the only values allowed in the `domain` field of both ledgers, by business area served,
never by directory: <!-- fill at setup, e.g. `account` `checkout` `billing` `infra` `all` -->

- Before non-trivial work in an area → run the `clio-context` skill.
- After finishing a piece of work → `/clio-memo`. What is owed → `/clio-debt`.
- A spec changed but the code hasn't → `/clio-update`. It is the only writer of `docs/specs/`.
- Keep the `@CONTEXT.md` line above; keep CONTEXT.md free of HTML comments.
- New file in `.claude/rules/` → start it with `paths:` frontmatter, or it loads in every session.

## Rules

- IMPORTANT: **No speculation, no hallucination.** Never fill a gap with a plausible-sounding
  answer — code behavior, file/route/column existence, business rules, spec intent, config values.
  Not verified (Read/Grep/DB query/actual run) → say "unverified" and **ask the user**. Ambiguous
  requirement → ask, don't invent; wrong-per-spec is worse than incomplete. Verify before stating:
  routes, config keys, method signatures, translation keys, numeric values, and any field of a
  schema or contract (DB column, protobuf message, OpenAPI/GraphQL field, event payload) — read the
  migration/`DESCRIBE`/`.proto`/schema first, never infer a field from a similar one. Multiple valid
  interpretations → present them, never pick one silently.
- Minimal scope, surgical edits: every changed line must trace to the request. No drive-by
  refactors, no speculative abstractions. Match the surrounding style. Remove only what **your**
  change orphaned; unrelated dead code gets mentioned, never deleted. A simpler approach exists →
  say so before building the complex one.
- Define the success criterion before starting: "add validation" → "tests for invalid inputs pass";
  "fix the bug" → "a test reproduces it, then passes". That criterion is what `## Testing Done`
  records; nothing ran → say so, and `/clio-memo` files it as `unverified`.
- IMPORTANT: Do not add code comments unless the user explicitly asks for them.

<!-- Project-specific hard rules go here, as bullets in the list above. Ask the user, don't guess:
     - Anything touching <money / payment / auth / data deletion> → state assumptions and ask.
     - i18n: never hardcode UI text, always `<translate call>`.
     - Timezone: default `<TZ>` — confirm before changing time logic.
     - Money: integer minor units only, never float.
     - Generated files: `<path>` is build output — edit `<source path>` instead. -->
