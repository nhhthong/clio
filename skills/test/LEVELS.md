# Levels — what each one must cover

Read only the sections the plan's `Levels` cell names. Each bullet is a case to write, or a line in
the report saying why it cannot apply to this task.

## unit
One class or function through its public signature (`UserService.createUser()`).
- The happy path with a value from the spec · each boundary the spec names (min, max, max+1, empty,
  zero) · each error the spec lists, asserting the error type or code, not just "throws".
- No DB, network, clock or randomness — inject them.

## integration
Several real components together: service + repository + a real database (container, not a mock).
- Write then read back through the public seam · the transaction rolls back on failure · a constraint
  the schema enforces (unique, FK, not null) surfaces as the domain error the spec expects.
- Each test owns its data: fresh schema or a transaction rolled back after it.

## api
The endpoint as a client sees it (`POST /users`).
- Status, body shape and every field the spec lists · each validation error with its status and
  message · pagination, filtering, sorting at the limits the spec states · idempotency when the spec
  requires it (same key twice → one effect).

## e2e
A whole flow from the spec's key flows (login → cart → pay), through the real UI or public API.
- The flow completes · the one failure in the middle the spec cares about most (payment declined)
  leaves the system in the state the spec says.
- Few and slow — only flows the spec names.

## contract
The API between two services (Order ↔ Payment).
- Consumer side: the requests it sends and the responses it relies on, as a contract file.
- Provider side: verifies that contract against the running provider. Both must run, or it is not a
  contract test.

## perf
Latency and throughput of one operation, **only with a number from the spec** (p95 < 200 ms, 1,000
req/s). The command exits non-zero when the threshold is missed.

## load
The system at the load the spec expects (500 concurrent users, N minutes).
- Error rate and latency percentiles stay inside the spec's numbers for the whole run.

## stress
Beyond the limit (10,000 concurrent users, or ramp until failure).
- It fails in the way the spec allows (429, queueing, degraded mode), not by losing or corrupting
  data · it recovers once the load drops.

## security
Everything that crosses a trust boundary.
- AuthN: no token, expired token, token signed with the wrong key, `alg: none` → rejected.
- AuthZ: user A reads/edits/deletes user B's resource → 403/404; each role the spec names against
  each action it must not do.
- Input: SQL/NoSQL injection, path traversal, oversized payload, script in a stored field rendered
  back — rejected or escaped, and no stack trace or query text in the response.
- Secrets and PII never appear in logs or error bodies.

## concurrency
Anything two actors can do to the same thing at once. `Repeat` ≥ 20, race detector on
(`go test -race`, TSan, `-Djdk…`), interleaving forced with a barrier or latch.
- **Lost update**: two writers, both changes survive or one gets a conflict error.
- **Double effect**: two identical requests (double submit, retry) → exactly one order, one charge.
- **Invariant**: a balance never negative, a stock count never below zero, under N parallel buyers.
- **Deadlock**: two resources locked in opposite order finish within a timeout.
- **Ordering**: events processed out of order end in the state the spec defines.
Every case asserts the invariant after all actors finish, never just "no error".

## regression
One per bug fixed: reproduces the bug through a public seam. It must be **run red before the fix**
(the gate checks) and green after. Kept forever.

## smoke
The small fixed suite that says the build is alive: it starts, the health route answers, one read and
one write succeed. Lives under the `infra` plan; every other area's gate assumes it passes.

## mutation
Required when the task is critical. Runs a mutation tester over the task's `Touches` files; the
command exits non-zero below the threshold (default 80 %, or the spec's / an ADR's). Surviving
mutants listed in the output are missing cases — add them, don't lower the threshold.
