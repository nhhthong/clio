"""`clio test run-task <task-id>...` — every runnable case of each task, through testcore's
run_cases() in one call so a shared `Batch:` template starts its runner once for the lot."""
import time

import testcore as tc


def cmd_run_task(tasks):
    """Every runnable case of each task given — all tasks' cases in one run_cases, so a batch template
    starts its runner once for the lot. Every task id is checked before anything runs."""
    rows = tc.cases()
    ids = []
    for task in tasks:
        mine = tc.runnable(rows, task)
        if not mine:
            tc.say("FAIL: task %s has no runnable case in %s/*.md — nothing run" % (task, tc.TESTS))
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
    return 0 if totalbad == 0 else 1
