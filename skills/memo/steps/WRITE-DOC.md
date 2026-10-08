# Step 2 — Write the doc

`.claude/clio/docs/tasks/<feature>/<id>_<name>.md`, one per sub-task, plus a `summary.md` per feature. The feature is kebab-case, the business area a task is scoped to (never a source directory). `<id>` is the creation timestamp, forever (filename prefix and the index's `id`); `<name>` is 1–4 lowercase words, from the plan task's wording; plan ids go in `plan_tasks`, never in the filename.

```bash
clio doc <<'EOF'
{"feature":"order-page","name":"loyalty-lookup","plan_tasks":["3.1"],"summary":"One sentence.",
 "files":["src/orders/loyalty.ts — why it changed"],"decisions":["Why X instead of Y"],
 "side_effects":["What could affect other features"],"testing":["OK: task 3.1 — every case passed at <fp>"],
 "related":["tasks/order-page/1789430400_order-fetch.md"],"follow_up":["An open question"],
 "commit":"3f2a1c","feature_what":"One or two sentences, for a new feature's summary.md","domain":"account"}
EOF
```
It prints `doc:` and `id:` for step 3. **CREATE** takes `feature` and `name`; **UPDATE**, the default, takes `"doc":"<path>"` instead. Every other key is optional. Do not read the doc first or edit it by hand: the command applies the rules.

| You give | It does |
|---|---|
| `summary` | CREATE writes it; an UPDATE keeps the Summary unless `"summary_replace":true` (the work's behaviour changed) |
| `files` | a new path is added; an old path with a new reason gets `; <reason> (date)` |
| `decisions` | appended. A reversed one: `"Superseded: now Y instead of X, because …"` |
| `side_effects`, `testing`, `related` | appended, dated (`testing` always) |
| `follow_up` | **replaces** the section, the only destructive one; `[]` writes `none` |
| `changelog` | one `- date — text (commit h)` line; a new doc gets `initial` |
| `commit`, `plan_tasks` | `Commit:` and `Plan tasks:` accumulate; `Updated:` is today |
| `relabel` | `["Summary","Decisions"]` → `## [SUPERSEDED date] Summary — REVERTED, DO NOT RE-IMPLEMENT`, body kept |
| `light: true` | a new doc is only the header, Summary and Change Log |
| `feature_what` | a feature with no `summary.md` gets one |

Yours to judge:
- **Same sub-task or new.** Continuing, fixing, extending or reverting what a doc describes → UPDATE (a sub-task `3.1.1` goes to its parent's doc); a different observable behaviour → a new doc beside it.
- **A section the code no longer matches** → `relabel` it; never delete a bullet.
- Never list the sub-tasks in `summary.md` (`ls` and `clio q plan <area>` say it; a hand-kept list drifts). A lesson for the whole feature goes to its `## General Memory` (`WRAP-UP.md`).
- **Split gate.** Over ~200 non-blank lines, or `req` now holds more than one row → ask once whether the next piece starts its own doc in the feature; split only on a yes, never move content out of an existing doc.
- Moving a doc keeps its filename and `id`; step 3 records the new `doc` under the same `id`.

Next: `INDEX-IT.md`.
