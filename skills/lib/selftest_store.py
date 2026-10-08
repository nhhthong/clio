#!/usr/bin/env python3
"""selftest_store.py — `clio add`, the one writer of the plan and test stores: merge, all or nothing,
done only through the gate, one id one area, covers and references checked before anything is written."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cliolib import store  # noqa: E402
from cliolib.testkit import clio, done, eq, ok, read, scratch  # noqa: E402

scratch()
os.makedirs(".claude/clio/database")


def add(kind, area, *recs, raw=None):
    rc, o, _ = clio("add", kind, area, input=raw if raw is not None else "".join(json.dumps(r) + "\n" for r in recs))
    return rc, o


def size(kind, area):
    p = store.path_of(kind, area)
    return len(read(p).splitlines()) if os.path.isfile(p) else 0


T31 = {"type": "task", "id": "3.1", "task": "list returns 200", "levels": ["unit", "api"]}
rc, o = add("plan", "orders", T31, {"type": "task", "id": "3.2", "task": "401 without a session",
                                     "levels": ["api", "security"], "critical": True, "needs": ["3.1"]})
eq(rc, 0, "a new task with defaults filled in: " + o)
r = json.loads(read(store.path_of("plan", "orders")).splitlines()[0])
eq((r["status"], r["needs"], r["by"], r["date"] == store.today()), ("open", [], None, True), "defaults and date")

# a partial record is a whole update: the rest comes from the current record
rc, o = add("plan", "orders", {"type": "task", "id": "3.1", "touches": ["orders/handler.go"]})
eq(rc, 0, "partial update: " + o)
last = {x["id"]: x for x in map(json.loads, read(store.path_of("plan", "orders")).splitlines())}
eq((last["3.1"]["task"], last["3.1"]["touches"]), ("list returns 200", ["orders/handler.go"]), "merge keeps the rest")

# all or nothing: one bad record and the good one beside it is not written either
n = size("plan", "orders")
rc, o = add("plan", "orders", {"type": "task", "id": "3.3", "task": "x", "levels": ["unit"]},
            {"type": "task", "id": "3.4", "task": "y", "levels": ["Unit"]})
ok(rc != 0 and "levels must be" in o and "nothing written" in o, "bad level not refused: " + o)
eq(size("plan", "orders"), n, "a refused batch wrote a line")
rc, o = add("plan", "orders", raw='{"type":"task","id":"3.3"\n')
ok(rc != 0 and "not valid JSON" in o, "broken JSON not refused: " + o)
rc, o = add("plan", "orders", {"type": "task", "id": "3.5", "task": "x", "levels": ["unit"], "colour": "red"})
ok(rc != 0 and "unknown field" in o, "an unknown field not refused: " + o)
rc, o = add("plan", "Orders", T31)
ok(rc != 0 and "area must be" in o, "a bad area name not refused: " + o)

# references: needs and by name tasks that exist in a plan, or in the same call
rc, o = add("plan", "orders", {"type": "task", "id": "3.6", "task": "x", "levels": ["unit"], "needs": ["9.9"]})
ok(rc != 0 and "names 9.9" in o, "a need naming nothing not refused: " + o)
rc, o = add("plan", "orders", {"type": "task", "id": "3.1", "status": "superseded"})
ok(rc != 0 and "names the task that replaced it" in o, "superseded without by not refused: " + o)

# one id, one area
rc, o = add("plan", "billing", {"type": "task", "id": "3.1", "task": "x", "levels": ["unit"]})
ok(rc != 0 and "already lives in" in o, "an id in a second area not refused: " + o)

# done is the gate's: add refuses it, and refuses touching a task that is done
rc, o = add("plan", "orders", {"type": "task", "id": "3.1", "status": "done"})
ok(rc != 0 and "clio test tick" in o, "done through add not refused: " + o)
store.write("plan", "orders", [{"type": "task", "id": "3.2", "status": "done"}], may_tick=True)
rc, o = add("plan", "orders", {"type": "task", "id": "3.2", "task": "reworded"})
ok(rc != 0 and "is done" in o, "a done task edited: " + o)

# a light task: one level, not critical, not regression or mutation — anything riskier is full
rc, o = add("plan", "orders", {"type": "task", "id": "3.7", "task": "mascot notes", "levels": ["smoke"], "tier": "light"})
eq(rc, 0, "a light task: " + o)
rc, o = add("plan", "orders", {"type": "task", "id": "3.8", "task": "x", "levels": ["unit", "api"], "tier": "light"})
ok(rc != 0 and "a light task is not critical" in o, "a two-level light task not refused: " + o)
rc, o = add("plan", "orders", {"type": "task", "id": "3.8", "task": "x", "levels": ["unit"], "tier": "light", "critical": True})
ok(rc != 0 and "a light task is not critical" in o, "a critical light task not refused: " + o)

# the project's mutation decision, last one wins
rc, o = add("plan", "infra", {"type": "mutation", "tool": "stryker", "threshold": 85})
eq(rc, 0, "mutation record: " + o)
eq(store.mutation()["threshold"], 85, "mutation read back")

# cases: a task that exists, covers from the level's own LEVELS.md ids, one line of command
C = {"type": "case", "id": "3.1-u1", "task": "3.1", "level": "unit", "covers": ["unit.1"], "behaviour": "b",
     "expected": "200", "source": "spec: 200", "command": "go test ./orders -run 'TestList$' | tee x"}
rc, o = add("test", "orders", C)
eq(rc, 0, "a case with a pipe and quotes in its command: " + o)
eq(store.case_rows()[0][4], C["command"], "the command reads back unchanged")
rc, o = add("test", "orders", dict(C, id="3.1-u2", covers=[]))
ok(rc != 0 and "covers must name" in o, "a case covering nothing not refused: " + o)
rc, o = add("test", "orders", dict(C, id="3.1-u3", covers=["api.1"]))
ok(rc != 0 and "does not list" in o, "a case covering another level's id not refused: " + o)
rc, o = add("test", "orders", dict(C, id="7.7-u1", task="7.7"))
ok(rc != 0 and "in no plan" in o, "a case for no task not refused: " + o)
rc, o = add("test", "orders", {"type": "meta", "id": "3.1", "na": {"unit.9": "x"}})
ok(rc != 0 and "does not list" in o, "an excuse for no LEVELS.md id not refused: " + o)
rc, o = add("test", "orders", {"type": "meta", "id": "3.1", "seams": ["GET /orders"], "na": {"api.1": "covered by 3.2"}})
eq(rc, 0, "meta: " + o)
eq([x[:2] for x in store.na_rows()], [("3.1", "api.1")], "meta na read back")

# a level with a digit in its name (e2e) is a level like any other
rc, o = add("test", "orders", {"type": "meta", "id": "3.1", "na": {"api.1": "covered by 3.2", "e2e.1": "no key flow"}})
eq(rc, 0, "an e2e id in na: " + o)

# what approve hashes moves with any edit of a case, but not with its date
h1 = store.case_lines("3.1")
store.write("test", "orders", [{"type": "case", "id": "3.1-u1"}])
eq(store.case_lines("3.1"), h1, "re-recording a case unchanged changed the hash")
store.write("test", "orders", [{"type": "case", "id": "3.1-u1", "expected": "201"}])
ok(store.case_lines("3.1") != h1, "an edited case kept the hash")
store.write("test", "orders", [{"type": "case", "id": "3.1-u1", "status": "removed"}])
eq(store.case_lines("3.1"), [], "a removed case still hashed")

done()
