# Plan records

One JSON object per line on stdin of `clio add plan <area>`. A record names only the fields it sets; the store carries the rest over.

| `type` | Fields |
|---|---|
| `task` | `id` (`<row>.<n>`), `task`, `req` (strings), `levels`, `tier` (`light` or full), `critical` (true), `needs` (task ids), `touches` (paths), `na` (level to reason), `delta` (a `spec-delta` id), `status` (`void`, `superseded`), `by` (the replacing id) |
| `mutation` | `tool` (`none` for no mutation testing), `threshold` (null means 80), `adr` (path) |

Example `task` records:

```json
{"type":"task","id":"3.1","task":"`GET /orders` returns 200 for an authenticated user","req":["3"],"levels":["unit","api"],"needs":["0.4"],"touches":["orders/handler.go"],"na":{"security":"3.2 proves the unauthenticated path"}}
{"type":"task","id":"3.2","task":"`GET /orders` returns 401 without a session","req":["3"],"levels":["api","security"],"critical":true,"needs":["3.1"],"touches":["orders/handler.go"]}
```
