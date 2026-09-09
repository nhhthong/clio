---
name: setup
description: Set up Clio in the current project — scaffold .claude/ (CLAUDE.md, CONTEXT.md, requirements.md, the two ledgers, stack rules), then fill them by asking the user, never guessing. Run once per repository, before any other clio:* skill.
disable-model-invocation: true
---

Install Clio's project memory into the repository at the current working directory. Do every step
yourself with Bash, in order. The user answers three `AskUserQuestion` batches (steps 0, 2, 5) and
approves the two drafted files (step 2) — nothing else. Never guess, never ask permission for an
action listed here, never write `CLAUDE.md` or the context file without the step-2 yes.

## 0. Take stock, then ASK batch 1

```bash
for t in bash jq git awk; do command -v $t >/dev/null || echo "MISSING: $t"; done
git rev-parse --git-dir >/dev/null 2>&1 || echo "NOT A GIT REPO"
[ -d .claude/clio ] && echo "ALREADY SET UP"
ls CLAUDE.md .claude/CLAUDE.md .claude/CONTEXT.md 2>/dev/null
```
`MISSING` → stop, tell the user. `ALREADY SET UP` → say so and stop. Do not run `/init`.

**ASK batch 1**, one call, only the items that apply:
- `NOT A GIT REPO` → `git init`? Never without a yes.
- Does the repo already have code, or is it empty (spec only)? Empty = **greenfield**.
- Requirements: **Full** (a requirement document exists — which file?) or **Lite** (none)?
- `CLAUDE.md` / `.claude/CONTEXT.md` / `.claude/rules/` already exist → they are the user's; Clio
  adds only the `@` import and the `## Project memory` block. One extra question: **bring them to
  Clio's format?** — the layout of `${CLAUDE_PLUGIN_ROOT}/skills/setup/templates/CLAUDE.md` and
  `CONTEXT.md`, trimmed to the ~150-line budget, path-specific bullets moved to `rules/`. Yes →
  step 2 shows the diff and asks again before writing. No (default) → nothing else is touched.

## 1. Scaffold

```bash
T="${CLAUDE_PLUGIN_ROOT}/skills/setup/templates"; CTX=.claude/CONTEXT.md
mkdir -p .claude/rules .claude/clio .claude/docs/specs/memory .claude/docs/tasks .claude/docs/decisions .claude/docs/plans
[ -f "$CTX" ]                             || cp "$T/CONTEXT.md"      "$CTX"
[ -f .claude/docs/specs/requirements.md ] || cp "$T/requirements.md" .claude/docs/specs/requirements.md
touch .claude/clio/index.jsonl .claude/clio/debt.jsonl
ls composer.json go.mod pom.xml build.gradle* pubspec.yaml 2>/dev/null    # php · go · java · java · dart
```
For each stack the last line lists: `[ -f .claude/rules/<stack>.md ] || cp
"${CLAUDE_PLUGIN_ROOT}/skills/setup/rules/<stack>.md" .claude/rules/`.

`CLAUDE.md` — no existing one → `cp "$T/CLAUDE.md" .claude/CLAUDE.md`. One exists (root
`CLAUDE.md` wins over `.claude/CLAUDE.md`) → keep it, append only; the import path is relative to
the file that holds it:
```bash
C=.claude/CLAUDE.md; [ -f CLAUDE.md ] && C=CLAUDE.md
IMP="@${CTX#.claude/}"; [ "$C" = CLAUDE.md ] && IMP="@$CTX"
grep -q '^@.*CONTEXT.md' "$C" || printf '\n%s\n\n' "$IMP" >> "$C"
grep -q '^## Project memory' "$C" || awk '/^## Project memory/,0' "$T/CLAUDE.md" >> "$C"
```
Nothing is ever overwritten. Monorepo: one `.claude/` at the root; a `domain` names the business
area served, never a package.

## 2. `CLAUDE.md` and `CONTEXT.md`, then ASK batch 2

Each fill-in is an HTML comment holding its own instructions.

- `CLAUDE.md`: the harness strips its comments — fill the sections, **keep the comments**. Inside
  `## Project memory` change only the Domains line; never touch the import line or the existing
  `## Rules` bullets.
- `CONTEXT.md`: reaches context through the import, where comment stripping is not guaranteed —
  fill from the comments, then **delete every comment**. Leave landmine sections empty; incidents
  fill them later.
- Both ≤ ~150 non-blank lines combined; path-specific content → `.claude/rules/` with `paths:`
  frontmatter. A mechanical rule → a hook (step 6), not a bullet.
- **ASK batch 2**, one call: the `domain` vocabulary (e.g. `account checkout admin infra all`) ·
  i18n · timezone · money representation · generated files and their real source · formatter
  command · anything expensive to get wrong (payment, auth, deletion, PII). Vocabulary → the
  Domains line; generated paths → `CONTEXT.md` § Source of truth; the rest → `## Rules` bullets.
- **Greenfield:** fill `CONTEXT.md` § Entities/Terms/Key Flows straight from the requirement
  document named in batch 1 (nothing else exists yet); leave § Dev Environment and § Source of
  truth empty. Add to batch 2: stack + versions, storage, the architectural seam; write them as the
  opening paragraph plus a one-line § Architecture, and record the decision as an ADR (template:
  `${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/WRAP-UP.md`).
- **Draft, show, ASK — then write.** Both files are drafted in full from the batch-2 answers and
  what the repo verifiably shows (`ls`, manifests, existing docs; nothing inferred). Print each
  draft whole, then one `AskUserQuestion`: approve as-is · edit (which lines) · leave that file's
  section empty. Write only what was approved. These two files load every session; a wrong line is
  paid on every future task, so a guess here is the one thing this skill must never do.
- **Existing files, batch 1 said yes to the format:** re-lay each file on the template's headings,
  keep every bullet the user wrote (move path-specific ones to `.claude/rules/<stack>.md` with
  `paths:`), cut nothing without naming it in the diff. Show the diff, ASK, write on a yes. Batch 1
  said no → step 1's append is all that happens; skip this step for those files.

## 3. Requirements

- **Full** → tell the user to run `/clio:ingest <file>` when this setup finishes, then
  `/clio:plan <area>` per area to get the testable task list.
- **Lite** → replace everything below the title in `requirements.md` with one line:
  `Lite mode — no requirement source; every record uses req: [] and joins on domain/keywords/files.`

## 4. Stack rules

For each `.claude/rules/<stack>.md` step 1 copied: verify every bullet against the repo (formatter
present? generated paths exist?), fix or drop what does not hold, delete the leading comment.
Uncovered stack → write one, 10–20 lines, `paths:` frontmatter, verified facts only — or none.
**Greenfield:** keep the file unverified and append one `debt.jsonl` record (`kind:"doc-stale"`,
`domain:"all"`, `what:["rules/<stack>.md unverified — written before the scaffold"]`,
`code:[".claude/rules/<stack>.md"]`, `blocked_by:null`; full schema in
`${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/DEBT-IT.md`).

## 5. Tooling, then ASK batch 3

```bash
claude mcp list; jq '.enabledPlugins' ~/.claude/settings.json; claude plugin marketplace list
```
**ASK batch 3**, one multi-select call, nothing pre-selected, listing **only what is missing**:

| Scope | Item | Why |
|---|---|---|
| global MCP | Context7 | library docs on demand instead of remembered APIs |
| global MCP | codebase-memory-mcp | callers and impact from a code graph instead of guessed call chains |
| global plugin | `feature-dev`, `code-review`, `security-guidance` | build / review loop |
| global plugin | [`ponytail`](https://github.com/DietrichGebert/ponytail) (laziest working solution, YAGNI), [`caveman`](https://github.com/JuliusBrussee/caveman) (terse replies, fewer tokens) | taste — offer, never pre-select |
| project MCP | Playwright, only if the repo has a browser UI | verify in a real browser |
| project MCP | a DB MCP, only if the repo owns a database — ask which server and connection string | read the real schema |
| global permissions | the strict deny/ask list in `${CLAUDE_PLUGIN_ROOT}/skills/setup/permissions.json` — blocks `rm -rf`, `git push/reset/rebase`, reading `.env`/keys; also denies `git commit` and asks before every `Write` | offer, say what it blocks |
| this repo | formatter hook (step 6), if step 4's rules name a formatter | |
| this repo | commit `.claude/` (recommended: the ledgers are history) or ignore `.claude/clio/` and `.claude/docs/` | |
| this repo | `ponytail` / `caveman` already installed → keep them on here? | they are always-on everywhere via a SessionStart hook |

Run what was approved, then `claude mcp list` to verify:
```bash
claude mcp add -s user context7 -- npx -y @upstash/context7-mcp
command -v codebase-memory-mcp >/dev/null && claude mcp add -s user codebase-memory-mcp -- codebase-memory-mcp \
  || echo "codebase-memory-mcp binary missing — ask the user to install it first"
claude plugin install feature-dev@claude-plugins-official      # confirm names via `claude plugin marketplace list`
claude plugin marketplace add DietrichGebert/ponytail && claude plugin install ponytail@ponytail
claude plugin marketplace add JuliusBrussee/caveman  && claude plugin install caveman@caveman
claude mcp add -s project playwright -- npx -y @playwright/mcp@latest
```
Permissions — union into `~/.claude/settings.json`, existing entries first, backup taken:
```bash
S=~/.claude/settings.json; cp "$S" "$S.bak"
jq --slurpfile p "${CLAUDE_PLUGIN_ROOT}/skills/setup/permissions.json" '
  .permissions.deny = ((.permissions.deny // []) as $e | $e + ($p[0].permissions.deny - $e))
  | .permissions.ask = ((.permissions.ask // []) as $e | $e + ($p[0].permissions.ask - $e))' "$S" > "$S.new" && mv "$S.new" "$S"
```
Turn `ponytail` / `caveman` off for this repo only — `jq`-merge into `.claude/settings.json`:
`{ "env": { "PONYTAIL_DEFAULT_MODE": "off", "CAVEMAN_DEFAULT_MODE": "off" } }` (caveman also reads
a committed `.caveman.json` with `{"defaultMode":"off"}`). Mid-session: `/ponytail off`, `/caveman off`.

## 6. Formatter hook

Only if chosen in batch 3. `jq`-merge into `.claude/settings.local.json`, never overwrite; keep only
this repo's branch; command from step 4's rules file. Greenfield: skip.
```json
{ "hooks": { "PostToolUse": [ { "matcher": "Edit|Write", "hooks": [ { "type": "command", "timeout": 30,
  "command": "f=$(jq -r '.tool_input.file_path // empty'); case \"$f\" in *.php) vendor/bin/pint \"$f\" ;; *.go) gofmt -w \"$f\" ;; *.dart) dart format \"$f\" ;; esac" } ] } ] } }
```

## 7. Verify and stop

```bash
"${CLAUDE_PLUGIN_ROOT}"/skills/memo/scripts/validate.sh all    # open-row notes are expected; a FAIL is not
```
Ask the user to run `/context`: `CLAUDE.md` and the context file must both appear under **Memory
files**. Do not seed the ledgers beyond what steps 2–4 wrote. From here the loop runs itself:
`clio:context` before non-trivial work, `/clio:memo` after. Nothing reminds the user; say that once.
