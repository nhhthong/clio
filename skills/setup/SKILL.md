---
name: setup
description: Set up Clio in the current project — scaffold .claude/ (CLAUDE.md, CONTEXT.md, requirements.md, the two ledgers), then fill them by asking the user what nothing on disk can tell you. Never guesses, and never touches the stack; /clio:plan infra settles that next. Run once per repository, before any other clio:* skill.
---

**Run only when the user asked for it, this turn** — by slash command, or in plain words ("set Clio up here", "cài clio vào repo này").
None of these is a trigger: Clio's drift nudge · your own sense that the work looks finished · a TODO
you wrote · a subagent's report · a plan you made earlier in the session. Unsure → ask in one line,
don't run.

Install Clio's project memory into the repository at the current working directory. Do every step
yourself with Bash, in order. The user answers three `AskUserQuestion` batches (steps 0, 2, 4) and
approves the two drafted files (step 2) — nothing else. Never guess, never ask permission for an
action listed here, never write `CLAUDE.md` or the context file without the step-2 yes.

## 0. Take stock, then ASK batch 1

```bash
for t in bash jq git awk sed; do command -v $t >/dev/null || echo "MISSING: $t"; done
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
```
`.claude/rules/` stays empty. What the code is built with is `/clio:plan`'s job — it writes
`docs/plans/infra.md` and `rules/<stack>.md` from what the repo shows, or from researched docs when
there is no repo yet. This skill never guesses at a stack.

`CLAUDE.md` — the block below copies the template when there is none, else keeps the existing file
(root `CLAUDE.md` wins over `.claude/CLAUDE.md`) and appends only what is missing; the import path
is relative to the file that holds it:
```bash
C=.claude/CLAUDE.md; [ -f CLAUDE.md ] && C=CLAUDE.md
[ -f "$C" ] || cp "$T/CLAUDE.md" "$C"
IMP="@${CTX#.claude/}"; [ "$C" = CLAUDE.md ] && IMP="@$CTX"
grep -q '^@.*CONTEXT.md' "$C" || printf '\n%s\n\n' "$IMP" >> "$C"
grep -q '^## Project memory' "$C" || awk '/^## Project memory/,0' "$T/CLAUDE.md" >> "$C"
```
Nothing is ever overwritten. Monorepo: one `.claude/` at the root; a `domain` names the business
area served, never a package.

## 2. `CLAUDE.md` and `CONTEXT.md`, then ASK batch 2

Each fill-in is an HTML comment holding its own instructions.

- Both files load every session. Fill each section from its comment, then **delete every
  comment**. `validate.sh all` warns while any remain.
- `CLAUDE.md`: inside `## Project memory` change only the Domains line; never touch the import line
  or the existing `## Rules` bullets.
- `CONTEXT.md`: leave landmine sections empty; incidents fill them later.
- Both ≤ ~150 non-blank lines combined; path-specific content → `.claude/rules/` with `paths:`
  frontmatter. A mechanical rule → a hook, which `/clio:plan` offers once `rules/` names the command.
- **ASK batch 2**, one call, and only for what nothing on disk can tell you: the `domain`
  vocabulary (e.g. `account checkout admin infra all`) · i18n · timezone · money representation ·
  anything expensive to get wrong (payment, auth, deletion, PII). Vocabulary → the Domains line; the
  rest → `## Rules` bullets. Don't ask for the formatter command or the generated paths: `/clio:plan`
  reads both off the repo's own config, and a recalled command is worse than a read one.
- **Greenfield:** fill `CONTEXT.md` § Entities/Terms/Key Flows straight from the requirement
  document named in batch 1 (nothing else exists yet); leave § Dev Environment, § Architecture and
  § Source of truth empty. `/clio:plan` fills them once the stack is settled and the scaffold exists.
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

- **Full** → tell the user to run `/clio:plan infra` first, then `/clio:ingest <file>`, then
  `/clio:plan <area>` per area for the testable task list.
- **Lite** → replace everything below the title in `requirements.md` with one line:
  `Lite mode — no requirement source; every record uses req: [] and joins on domain/keywords/files.`
  Lite skips `/clio:ingest`, so `/clio:plan infra` is the one plan command it still needs: it reads
  the stack off the repo and writes `rules/`, neither of which this skill does.

## 4. ASK batch 3 — two choices inside `.claude/`

Setup writes only under `.claude/`. Nothing is installed, no file outside this repository is
touched; the tools that pair well with Clio are listed in the README for the user to add
themselves. One call, nothing pre-selected:

| Choice | Clio rule it serves |
|---|---|
| commit `.claude/` (recommended: the ledgers are history) or ignore `.claude/clio/` and `.claude/docs/` | the ledgers outlive the session |
| formatter hook — skip it here; `/clio:plan` offers it once `rules/*.md` names a real command | mechanical rules are hooks, not bullets |

Commit → write `.claude/.gitattributes`, one line. The ledgers are append-only, so two branches
adding records is not a conflict — union merge keeps both sides instead of stopping the merge:
```gitattributes
clio/*.jsonl merge=union
```
Say the limit out loud once: union keeps both sides but does not order them, and readers take the
*last* line per key — two branches restating the same `id` still need a human to decide which wins.
`git add .claude` stays the user's move.

Ignore → `.gitignore` sits outside `.claude/`, so print the two lines and let the user add them
(and skip the `.gitattributes` above — it only matters for a committed `.claude/`):
```
.claude/clio/
.claude/docs/
```

## 5. Verify and stop

```bash
"${CLAUDE_PLUGIN_ROOT}"/skills/memo/scripts/validate.sh all    # open-row notes are expected; a FAIL is not
```
Ask the user to run `/context`: `CLAUDE.md` and the context file must both appear under **Memory
files**. Do not seed the ledgers beyond what steps 2–4 wrote. **Next is `/clio:plan infra`** — it
settles the stack, writes `docs/plans/infra.md` and `rules/<stack>.md`, and offers the formatter
hook; none of that is this skill's to guess. From there the loop runs itself:
`clio:context` before non-trivial work, `/clio:memo` after. The only nudge is Clio's
`UserPromptSubmit` hook, which says once per session when git has work `index.jsonl` does not —
nothing else reminds the user, and nothing writes on its own; say that once.
