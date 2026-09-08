<!-- HOW TO FILL THIS FILE
     This file reaches every session through the `@CONTEXT.md` import in CLAUDE.md, and comment
     stripping is NOT guaranteed on imported files. Fill each section from its comment, then DELETE
     every HTML comment (this one included). Stable facts only: entities, flows, landmines. Task
     history belongs in .claude/docs/tasks/. Later writes go through /clio:memo, which proposes a
     diff and waits for a yes. -->

# Domain Context

**No speculation, no hallucination — ask if unsure.** Full rule in `.claude/CLAUDE.md` § Rules;
applies to everything in this file too.

## Dev Environment

<!-- Start/stop commands, services, ports. Then the landmines — but ONLY ones that already cost
     someone a session. Leave empty at setup; real incidents fill it. -->

## Core Entities

<!-- 1–3 lines each. Name the trap, not the schema: "two models share this table", "this column is
     not a FK". Link the ADR that explains it: `decisions/<file>.md`. -->

## Terms that mean two different things

<!-- The highest-value section. For each collision: both meanings, where each lives, and the rule
     for not conflating them. Delete the heading if the domain has none. -->

## Key Flows

<!-- The 5–10 routes, commands or jobs that matter. One line each. -->

## Source of truth

<!-- Generated vs hand-edited paths: what overwrites what, and the build command that does it.
     Delete the heading if nothing in the repo is generated. -->
