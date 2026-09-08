---
name: clio-setup
description: Set up Clio in the current project — scaffold .claude/ (CLAUDE.md, CONTEXT.md, requirements.md, the two ledgers, stack rules), then fill them by asking the user, never guessing. Run once per repository, before any other clio-* skill.
disable-model-invocation: true
---

Install Clio's project memory into the repository at the current working directory. Do every step
yourself with Bash, in order. The user only answers **ASK** items — batch each step's ASKs into one
`AskUserQuestion` call, never guess, never ask permission for an action listed here.

## 0. Before you start

```bash
for t in bash jq git awk; do command -v $t >/dev/null || echo "MISSING: $t"; done
git rev-parse --git-dir 2>/dev/null || echo "NOT A GIT REPO"
ls .claude/clio 2>/dev/null && echo "ALREADY SET UP"
```
- `MISSING` → stop, tell the user. `NOT A GIT REPO` → **ASK** to `git init`; never without a yes.
  `ALREADY SET UP` → say so and stop.
- **ASK:** does the repo already have code, or is it empty (spec only)? Empty = **greenfield**: run
  step 3 before step 2.
- Do not run `/init`. A root `CLAUDE.md` that exists → fold it into `.claude/CLAUDE.md` in step 2 and
  tell the user to delete the root one.

## 1. Scaffold

```bash
T="${CLAUDE_SKILL_DIR}/templates"
mkdir -p .claude/rules .claude/clio .claude/docs/specs/memory .claude/docs/tasks .claude/docs/decisions
[ -f .claude/CLAUDE.md ]                  || cp "$T/CLAUDE.md"       .claude/CLAUDE.md
[ -f .claude/CONTEXT.md ]                 || cp "$T/CONTEXT.md"      .claude/CONTEXT.md
[ -f .claude/docs/specs/requirements.md ] || cp "$T/requirements.md" .claude/docs/specs/requirements.md
touch .claude/clio/index.jsonl .claude/clio/debt.jsonl
ls composer.json go.mod pom.xml build.gradle* pubspec.yaml 2>/dev/null    # php · go · java · java · dart
```
For each stack the last line lists: `[ -f .claude/rules/<stack>.md ] || cp
"${CLAUDE_SKILL_DIR}/rules/<stack>.md" .claude/rules/`. Nothing is ever overwritten. Monorepo: one
`.claude/` at the root; a `domain` names the business area served, never a package.

## 2. `CLAUDE.md` and `CONTEXT.md`

Each fill-in is an HTML comment holding its own instructions.

- `CLAUDE.md`: the harness strips its comments — fill the sections, **keep the comments**. Never
  touch `@CONTEXT.md`, `## Project memory`, or the existing `## Rules` bullets.
- `CONTEXT.md`: reaches context through `@CONTEXT.md`, where comment stripping is not guaranteed —
  fill from the comments, then **delete every comment**. Leave landmine sections empty; incidents
  fill them later.
- Both ≤ ~150 non-blank lines combined; path-specific content → `.claude/rules/` with `paths:`
  frontmatter. A mechanical rule → a hook (step 6), not a bullet.
- **ASK** in one batch: the `domain` vocabulary (e.g. `account checkout admin infra all`) · i18n ·
  timezone · money representation · generated files and their real source · formatter command ·
  anything expensive to get wrong (payment, auth, deletion, PII). Vocabulary → `CLAUDE.md`
  § Project memory; generated paths → `CONTEXT.md` § Source of truth; the rest → `## Rules` bullets.
- **Greenfield:** fill `CONTEXT.md` § Entities/Terms/Key Flows from `docs/specs/memory/*.md`; leave
  § Dev Environment and § Source of truth empty. **ASK** stack + versions, storage, and the
  architectural seam; write them as the opening paragraph plus a one-line § Architecture, and record
  the decision as an ADR (template: `${CLAUDE_PLUGIN_ROOT}/skills/clio-memo/steps/WRAP-UP.md`).

## 3. Requirements

**ASK** which shape:
- **Full** — a requirement source exists. Tell the user to run `/clio-ingest <source>` when this
  setup finishes.
- **Lite** — none. Replace the two tables in `requirements.md` with one line:
  `Lite mode — no requirement source; every record uses req: [] and joins on domain/keywords/files.`

## 4. Stack rules

For each `.claude/rules/<stack>.md` step 1 copied: verify every bullet against the repo (formatter
present? generated paths exist?), fix or drop what does not hold, delete the leading comment.
Uncovered stack → write one, 10–20 lines, `paths:` frontmatter, verified facts only — or none.
**Greenfield:** keep the file unverified and append one `debt.jsonl` record (`kind:"doc-stale"`,
`domain:"all"`, `what:["rules/<stack>.md unverified — written before the scaffold"]`,
`code:[".claude/rules/<stack>.md"]`, `blocked_by:null`; schema in
`${CLAUDE_PLUGIN_ROOT}/skills/clio-memo/steps/DEBT-IT.md`).

## 5. Tooling (optional, ASK once)

```bash
claude mcp list; jq '.enabledPlugins' ~/.claude/settings.json; claude plugin marketplace list
```
List **only what is missing** in one multi-select `AskUserQuestion`, nothing pre-selected:

| Scope | Item | Why |
|---|---|---|
| global MCP | Context7 | library docs on demand instead of remembered APIs |
| global MCP | codebase-memory-mcp | callers and impact from a code graph instead of guessed call chains |
| global plugin | `feature-dev`, `code-review`, `security-guidance` | build / review loop |
| global plugin | `ponytail` (minimal solutions), `caveman` (terse replies) | taste — offer, never pre-select |
| project MCP | Playwright, only if the repo has a browser UI | verify in a real browser |
| project MCP | a DB MCP, only if the repo owns a database — **ASK** which server and connection string | read the real schema |
| global permissions | the strict deny/ask list in `${CLAUDE_SKILL_DIR}/permissions.json` — blocks `rm -rf`, `git push/reset/rebase`, reading `.env`/keys; also denies `git commit` and asks before every `Write` | offer, never pre-select; say what it blocks |

Run what was approved, then `claude mcp list` to verify:
```bash
claude mcp add -s user context7 -- npx -y @upstash/context7-mcp
command -v codebase-memory-mcp >/dev/null && claude mcp add -s user codebase-memory-mcp -- codebase-memory-mcp \
  || echo "codebase-memory-mcp binary missing — ASK the user to install it first"
claude plugin install feature-dev@claude-plugins-official      # confirm names via `claude plugin marketplace list`
claude mcp add -s project playwright -- npx -y @playwright/mcp@latest
```
Permissions, if chosen — union into `~/.claude/settings.json`, existing entries first, backup taken:
```bash
S=~/.claude/settings.json; cp "$S" "$S.bak"
jq --slurpfile p "${CLAUDE_SKILL_DIR}/permissions.json" '
  .permissions.deny = ((.permissions.deny // []) as $e | $e + ($p[0].permissions.deny - $e))
  | .permissions.ask = ((.permissions.ask // []) as $e | $e + ($p[0].permissions.ask - $e))' "$S" > "$S.new" && mv "$S.new" "$S"
```
`ponytail` and `caveman` are always-on once installed. If either is present, **ASK** whether to
keep it on here; to turn one off for this repo only, `jq`-merge into `.claude/settings.json`:
`{ "env": { "CAVEMAN_DEFAULT_MODE": "off", "PONYTAIL_DEFAULT_MODE": "off" } }`.

## 6. Formatter hook (optional)

**ASK** whether to add one to `.claude/settings.local.json`, command from step 4's rules file;
`jq`-merge, never overwrite. Keep only this repo's branches. Greenfield: skip.
```json
{ "hooks": { "PostToolUse": [ { "matcher": "Edit|Write", "hooks": [ { "type": "command", "timeout": 30,
  "command": "f=$(jq -r '.tool_input.file_path // empty'); case \"$f\" in *.php) vendor/bin/pint \"$f\" ;; *.go) gofmt -w \"$f\" ;; *.dart) dart format \"$f\" ;; esac" } ] } ] } }
```

## 7. Verify and stop

```bash
"${CLAUDE_PLUGIN_ROOT}"/skills/clio-memo/scripts/validate.sh all    # ⚠️/✅ notes are expected; a FAIL is not
```
Ask the user to run `/context`: `CLAUDE.md` and `CONTEXT.md` must both appear under **Memory files**.
**ASK** whether `.claude/` is committed (recommended: yes, the ledgers are history). Do not seed the
ledgers beyond what steps 2–4 wrote. From here the loop runs itself: `clio-context` before
non-trivial work, `/clio-memo` after. Nothing reminds the user; say that once.
