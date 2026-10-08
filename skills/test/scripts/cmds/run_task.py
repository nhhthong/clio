"""`clio test run-task <task-id>...` — every runnable case of each task, through testcore's
run_cases() in one call so a shared `Batch:` template starts its runner once for the lot."""
import time

import testcore as tc
from cliolib import common as c
from cliolib import store


NOTE_MAX = 10   # past this a shared file is a hub, and a longer list is noise


def _overlap(a, b):
    """Two `touches` entries name the same code: the same path, or one a directory holding the other."""
    a, b = a.rstrip("/"), b.rstrip("/")
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def shared(tasks, rows):
    """Other tasks — open or done — whose touches overlap these tasks' and that have cases: the code
    run-task just proved is code they were proved on too, so their passes may no longer hold."""
    plan = store.tasks()
    mine = [x for t in tasks for x in c.items((plan.get(t) or {}).get("touches"))]
    tested = {r[1] for r in rows}
    out = []
    for tid, r in plan.items():
        if tid in tasks or tid not in tested or r.get("status") not in ("open", "done"):
            continue
        hit = sorted({y for y in c.items(r.get("touches")) for x in mine if _overlap(c.tostring(x), c.tostring(y))})
        if hit:
            out.append((tid, hit))
    return out


def cmd_run_task(tasks):
    """Every runnable case of each task given — all tasks' cases in one run_cases, so a batch template
    starts its runner once for the lot. Every task id is checked before anything runs."""
    rows = tc.cases()
    ids = []
    for task in tasks:
        mine = tc.runnable(rows, task)
        if not mine:
            tc.say("FAIL: task %s has no runnable case in %s/*.jsonl — nothing run" % (task, tc.TESTS))
            return 1
        ids += [r[0] for r in mine]
    t0 = time.monotonic()
    n0 = len(tc.records())
    tc.run_cases(None, "", ids)
    res = dict(tc.last_results(ids, n0))
    total = totalbad = 0
    for task in tasks:
        mine = [r[0] for r in rows if r[1] == task and r[0] in res]
        n = len(mine)
        bad = sum(1 for cid in mine if res[cid] != "pass")
        tc.say("task %s: %d/%d cases passed" % (task, n - bad, n))
        total, totalbad = total + n, totalbad + bad
    if len(tasks) != 1:
        tc.say("all: %d/%d cases passed across %d tasks" % (total - totalbad, total, len(tasks)))
    tc.say("took %d s" % int(time.monotonic() - t0))
    others = shared(tasks, rows)
    if others:
        tc.say("note: %d other task(s) touch the same files — their last pass was on other code; run-task the ones this change can reach:" % len(others))
        for tid, hit in others[:NOTE_MAX]:
            tc.say("      %s (%s)" % (tid, ", ".join(hit)))
        if len(others) > NOTE_MAX:
            tc.say("      … and %d more — a file this many tasks share is a hub: pick by behaviour (`clio q plan --all`)" % (len(others) - NOTE_MAX))
    return 0 if totalbad == 0 else 1
