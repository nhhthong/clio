# Changelog

## 1.0.2 — 2026-09-08

- Skills renamed to `setup`, `context`, `memo`, `update`, `ingest`, `debt`, `ask`. Plugin skills are
  namespaced by Claude Code, so the commands are `/clio:memo`, `/clio:debt` and so on; the old
  `clio-` prefix doubled the name.

## 1.0.1 — 2026-09-08

- `/clio:setup` gained a tooling step: it lists missing MCP servers and plugins once and installs
  only what you pick.
- No hooks; one script (the validator); no test suite. The strict permission list is back as an
  opt-in ASK inside the tooling step. `clio:update` and
  `clio:ingest` are single files.

## 1.0.0 — 2026-09-08

First release as a Claude Code plugin.
