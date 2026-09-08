<!-- HOW TO FILL THIS FILE
     These HTML comments are stripped before the file enters a session's context, but stay visible
     when you open the file with the Read tool. So: fill in the sections, leave the comments where
     they are — they cost nothing at runtime and guide the next edit.
     Target under ~80 lines total. Record only what the code cannot tell you; cut anything a reader
     could derive from the repo itself. -->

# CLAUDE.md

@CONTEXT.md

<!-- One paragraph: what this project is, stack + versions, and the constraint that shapes it
     (legacy port, multi-tenant, regulated data, offline-first…). -->

## Architecture

<!-- 10–20 line directory tree, one comment per top-level dir. Name the seam that matters — which
     dir is the thin framework layer, which holds the business logic. Delete this heading if the
     layout is obvious from the root listing. -->

## Code style

<!-- Formatter + its config file, and what is excluded from it. One or two lines; delete the
     heading if the repo has no formatter. -->

## Project memory — how this repo records work

Three questions, three separate homes. Never mix them:

| Question | Home | Written by |
|---|---|---|
| Has it been *decided*? | `.claude/docs/specs/requirements.md` status column | humans + `/clio-update` |
| What was *built*, when? | `.claude/clio/index.jsonl` | `/clio-memo` |
| What is still *owed*? | `.claude/clio/debt.jsonl` | both commands |

✅ means decided, never built. Never write build progress into a spec file, or a spec decision into
the ledgers.

Domains — the only values allowed in the `domain` field of both ledgers, by business area served,
never by directory: <!-- fill at setup, e.g. `account` `checkout` `billing` `infra` `all` -->

- Before non-trivial work in an area → run the `clio-context` skill.
- After finishing a piece of work → `/clio-memo`. Quick look at what is owed → `/clio-debt`.
- A spec changed but the code hasn't → `/clio-update`. It is the only writer of `docs/specs/`.
- `@CONTEXT.md` above imports `.claude/CONTEXT.md` at launch — it is not a file the harness loads on
  its own. Keep the line; keep CONTEXT.md free of HTML comments (imports are not guaranteed to strip
  them).
- New file in `.claude/rules/` → start it with `paths:` frontmatter, or it loads in every session.
- Auto memory (`~/.claude/projects/<project>/memory/`) is machine-local and outside git: it holds
  the user's preferences and corrections, never this project's decisions or open debt.

## Rules

- IMPORTANT: **No speculation, no hallucination.** Never guess or fill a gap with a
  plausible-sounding answer — code behavior, file/route/column existence, business rules, spec
  intent, config values, anything. Not verified (Read/Grep/DB query/actual run) → say "unverified"
  and **ask the user**. Ambiguous requirement → ask, don't invent; wrong-per-spec is worse than
  incomplete. Verify before stating: routes, config keys, method signatures, translation keys,
  numeric/config values (read the stored value before comparing it against a spec number), and any
  field of a schema or contract — DB column, protobuf message, OpenAPI/GraphQL field, event payload,
  save-file format: read the migration/`DESCRIBE`/`.proto`/schema file first, never infer a field
  from a similar one. Example/test numbers → label as arbitrary test input, never next to a spec
  claim.
  Multiple valid interpretations → present them, never pick one silently.
- Minimal scope, surgical edits: every changed line must trace to the request. No drive-by
  refactors, no speculative abstractions. Match the surrounding style even where you'd do it
  differently. Remove only the imports/vars/functions **your** change orphaned; unrelated dead code
  gets mentioned, never deleted. A simpler approach exists → say so before building the complex one.
- Define the success criterion before starting, not after: "add validation" → "tests for invalid
  inputs pass"; "fix the bug" → "a test reproduces it, then passes". Multi-step work → state a short
  plan, one verify per step. That criterion is what `## Testing Done` records; nothing ran → say so
  plainly, `/clio-memo` files it as `unverified` rather than letting it pass as built.
- IMPORTANT: Do not add code comments unless the user explicitly asks for them.

<!-- Project-specific hard rules go here, as bullets in the list above. Ask the user, don't guess.
     Common ones worth having:
     - Multiple interpretations, or anything touching <money / payment / auth / data deletion> →
       state assumptions and ask.
     - i18n: never hardcode UI text, always `<translate call>`.
     - Timezone: default `<TZ>` — confirm before changing time logic.
     - Money: integer minor units only, never float.
     - Generated files: `<path>` is build output — edit `<source path>` instead.
     - Code search: prefer Grep/Glob tools over `Bash grep`/`find` (matters when a search-augmenter
       hook is installed — it only fires on tool calls). SKIP this bullet if a hook already gates
       Grep/Glob toward a code-graph MCP; two rules pointing opposite ways is worse than neither. -->
