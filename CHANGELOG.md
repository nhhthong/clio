# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [1.0.1] — 2026-09-08

### Added
- `/clio-setup` step 5 *Tooling*: takes stock of installed MCP servers and plugins, then offers the
  missing ones in a single multi-select question (Context7, codebase-memory-mcp, `feature-dev`,
  `code-review`, `security-guidance`, `ponytail`, `caveman`, Playwright / DB MCP per stack). Nothing
  is pre-selected, nothing is installed without a yes.

## [1.0.0] — 2026-09-08

First release as a Claude Code plugin. Previously a copy-into-project skeleton.

### Added
- Plugin manifest, marketplace entry, `hooks/hooks.json` — install with one command, update with one command.
- Skills `clio-setup`, `clio-context`, `clio-memo`, `clio-update`, `clio-ingest`, `clio-debt`, `clio-ask`.
- `scripts/scaffold.sh` (data files only, stack rules copied only for detected stacks).
- `scripts/migrate.sh` for projects set up with the old skeleton.

### Changed
- Commands became skills; step files live inside each skill, referenced via `${CLAUDE_SKILL_DIR}`.
- `validate.sh` ships in the plugin and is no longer copied into projects.
- Renamed: `.claude/database/` → `.claude/clio/`, `routes.md` → `requirements.md`,
  field `est` → `req`, field `folder` → `domain`, hook `feature-done-reminder` → `memo-reminder`.
- Project-specific vocabulary (domains, generated paths) now lives in the project's `CLAUDE.md` /
  `CONTEXT.md` instead of inside step files.

### Removed
- `setup.sh`, `upgrade.sh`, `install-global.sh`, `merge-settings.sh`, `hooks.json.example`, `TUTORIAL.md`.

### Fixed
- `clio-update` wrap-up told the agent to rewrite a debt line in place; the ledger is append-only.
