# Changelog

## 1.0.2 — 2026-09-08

- Skills renamed to `setup`, `context`, `memo`, `update`, `ingest`, `debt`, `ask`. Plugin skills are
  namespaced by Claude Code, so the commands are `/clio:memo`, `/clio:debt` and so on; the old
  `clio-` prefix doubled the name.
- `/clio:setup` keeps an existing `CLAUDE.md` (root or `.claude/`) and appends only what Clio
  needs; asks what to do with an existing `.claude/CONTEXT.md`; three question batches instead of
  six; greenfield fills context from the requirement document itself; real install commands and
  per-repo off switches for `ponytail` and `caveman`.
- `validate.sh` no longer counts CLAUDE.md lines or needs perl.

## 1.0.1 — 2026-09-08

- `/clio:setup` gained a tooling step: it lists missing MCP servers and plugins once and installs
  only what you pick.
- No hooks; one script (the validator); no test suite. The strict permission list is back as an
  opt-in ASK inside the tooling step. `clio:update` and
  `clio:ingest` are single files.

## 1.0.0 — 2026-09-08

First release as a Claude Code plugin.
