"""`clio test diff <task-id>...` — what changed in each task's cases since its last approval, grouped
so one edit made to many cases reads as one line: `expected: "100" → "99" — 3.1-u1, 3.2-u1`. What
/clio:test shows the user before asking for the yes again. Read-only."""
import testcore as tc
from cliolib import common as c


def _parse(lines):
    """(cases by id, list lines) from what approve stored: a case line is JSON, a list line is not."""
    cases, rest = {}, []
    for line in lines:
        try:
            r = c.loads(line)
        except ValueError:
            rest.append(line)
            continue
        if isinstance(r, dict) and c.truthy(r.get("id")):
            cases[c.tostring(r["id"])] = r
        else:
            rest.append(line)
    return cases, rest


def cmd_diff(tasks):
    recs = tc.records()
    groups, added, removed, lists = {}, [], [], []
    for task in tasks:
        arec = next((r for r in reversed(recs) if r.get("approve") == task), None)
        now_c, now_l = _parse(tc.case_part(task) + tc.list_part(task))
        if arec is None:
            tc.say("%s: never approved — every case below is new" % task)
            added += sorted(now_c)
            lists += ["+ " + l for l in now_l]
            continue
        if not isinstance(arec.get("lines"), list):
            tc.say("%s: approved before `clio test diff` existed — no stored copy to compare; show the whole list" % task)
            continue
        was_c, was_l = _parse(arec["lines"])
        added += sorted(set(now_c) - set(was_c))
        removed += sorted(set(was_c) - set(now_c))
        for cid in sorted(set(now_c) & set(was_c)):
            for k in sorted(set(now_c[cid]) | set(was_c[cid])):
                a, b = was_c[cid].get(k), now_c[cid].get(k)
                if c.dumps(a) != c.dumps(b):
                    groups.setdefault((k, c.dumps(a), c.dumps(b)), []).append(cid)
        lists += ["- " + l for l in was_l if l not in now_l] + ["+ " + l for l in now_l if l not in was_l]
    if not (groups or added or removed or lists):
        tc.say("no change since the last approval of " + " ".join(tasks))
        return 0
    for (k, a, b), ids in sorted(groups.items()):
        tc.say("%s: %s → %s — %s" % (k, a, b, ", ".join(ids)))
    if added:
        tc.say("added: " + ", ".join(added))
    if removed:
        tc.say("removed: " + ", ".join(removed))
    for l in lists:
        tc.say(l)
    return 0
