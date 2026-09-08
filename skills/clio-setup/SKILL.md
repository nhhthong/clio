---
name: clio-setup
description: Set up Clio in the current project — scaffold .claude/ (CLAUDE.md, CONTEXT.md, requirements.md, the two ledgers, stack rules), then fill them by asking the user, never guessing. Run once per repository, before any other clio-* skill.
disable-model-invocation: true
---

You are installing Clio's project-memory structure into the repository at the current working
directory. Do every step yourself with Bash, in order. The user only answers **ASK** items — batch
each step's ASKs into one `AskUserQuestion` call, never guess, never ask permission for an action
listed here.

Plugin root: `${CLAUDE_PLUGIN_ROOT}`. Templates: `${CLAUDE_SKILL_DIR}/templates/`.

## 0. Before you start

```bash
for t in bash jq git awk; do command -v $t >/dev/null || echo "MISSING: $t"; done
git rev-parse --git-dir 2>/dev/null || echo "NOT A GIT REPO"
ls .claude/clio 2>/dev/null && echo "ALREADY SET UP"
```
- `MISSING` → stop, tell the user. `NOT A GIT REPO` → **ASK** to `git init` (ledgers are append-only
  and rely on `git log`); never `git init` without a yes. `ALREADY SET UP` → say so and stop; there
  is nothing to redo, and `/clio-memo` handles CONTEXT.md updates from here on.
- A `database/` dir under `.claude/` (pre-plugin skeleton) exists → run
  `"${CLAUDE_PLUGIN_ROOT}"/scripts/migrate.sh .`, show its output, stop.
- **ASK:** does the repo already have code, or is it empty (spec only)? Empty = **greenfield**: do
  step 3 before step 2 and follow the greenfield lines.
- Do not run `/init`. A root `CLAUDE.md` that exists → fold into `.claude/CLAUDE.md` in step 2, then
  tell the user to delete the root one (you cannot delete files).

## 1. Scaffold

```bash
"${CLAUDE_PLUGIN_ROOT}"/scripts/scaffold.sh .
```
Creates only what is missing, never overwrites. Monorepo: one `.claude/` at the root; a `domain`
term names the business area served, never a package name. **ASK** only if packages have separate
requirement sources — that is the one case for separate `.claude/` trees.

## 2. `CLAUDE.md` and `CONTEXT.md`

Both exist now; each fill-in is an HTML comment holding its own instructions.

- `CLAUDE.md`: the harness strips its comments — fill the sections, **keep the comments**. Never
  touch `@CONTEXT.md`, `## Project memory`, or the existing `## Rules` bullets.
- `CONTEXT.md`: reaches context only through `@CONTEXT.md`; comment stripping is not guaranteed —
  fill from the comments, then **delete every comment**. Leave landmine sections empty.
- Budget: both ≤ ~150 non-blank lines combined. Path-specific content → `.claude/rules/` with
  `paths:` frontmatter.
- Check installed hooks/plugins before writing `## Rules`; drop any bullet that contradicts one:
  ```bash
  jq '{hooks: [.hooks // {} | .[][] | .hooks[].command], plugins: .enabledPlugins}' ~/.claude/settings.json
  ```
- Mechanical rule → a hook (step 6) or `permissions.deny`, not a bullet.
- **ASK** in one batch: the `domain` vocabulary (e.g. `account checkout admin infra all`; game:
  `gameplay ui assets netcode save`; CRM: `leads pipeline contacts`) · i18n · timezone · money
  representation · generated files and their real source · formatter command · anything expensive
  to get wrong (payment, auth, deletion, PII). Write the vocabulary into `CLAUDE.md`
  § Project memory, generated paths into `CONTEXT.md` § Source of truth.
- **Greenfield:** fill `CONTEXT.md` § Entities/Terms/Key Flows from `docs/specs/memory/*.md`
  (step 3 already ran); leave § Dev Environment and § Source of truth empty. **ASK** stack +
  versions, storage, and the architectural seam; write them as the opening paragraph plus a
  one-line § Architecture, record the same decision as `.claude/docs/decisions/<today>_stack.md`
  (template: `${CLAUDE_PLUGIN_ROOT}/skills/clio-memo/steps/WRAP-UP.md` § ADR) and index it per
  `${CLAUDE_PLUGIN_ROOT}/skills/clio-memo/steps/INDEX-IT.md` with `"type":"adr"`, `req:[]`,
  `domain:"all"`.

## 3. Requirements → `.claude/docs/specs/requirements.md`

**ASK** which shape:
- **Full** — a requirement source exists. Tell the user to run `/clio-ingest <source>` after this
  setup finishes; do not walk it yourself here.
- **Lite** — no requirement document. Replace the two tables in `requirements.md` with one line:
  `Lite mode — no requirement source; every record uses req: [] and joins on domain/keywords/files.`

## 4. Stack rules — `.claude/rules/`

`scaffold.sh` copied a starter only for stacks it detected (`composer.json`, `go.mod`,
`pom.xml`/`build.gradle*`, `pubspec.yaml`). For each file present: verify every bullet against the
repo (formatter present? generated paths exist?), fix or drop what does not hold, delete the leading
comment. Uncovered stack → write `rules/<stack>.md`, 10–20 lines, `paths:` frontmatter, verified
facts only — or none. **Greenfield:** keep the chosen stack's file, skip verification, append one
`debt.jsonl` record (schema: `${CLAUDE_PLUGIN_ROOT}/skills/clio-memo/steps/DEBT-IT.md`):
`kind:"doc-stale"`, `domain:"all"`, `what:["rules/<stack>.md unverified — written before the
scaffold","wire the formatter PostToolUse hook"]`, `code:[".claude/rules/<stack>.md"]`,
`blocked_by:null`.

## 5. Tooling (optional, ASK once)

Stack-dependent → project scope; user-dependent → global. Take stock first, then list **only what is
missing** in one `AskUserQuestion` (multi-select, nothing pre-selected), and run what was approved:
```bash
claude mcp list; jq '.enabledPlugins' ~/.claude/settings.json; claude plugin marketplace list
```

| Scope | Item | Why |
|---|---|---|
| global MCP | Context7 | library docs on demand instead of remembered APIs |
| global MCP | codebase-memory-mcp | code graph for callers/impact instead of guessed call chains |
| global plugin | `feature-dev`, `code-review`, `security-guidance` | build / review loop |
| global plugin | `ponytail` (minimal solutions), `caveman` (terse replies) | behaviour, taste — offer, never pre-select |
| project MCP | Playwright — only if the repo has a browser UI | verify in a real browser |
| project MCP | a DB MCP — only if the repo owns a database; **ASK** which server and connection string, never pick a package yourself | read the real schema |

Cap global MCP at 3–4. Skip Serena if codebase-memory-mcp is installed.
```bash
claude mcp add -s user context7 -- npx -y @upstash/context7-mcp
command -v codebase-memory-mcp >/dev/null && claude mcp add -s user codebase-memory-mcp -- codebase-memory-mcp \
  || echo "codebase-memory-mcp binary missing — ASK the user to install it first"
claude plugin install feature-dev@claude-plugins-official      # confirm marketplace names via `claude plugin marketplace list`
claude plugin install ponytail@<marketplace>                   # only if chosen; same for caveman
claude mcp add -s project playwright -- npx -y @playwright/mcp@latest
claude mcp list                                                # verify what resolved
```
codebase-memory-mcp indexes on first use: in the next session, call its `index_repository` tool once.

Behaviour plugins with a `SessionStart` hook (`caveman`, `ponytail`) are always-on everywhere once
installed. If either is installed, **ASK** whether to keep it on for this repo; to turn one off here
only, `jq`-merge into `.claude/settings.json` (never overwrite):
```json
{ "env": { "CAVEMAN_DEFAULT_MODE": "off", "PONYTAIL_DEFAULT_MODE": "off" } }
```

## 6. Formatter hook (optional)

**ASK** whether to add a formatter hook to `.claude/settings.local.json`, command from step 4's
rules file. Merge with `jq` into the existing JSON, never overwrite:
```json
{ "hooks": { "PostToolUse": [ { "matcher": "Edit|Write", "hooks": [ { "type": "command", "timeout": 30,
  "command": "f=$(jq -r '.tool_input.file_path // empty'); case \"$f\" in *.php) vendor/bin/pint \"$f\" ;; *.go) gofmt -w \"$f\" ;; *.dart) dart format \"$f\" ;; esac" } ] } ] } }
```
Keep only this repo's branches. **Greenfield:** skip — the step-4 debt record carries it.

A stricter permission set is available at `${CLAUDE_PLUGIN_ROOT}/docs/permissions.example.json`;
mention it once, do not merge it unless asked.

## 7. Verify and stop

```bash
"${CLAUDE_PLUGIN_ROOT}"/scripts/validate.sh all    # ⚠️/✅ requirements.md notes are expected; any FAIL is not
```
Ask the user to run `/context` — `CLAUDE.md` and `CONTEXT.md` must both appear under **Memory
files**. **ASK** whether `.claude/` is committed (recommended: yes, the ledgers are history) or
ignored. Do not seed the ledgers beyond what steps 2–4 wrote. The loop now runs itself:
`clio-context` before non-trivial work, the Stop hook after, `session-debt` at start, `/clio-memo`
proposing a `CONTEXT.md` diff when nudged. Greenfield: the first `/clio-memo` is the scaffold —
record the scaffold command, re-verify `rules/<stack>.md`, close the `doc-stale` record.
