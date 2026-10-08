#!/usr/bin/env python3
"""selftest_migrate.py — a 4.2 project's Markdown plans and case tables move into the stores: dry run
first, refused on an id in two plans, and once written the gate passes on the evidence and the
approval recorded before — nothing re-run, nothing re-approved."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from selftest_common import RUNS, clio, done, grep, miss, out, read, t, write  # noqa: E402
import testcore as tc  # noqa: E402
from cliolib import store  # noqa: E402
from cliolib import tables  # noqa: E402

P = ".claude/clio/docs/plans/"
T = ".claude/clio/docs/tests/"
os.makedirs(P)
os.makedirs(T)
write(P + "infra.md", "# Plan — infra\nMutation: stryker (ADR 1790000000_stryker, 90%)\n\n"
      "| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n"
      "| 0.1 | Toolchain | 0 | smoke | – | – | [x] 2026-09-01 abc1234 |\n")
write(P + "orders.md", "# Plan — orders\n\n"
      "| # | Task | req | Test that proves it | Needs | Done |\n|---|---|---|---|---|---|\n"
      "| 3.0 | legacy list | 3 | `go test ./x` | 9.9 | [x] 2026-01-01 |\n\n## Re-planned 2026-09-02\n\n"
      "| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n"
      "| 3.1 | list returns 200 | 3 | unit, api | 0.1 | `orders/handler.go` | [ ] |\n"
      "| 3.2 | 401 without session | 3 | critical · api | 3.1 | `orders/handler.go` | superseded 2026-09-03 → 3.2.1 |\n"
      "| 3.2.1 | 401, again | 3 | critical · api | 3.1 | `orders/handler.go`, `auth/` | [ ] |\n"
      "| 3.3 | dropped idea | 3 | unit | – | – | superseded 2026-09-04 |\n"
      "| 7.1 | — waits on `ocr-dpi-open` (⚠️ row) | 7.1 | – | – | – | – |\n\n"
      "Not applicable:\n- 3.1 · contract — public route\n")
write(T + "orders.md", "# Tests — orders\nPlan: plans/orders.md · Seams: GET /orders\n\n"
      "| Case | Task | Level | Covers | Behaviour | Expected (source) | Command | Repeat |\n|---|---|---|---|---|---|---|---|\n"
      "| 3.1-u1 | 3.1 | unit | unit.1 | list | 200 (spec) | `true u1` | 1 |\n"
      "| 3.1-a1 | 3.1 | api | – | shape | fields (spec) | `true a1` | 1 |\n\n"
      "Not applicable:\n- 3.1 · api.1 — covered by a1's shape check\n\n"
      "| Case | Task | Level | Behaviour | Expected (source) | Command | Repeat |\n|---|---|---|---|---|---|---|\n"
      "| 3.2.1-a1 | 3.2.1 | api | no session | 401 | `true b1` | 1 |\n\n"
      "Red waived:\n- 3.2.1-a1 — correct since before abc1234\n")

# what 4.2 left in runs.jsonl: 3.1 approved and passing on today's code
tc.LEVELS = " ".join(store.LEVELS)
old = tc.hash_of(tables.case_lines("3.1", [T + "orders.md"])
                 + [l for t_, _, l in tables.na_rows([T + "orders.md"]) if t_ == "3.1"])
fp = out("fp").strip()
recs = [{"date": "2026-09-05", "approve": "3.1", "hash": old},
        {"date": "2026-09-05", "approve": "3.2.1", "hash": "stale"}]
for cid, cmd in (("3.1-u1", "true u1"), ("3.1-a1", "true a1")):
    recs.append({"date": "2026-09-05", "case": cid, "task": "3.1", "level": "unit", "cmd": cmd, "commit": None,
                 "fp": fp, "result": "pass", "runs": 1, "passed": 1, "exit": 0, "artifacts": []})
write(RUNS, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs))

# dry run: says what it would do, writes nothing
rc, o = t("migrate")
if rc != 0 or "dry run" not in o:
    miss("dry run: " + o)
if "note: task 3.1 needs 0.1" in o:
    miss("a need that exists was reported as dangling: " + o)
for want in ("plan orders", "5 tasks — done 1, open 2, superseded 1, void 1", "approvals carried over: 1 task(s)",
             "not carried, their table changed after approve: 3.2.1", "skipped: .claude/clio/docs/plans/orders.md 7.1",
             "mutation: stryker, 90%", "note: task 3.0 needs 9.9, which no plan holds"):
    if want not in o:
        miss("dry run lacks [%s]: %s" % (want, o))
if store.files("plan") or not os.path.isfile(P + "orders.md"):
    miss("the dry run wrote something")

# an id in two plans is refused: the gate would mix their cases
write(P + "other.md", "| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n"
      "| 3.1 | twin | 3 | unit | – | – | [ ] |\n")
rc, o = t("migrate", "--write")
if rc == 0 or "task 3.1 is in" not in o or store.files("plan"):
    miss("an id in two plans was migrated: " + o)
os.remove(P + "other.md")

rc, o = t("migrate", "--write")
if rc != 0:
    miss("migrate --write: " + o)
if os.path.exists(P + "orders.md") or not os.path.isfile(".claude/clio/docs/archive/v4/plans/orders.md"):
    miss("the Markdown was not archived")
plan = {r["id"]: r for _, r in store.current("plan") if r.get("type") == "task"}
if (plan["0.1"]["status"], plan["0.1"]["date"], plan["0.1"]["commit"]) != ("done", "2026-09-01", "abc1234"):
    miss("a done task lost its tick: %s" % plan["0.1"])
if (plan["3.0"]["status"], plan["3.0"]["levels"]) != ("done", []):
    miss("a pre-4.0 done row: %s" % plan["3.0"])
if (plan["3.2"]["status"], plan["3.2"]["by"], plan["3.3"]["status"]) != ("superseded", "3.2.1", "void"):
    miss("superseded rows: %s %s" % (plan["3.2"], plan["3.3"]))
if plan["3.2.1"]["touches"] != ["orders/handler.go", "auth/"] or plan["3.1"]["na"] != {"contract": "public route"}:
    miss("touches or plan na lost: %s" % plan["3.1"])
if store.mutation()["threshold"] != 90:
    miss("the Mutation line was not carried")
if "7.1" in plan:
    miss("a ⚠️ placeholder became a task")
cases = {r[0]: r for r in store.case_rows()}
if cases["3.2.1-a1"][6] != 0 or cases["3.1-a1"][3] != "–":
    miss("covers: a pre-4.1 row must stay untracked: %s" % cases)
if not grep(r"^- red waived: 3\.2\.1-a1", clio("q", "cases", "3.2.1")[1]):
    miss("the waiver was not carried: " + clio("q", "cases", "3.2.1")[1])

# the point of it all: 3.1 passes on its old evidence and its old approval — nothing re-run or re-approved
g = out("gate", "3.1")
if "OK: task 3.1" not in g:
    miss("evidence or approval lost in migration: " + g)
if "never approved" not in out("gate", "3.2.1") and "changed since" not in out("gate", "3.2.1"):
    miss("a stale approval was carried")
if '"migrated_from"' not in read(RUNS):
    miss("the carried approval does not say where it came from")

rc, o = t("migrate", "--write")
if "nothing to migrate" not in o:
    miss("a second migrate: " + o)
rc, o, _ = clio("validate", "all")
if "lives in" in o or "is not a JSON record" in o:
    miss("validate after migrate: " + o)

done()
