"""`clio test coverage <task-id>` — per case of a task: level and last recorded result, what
/clio:plan reads to decide whether a ticked task's tests fall short."""
import testcore as tc
from cliolib import common as c


def cmd_coverage(task):
    """Per case of a task: level and last result on this code (pass/fail/never) — what /clio:plan reads
    to decide whether a ticked task's tests fall short."""
    mine = tc.runnable(tc.cases(), task)
    if not mine:
        tc.say("no cases")
        return 0
    recs = tc.records()
    for r in mine:
        last = next((x.get("result") for x in reversed(recs)
                     if x.get("case") == r[0] and not c.truthy(x.get("red_base"))), None)
        tc.say("%s\t%s\t%s" % (r[0], r[2], c.tostring(last) if last is not None else "never"))
    return 0
