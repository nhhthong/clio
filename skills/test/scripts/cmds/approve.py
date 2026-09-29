"""`clio test approve <task-id>...` — record the hash of each task's case rows once the user
approved them; the gate holds each table to its own hash from here on."""
import testcore as tc


def cmd_approve(tasks):
    """One yes can cover a batch: each task still gets its own record and hash, so editing one table
    later voids that task's approval only. All ids are checked first — a typo approves nothing."""
    rows = tc.cases()
    for task in tasks:
        if not any(r[1] == task for r in rows):
            tc.say("FAIL: task %s has no case rows to approve — nothing approved" % task)
            return 1
    for task in tasks:
        h = tc.table_hash(task)
        tc.append({"date": tc.today(), "approve": task, "hash": h,
                   "cases": tc.hash_of(tc.case_part(task)), "lists": tc.hash_of(tc.list_part(task))})
        tc.say("approved: task %s case table %s" % (task, h))
    return 0
