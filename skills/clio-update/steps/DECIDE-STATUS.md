# Step 2 — Decide the status

The whole point of the file. `blocked_by` is decisive, not `status` — `status` says how far the
work got, `blocked_by` says whether anyone may start.

| `status` | `blocked_by` | meaning | may implement? |
|---|---|---|---|
| `pending` | `null` | Settled, code doesn't match yet, nothing external missing. | **Yes — the queue** |
| `pending` | *a string* | Still open, or depends on something outside (upstream field, sample, undecided rule). | **No** |
| `in-process` | either | Workaround/partial fix shipped, root cause open. | Only to continue, and only if `blocked_by` is `null` |
| `done` | `null` | Code already matches, or change needs no code. | **No — don't redo it** |

Write `blocked_by` as the concrete missing thing ("upstream system exposes no synced flag", "no
sample file received"), never "pending confirmation". `null` the moment nothing external is missing.

Two traps: a ✅ in `requirements.md` means a decision exists, not that it's built (✅ + mismatch =
`pending` + `blocked_by: null`). A decision confirmed only second-hand (internal relay, or carrying a
"re-verify" note in the live decision channel's open items) keeps a non-null `blocked_by` regardless
of how definite another spec file sounds.

Next: `APPEND-DEBT.md`.
