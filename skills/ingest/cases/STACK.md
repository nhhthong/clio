# The stack: `memory/infra.md`, row 0

Read on the first run, and on a later run when the source changes a constraint on the stack.

A spec says what the product must do and rarely what it is built with. Do not choose the stack here and do not plan or build anything for it: a stack chosen before any area is planned is the first thing a moving spec throws away. `/clio:plan <area>` diagnoses the toolchain when an area first needs it ([../../plan/cases/SCAFFOLD.md](../../plan/cases/SCAFFOLD.md)).

Collect the constraints the source states that bind the stack, each with its quote: platform, offline use, data volume, latency, hosting, licence, a stack the customer mandates. Then take one branch.

**The repo has code.** Read the manifests and lockfiles. The stack is what they pin, so propose nothing. Write it under `## Decisions` with exact versions. Every source constraint the current stack does not visibly meet becomes an open point.

**The repo is empty.** Write the constraints only, and under `## Decisions` one line: "Stack not chosen; `/clio:plan` proposes candidates when the first area is planned." The row 0 marker is ✅, because the decision is when, not what.

`memory/infra.md` follows [../SPEC-FORMAT.md](../SPEC-FORMAT.md). `## Source` quotes the constraints.
