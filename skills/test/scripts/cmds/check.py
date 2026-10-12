"""`clio test check <task-id>` — the evidence of a `none` task (no cases): run the task's `check`
command once (the repo's own build or compile line) and record it in runs.jsonl, bound to the
fingerprint like a case. A none task without a `check` command has nothing to run."""
import os
import tempfile

import testcore as tc
from cliolib import common as c
from cliolib import fingerprint as fpm
from cliolib import store


def cmd_check(task):
    rec = store.tasks().get(task)
    if rec is None or rec.get("tier") != "none":
        tc.say("FAIL: task %s is not a `none` task — use run-task" % task)
        return 1
    cmd = rec.get("check")
    if not cmd:
        tc.say("task %s has no check command — nothing to run; the gate will accept its skip reason" % task)
        return 0
    tree = fpm.fp_tree(tc.ROOT, tc.RUNS)
    fd, log = tempfile.mkstemp()
    os.close(fd)
    try:
        code, timed_out = tc.capped(cmd, tc.ROOT, log)
        result = "pass" if code == 0 else "fail"
        tc.append({"date": tc.today(), "check": task, "cmd": cmd, "commit": tc.short_head(tc.ROOT),
                   "fp": tree[:12], "result": result, "exit": code})
        tc.say("%s: check %s — exit %d" % (result, task, code))
        if result != "pass":
            tc.say("--- last output")
            tc.tail(log)
        return 0 if result == "pass" else 1
    finally:
        os.remove(log)
