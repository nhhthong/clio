# The stack: `memory/infra.md`, row 0

Read on the first run, and on a later run when the source changes a constraint on the stack.

A spec says what the product must do and rarely what it is built with, yet every area plan needs that settled first. Decide the stack at decision level: language, framework, build tool, test runner, and the constraints behind them. `/clio:plan infra` turns it into scaffold tasks. It does not choose.

Collect the constraints the source states that bind the stack, each with its quote: platform, offline use, data volume, latency, hosting, licence, a stack the customer mandates. Then take one branch.

**The repo has code.** Read the manifests and lockfiles. The stack is what they pin, so propose nothing. Write it under `## Decisions` with exact versions. Every source constraint the current stack does not visibly meet becomes an open point.

**The repo is empty.** Research 2 or 3 candidate stacks that fit the constraints, using Context7 first and web search as fallback (say which). From each stack's own docs take the scaffold command, build and test commands, required version and recommended layout, each with its source and the date read. Show them side by side against the constraints, then ask. The user picks one or names their own. Never pick silently. Record the choice as an ADR (`${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/WRAP-UP.md`, section ADR), indexed with `clio add index` as type `adr`, domain `infra`, req `["0"]`.

Stop at what the scaffold needs. A library for one domain (OCR, imaging, an HTTP client) belongs to that area's spec or plan, because the rows it serves are often still open.

`memory/infra.md` follows [../SPEC-FORMAT.md](../SPEC-FORMAT.md). `## Decisions` holds the chosen stack and the commands the docs gave. `## Source` quotes the constraints and names the ADR.
