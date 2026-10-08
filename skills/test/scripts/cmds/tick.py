"""`clio test tick <task-id> [--commit <hash>]` — mark a plan task done, and only on a passing gate.
The one path to `status: done`: `clio add` refuses it, so a tick always stands on evidence. On a task
already done it records the commit only (the backfill /clio:memo does once the work is committed)."""
import testcore as tc
from cliolib import store

from cmds.gate import cmd_gate


def cmd_tick(args):
    task, commit = "", None
    i = 0
    while i < len(args):
        if args[i] == "--commit" and i + 1 < len(args):
            commit = args[i + 1]
            i += 2
            continue
        if task:
            tc.say("usage: clio test tick <task-id> [--commit <hash>]")
            return 1
        task = args[i]
        i += 1
    homes = [(p, r) for p, r in store.current("plan") if r.get("type") == "task" and r.get("id") == task]
    if len(homes) != 1:
        tc.say("FAIL: task %s is in %s plan file(s) — nothing ticked" % (task, len(homes)))
        return 1
    path, rec = homes[0]
    if rec.get("status") == "done":
        if commit is None or commit == rec.get("commit"):
            tc.say("task %s is already done%s" % (task, " at " + rec["commit"] if rec.get("commit") else ""))
            return 0
        if rec.get("commit"):
            tc.say("FAIL: task %s is done at %s — a recorded commit is not overwritten (to %s)" % (task, rec["commit"], commit))
            return 1
        part = {"type": "task", "id": task, "commit": commit}
    else:
        if cmd_gate(task) != 0:
            tc.say("not ticked: task %s — the gate did not pass" % task)
            return 1
        part = {"type": "task", "id": task, "status": "done", "commit": commit}
    errs, _ = store.write("plan", store.area_of(path), [part], may_tick=True)
    for e in errs:
        tc.say("FAIL: " + e)
    if errs:
        return 1
    tc.say("ticked: task %s done%s" % (task, " at " + commit if commit else ""))
    return 0
