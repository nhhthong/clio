# Levels — which a task needs, and what each must cover

`/clio:plan` reads **Choosing** to fill a task's `Levels` cell. `/clio:test` reads only the catalog
sections that cell names. Sources: Microsoft ISE Engineering Playbook (automated testing, CDC, fault
injection, performance), OWASP WSTG (security, business logic), Pact docs (when contract testing fits).

## Choosing

Risk → question → level. Ask every question against what `/clio:plan` § 2 found in the code and the
spec, not against habit. A task usually answers yes to several; each yes is a level.

| # | Question about this task | Yes when § 2 found… | Level |
|---|---|---|---|
| 1 | Does it hold logic of its own? | a branch, calculation, validation or transformation | `unit` |
| 2 | Does it read or write a real store, queue or file? | a repository, query, migration, message publish | `integration` |
| 3 | Does it add or change a route a client calls? | a handler, router entry, GraphQL resolver, CLI command | `api` |
| 4 | Does another service we can name call it, or does it call one? | a client/SDK for an internal service, a consumed topic | `contract` |
| 5 | Does it complete a flow the spec names end to end? | the spec's key-flow list includes it | `e2e` |
| 6 | Can the same request arrive twice (retry, double submit, redelivery)? | a POST/PUT with side effects, a queue consumer, a webhook | `idempotency` |
| 7 | Can two actors change the same record at once? | shared row/counter/file, no lock or version check yet | `concurrency` |
| 8 | Does it cross a trust boundary? | outside input, an auth or ownership check, a secret | `security` |
| 9 | Does the spec say what happens when a dependency fails? | a timeout, retry, fallback or circuit rule in `## Decisions` | `resilience` |
| 10 | Does the spec state a latency or throughput number? | p95, req/s | `perf` |
| 11 | Does the spec state an expected load or a limit? | concurrent users, N minutes, a max | `load`, `stress` |
| 12 | Is it a bug fix or a revert? | a `code-debt` or `spec-delta` record | `regression` |
| 13 | Is it toolchain or scaffold? | an `infra` task | `smoke` |

Not a question — derived:
- **Critical** → prefix `critical ·` when a bug here would corrupt shared state, grant access it
  should not, or destroy something — money, auth, deletes and two writers on one record are the
  usual shapes, not the whole list. Every case must then have been seen red.
- **Beyond critical** → for a task already `critical`, propose `mutation` and **ASK**; never add it
  yourself. Assess the task, not its domain. Of a bug that slips past every case the other levels
  will have, ask:
  1. **Persists** — does it leave wrong state that stays and compounds (a count, balance, quota,
     stock, reservation, seat or slot)?
  2. **Silent** — would it go unnoticed until a reconciliation, a customer or an audit?
  3. **Hard to undo** — could it be shipped, charged, booked, sent or spread to other records first?
  4. **Mutable logic** — does the rule live in a hand-written comparison, branch, arithmetic or
     loop? No if it is held by a lock, annotation, DB constraint, schema or config (prove those
     with `concurrency` / `integration`), or by a constant (`LIMIT = 5`): default mutators do not
     change constants, so a unit case at the exact boundary proves it instead.
  Q4 yes and at least two of Q1–Q3 → propose, with the four answers as the reason. Money moved, a
  ledger written, stock or seats oversold are typical, not the rule. Declined → no `mutation`, no
  `Not applicable` line, not asked again on re-plan. `Mutation: none` in `plans/infra.md` → do not
  propose; say which task would have qualified.
- **Transaction / isolation** is not its own level: rollback and constraints are `integration`
  cases; two transactions on one row are `concurrency` cases.

Where a yes still does not earn the level:
- `contract` — the consumer cannot be named (a public API), the other side will not run the
  contract, or the route only passes requests through. Use `api` instead.
- `e2e` — the flow is not in the spec's key flows. Few and slow; cover the pieces with `api`.
- `perf` `load` `stress` `resilience` — no number or behaviour in the spec → no level; the gap is a
  ⚠️ (`spec-blocked`). Never invent a threshold or a fallback.

**Not applicable.** A question whose trigger § 2 did find, answered no anyway — a POST that is
naturally idempotent, a route that reads only immutable data — goes under the plan table as
`- <task> · <level> — <reason>`. Silence means the trigger was absent.

## unit
One class or function through its public signature (`UserService.createUser()`).
- The happy path with a value from the spec · each boundary the spec names (min, max, max+1, empty,
  zero) · each error the spec lists, asserting the error type or code, not just "throws".
- No DB, network, clock or randomness — inject them.

## integration
Several real components together: service + repository + a real database (container, not a mock).
- Write then read back through the public seam · the transaction rolls back on failure and leaves no
  partial write · a constraint the schema enforces (unique, FK, not null) surfaces as the domain
  error the spec expects.
- Each test owns its data: fresh schema or a transaction rolled back after it.

## api
The endpoint as a client sees it (`POST /users`).
- Status, body shape and every field the spec lists · each validation error with its status and
  message · pagination, filtering, sorting at the limits the spec states.
- Auth outcomes here are status checks only; attacks on them belong to `security`.

## e2e
A whole flow from the spec's key flows (login → cart → pay), through the real UI or public API.
- The flow completes · the one failure in the middle the spec cares about most (payment declined)
  leaves the system in the state the spec says.

## contract
The API between two services (Order ↔ Payment), consumer-driven.
- Consumer side: the requests it sends and the responses it relies on, as a contract file.
- Provider side: verifies that contract against the running provider, with its state set up per
  interaction. Both must run, or it is not a contract test.

## idempotency
The same operation delivered more than once.
- Same request (same idempotency key, or same message id) N times → one effect, and every reply
  matches the first.
- Same key with a different body → the error the spec defines, not a second effect.
- Redelivery after a crash between the effect and the ack → still one effect.
Assert the state (one row, one charge), never just the status code.

## concurrency
Two or more actors on the same thing at once. `Repeat` ≥ 20, race detector on (`go test -race`,
TSan, `-Djdk…`), interleaving forced with a barrier or latch.
- **Lost update**: two writers, both changes survive or one gets a conflict error.
- **Double effect**: two identical requests released together → exactly one order, one charge.
- **Invariant**: a balance never negative, a stock count never below zero, under N parallel buyers.
- **Isolation**: a reader never sees another transaction's partial write.
- **Deadlock**: two resources locked in opposite order finish within a timeout.
- **Ordering**: events processed out of order end in the state the spec defines.
Every case asserts the invariant after all actors finish, never just "no error".

## security
Everything that crosses a trust boundary (OWASP WSTG categories).
- AuthN: no token, expired token, token signed with the wrong key, `alg: none` → rejected.
- AuthZ: user A reads/edits/deletes user B's resource by changing an id → 403/404 (horizontal);
  each role the spec names against each action it must not do (vertical).
- Session: logout and expiry invalidate the token; a fixed session id is not accepted.
- Input: SQL/NoSQL/command injection, path traversal, SSRF in a URL field, oversized payload, an
  upload of the wrong type, script in a stored field rendered back — rejected or escaped.
- Errors: no stack trace, query text, secret or PII in a response body or a log line.
- Business logic: a step skipped or replayed (pay twice, reuse a one-time code) is refused.

## resilience
A dependency fails the way the spec anticipates: timeout, 5xx, connection refused, slow response.
- Fault injected at the seam the task does not own (a stub server, a toxiproxy, a mock of the
  third-party client) — never by mocking the task's own code.
- The spec's behaviour holds: the retry count and back-off, the fallback value, the error surfaced
  to the caller, no partial write · it recovers once the dependency is back.

## perf
Latency and throughput of one operation, **only with a number from the spec** (p95 < 200 ms, 1,000
req/s). The command exits non-zero when the threshold is missed.

## load
The system at the load the spec expects (500 concurrent users, N minutes).
- Error rate and latency percentiles stay inside the spec's numbers for the whole run.
- Spike (sudden jump) or soak (hours) only when the spec names them.

## stress
Beyond the limit (10,000 concurrent users, or ramp until failure).
- It fails in the way the spec allows (429, queueing, degraded mode), not by losing or corrupting
  data · it recovers once the load drops.

## regression
One per bug fixed: reproduces the bug through a public seam. It must be **run red before the fix**
(the gate checks) and green after. Kept forever. Re-running older cases after a change is not a
`regression` case; it is those cases' own re-run.

## smoke
The small fixed suite that says the build is alive: it starts, the health route answers, one read and
one write succeed. Lives under the `infra` plan; every other area's gate assumes it passes.

## mutation
Only where the plan names it: a critical task the user agreed is beyond critical (§ Choosing).
Runs a mutation tester
over the task's `Touches` classes that hold logic (not DTOs, records or config); the
command exits non-zero below the threshold (default 80 %, or the spec's / an ADR's). Surviving
mutants listed in the output are missing cases — add them, don't lower the threshold. The case's
command runs a full analysis: incremental history (PIT `withHistory`) is for iterating by hand,
never for evidence — it is experimental and ignores changes in a class's dependencies.
