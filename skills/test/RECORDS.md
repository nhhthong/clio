# Test records

One JSON object per line on stdin of `clio add test <area>`. A record names only the fields it sets; the store carries the rest over.

| `type` | Fields |
|---|---|
| `case` | `id` (for example `3.3-u1`), `task`, `level`, `covers` (`level.n` ids), `behaviour`, `expected`, `source`, `command`, `repeat` (default 1), `status` (`active`, `removed`) |
| `meta` | `id` (the task), `seams`, `na` (`level.n` to reason), `waived` (case id to reason, see [RED.md](RED.md)) |

Example:

```json
{"type":"case","id":"3.3-u1","task":"3.3","level":"unit","covers":["unit.1"],"behaviour":"page 2 of 120 has 50","expected":"50 items","source":"spec: \"50 per page\"","command":"go test ./orders -run 'TestPage2$'","repeat":1}
{"type":"meta","id":"3.3","seams":["GET /orders"],"na":{"security.2":"public route"}}
```
