# The stack — `memory/infra.md`, row `0`

Read by `/clio:ingest` on the first run, and on a later run when the source changes a constraint on
the stack.

A spec says what the product must do; it rarely says what it is built with, yet every area plan needs
that settled first. This skill decides the stack **at decision level** — language, framework, build
tool, test runner, and the constraints behind them. `/clio:plan infra` later turns it into the
scaffold and toolchain tasks; it does not choose.

Collect the constraints the source states that bind the stack — platform (web, desktop, mobile),
offline, data volume, latency, hosting, licence, a stack the customer already mandates — each with its
quote. Then one of:

**The repo has code.** Read the manifests and lockfiles; the stack is whatever they pin. Propose
nothing. Write it as `## Decisions` with the exact versions, and every source constraint the current
stack does not visibly meet as a ⚠️.

**The repo is empty.** Research 2–3 candidate stacks that fit the constraints. **Prefer Context7**
(fall back to web search, say which). From each stack's own docs: the scaffold command, build and
test commands, the version they need, the layout they recommend — each with source and the date
read. Show them side by side against the constraints, then **ASK**: the user picks one or names their
own. Never pick silently. Record the choice as an ADR (`${CLAUDE_PLUGIN_ROOT}/skills/memo/steps/WRAP-UP.md`
§ ADR, indexed with `"type":"adr"`, `"domain":"infra"`, `"req":["0"]`, then
`${CLAUDE_PLUGIN_ROOT}/bin/clio validate index`).

Scope stops at what the scaffold needs. A library for a domain — OCR, image processing, an HTTP
client — is chosen in that area's spec or plan, not here; the rows it serves are often still ⚠️.

`memory/infra.md` uses the template of `SKILL.md` § 1; `## Decisions` holds the chosen stack and the
commands the docs gave, `## Source` quotes the constraints and names the ADR.
