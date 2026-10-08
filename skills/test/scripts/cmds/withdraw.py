"""`clio test withdraw <task-id>...` — take done tasks back when the work never left the working tree.

A done task is final, and for work that is committed that stays true: undo it with `git revert` and a
revert task. But a change tried and dropped before any commit has nothing to revert except the working
tree, and a revert task for it would prove a state git already holds. So this is the one way a done
task becomes void, and it refuses unless the work is really gone:
  - the task has no recorded commit (`tick --commit` never ran for it);
  - its `touches` are clean in git (restore them first: `git restore <paths>`; delete new files);
  - no other done task still needs it (withdraw those in the same call, or they would stand on nothing).
It voids the task, removes its cases from the store, and lists the docs to relabel. runs.jsonl is not
touched. It needs the user's yes like `approve`: it is left out of every skill's allowed-tools, so the
permission prompt is that yes."""
import testcore as tc
from cliolib import common as c
from cliolib import store

IDX = ".claude/clio/database/index.jsonl"


def cmd_withdraw(tasks):
    plan = {c.tostring(r.get("id")): (p, r) for p, r in store.current("plan") if r.get("type") == "task"}
    asked = set(tasks)
    problems = []
    for t in tasks:
        if t not in plan:
            problems.append("task %s is in no plan" % t)
            continue
        _, r = plan[t]
        if r.get("status") != "done":
            problems.append("task %s is %s, not done — an open task is edited in place or voided with `clio add`" % (t, r.get("status")))
            continue
        if c.truthy(r.get("commit")):
            problems.append("task %s is committed (%s) — undo it with `git revert` and plan a revert task" % (t, r["commit"]))
        paths = [x for x in c.items(r.get("touches")) if c.tostring(x) not in ("", "–", "-")]
        dirty = c.git_out(["status", "--porcelain", "--"] + paths) if paths else ""
        if dirty:
            problems.append("task %s: its touches still differ from git — restore them first (git restore / delete the new files):\n      %s"
                            % (t, dirty.replace("\n", "\n      ")))
    for t, (_, r) in plan.items():
        if t in asked or r.get("status") != "done":
            continue
        gone = [n for n in c.items(r.get("needs")) if c.tostring(n) in asked]
        if gone:
            problems.append("task %s is done and needs %s — withdraw it in the same call, or it stands on nothing" % (t, ", ".join(gone)))
    if problems:
        for p in problems:
            tc.say("FAIL: " + p)
        tc.say("nothing withdrawn")
        return 1
    by_area = {}
    for t in tasks:
        by_area.setdefault(store.area_of(plan[t][0]), []).append({"type": "task", "id": t, "status": "void"})
    for area, recs in sorted(by_area.items()):
        errs, _ = store.write("plan", area, recs, withdraw=True)
        if errs:
            for e in errs:
                tc.say("FAIL: " + e)
            return 1
    removed = {}
    for p, r in store.current("test"):
        if r.get("type") == "case" and c.tostring(r.get("task")) in asked and r.get("status") != "removed":
            removed.setdefault(store.area_of(p), []).append({"type": "case", "id": c.tostring(r["id"]), "status": "removed"})
    for area, recs in sorted(removed.items()):
        store.write("test", area, recs)
    open_deps = sorted(t for t, (_, r) in plan.items() if r.get("status") == "open"
                       and any(c.tostring(n) in asked for n in c.items(r.get("needs"))))
    tc.say("withdrawn: %s — %d case(s) removed from the store; runs.jsonl untouched" % (", ".join(tasks), sum(len(v) for v in removed.values())))
    if open_deps:
        tc.say("note: open task(s) still need them and will never be ready: %s — edit their needs or void them" % ", ".join(open_deps))
    # The docs that describe the withdrawn work: /clio:memo relabels them (DEBT-IT.md § 1).
    last = {}
    for r in c.read_valid(IDX):
        if isinstance(r, dict) and r.get("type") == "task" and c.truthy(r.get("id")):
            last[c.tostring(r["id"])] = r
    status = {t: (r.get("status") if r.get("status") != "done" else "done") for t, (_, r) in plan.items()}
    for t in asked:
        status[t] = "void"
    for did, r in sorted(last.items()):
        mine = [c.tostring(x) for x in c.items(r.get("plan_tasks")) if c.tostring(x) in asked]
        if not mine:
            continue
        rest = [c.tostring(x) for x in c.items(r.get("plan_tasks")) if status.get(c.tostring(x)) not in ("void", "superseded")]
        tc.say("doc: %s  [%s]  %s" % (c.tostring(r.get("doc")), ", ".join(mine),
                                       "relabel Summary and Decisions" if not rest else "also covers %s — relabel only what concerned %s" % (", ".join(rest), ", ".join(mine))))
    return 0
