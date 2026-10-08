"""`clio test migrate [--write]` — move a 4.x project's Markdown plans and case tables
(.claude/clio/docs/plans/*.md, docs/tests/*.md) into the stores (database/plan|test/<area>.jsonl).

Without --write it only reports what it would do. With --write it writes every area, carries each
approval that still matched its table over to the new format (so nothing approved is asked again),
and moves the Markdown files to docs/archive/v4/ for comparison. Evidence in runs.jsonl stays valid:
it is keyed by case id and command, and both move over unchanged. It lives under `clio test` because
carrying an approval writes runs.jsonl, which only `clio test` may do.

Refused, with the reason, when an id lives in two plan files (one must be renamed first — the gate
would mix their cases), when an unticked task has no levels (a pre-4.0 row nobody re-planned), or
when the stores already hold records."""
import os
import re
import shutil

import testcore as tc
from cliolib import common as c
from cliolib import store
from cliolib import tables

OLD_PLANS = ".claude/clio/docs/plans"
OLD_TESTS = ".claude/clio/docs/tests"
ARCHIVE = ".claude/clio/docs/archive/v4"
BULLET = re.compile(r"-[ \t]*(\S+)[ \t]*·[ \t]*(\S+)[ \t]*—[ \t]*(.*)")
WAIVER = re.compile(r"-[ \t]*(\S+)[ \t]*—[ \t]*(.*)")


def md(d):
    return sorted(p for p in (os.path.join(d, f) for f in os.listdir(d)) if p.endswith(".md")) if os.path.isdir(d) else []


def area(path):
    return os.path.basename(path)[:-3].lower().replace(" ", "-")


def split(cell):
    return [x.strip() for x in re.split(r"[,\s]+", cell) if x.strip() and x.strip() not in ("–", "-")]


def touches_of(path):
    """(id → Touches cell) of one plan file — the column plan_rows does not return."""
    out, col = {}, 0
    for line in tables.live(tables.read_lines(path)):
        if not re.match(r"[ \t]*\|", line):
            continue
        cells = tables._cells(line)
        if tables._f(cells, 2) == "#":
            col = next((i for i in range(3, len(cells)) if tables._f(cells, i) == "Touches"), 0)
            continue
        if col and tables._ID.fullmatch(tables._f(cells, 2)):
            out[tables._f(cells, 2)] = [x.strip(" `") for x in tables._f(cells, col).split(",") if x.strip(" `–-")]
    return out


def done_state(cell):
    """The Done cell as (status, by, commit, date), or None for a row that is no task (a ⚠️ placeholder)."""
    if cell.startswith("[x]"):
        m = re.match(r"\[x\][ \t]*([0-9]{4}-[0-9]{2}-[0-9]{2})?[ \t]*([0-9a-fA-F]{6,40})?", cell)
        return "done", None, m.group(2), m.group(1)
    if cell.startswith("[ ]"):
        return "open", None, None, None
    if cell.startswith("superseded"):
        m = re.search(r"→[ \t]*([0-9]+(\.[0-9]+)*)", cell)
        d = re.search(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", cell)
        return ("superseded" if m else "void"), (m.group(1) if m else None), None, (d.group(0) if d else None)
    return None


def plan_records(path, problems, skipped):
    touches = touches_of(path)
    nas = {}
    for raw in tables.list_bullets("Not applicable", [path]):
        m = BULLET.fullmatch(raw.strip())
        if m:
            nas.setdefault(m.group(1), {})[m.group(2)] = m.group(3).strip() or "—"
    recs = []
    for _, tid, task, req, levels, needs, done, kind in tables.plan_rows([path]):
        st = done_state(done)
        if st is None:
            skipped.append("%s %s — not a task (Done is %r): a ⚠️ row waits in the report, not the plan" % (path, tid, done))
            continue
        status, by, commit, date = st
        crit = levels.startswith("critical")
        lv = split(levels.replace("critical", "").replace("·", " ")) if kind == "row" else []
        if status == "open" and not lv:
            problems.append("%s %s — open, but has no levels (a pre-4.0 row): re-plan or drop it with clio 4.2 first" % (path, tid))
            continue
        rec = {"type": "task", "id": tid, "task": task, "req": split(req), "levels": lv, "critical": crit,
               "needs": split(needs), "touches": touches.get(tid, []), "na": nas.get(tid, {}),
               "status": status, "by": by, "commit": commit}
        if date:
            rec["date"] = date
        recs.append(rec)
    return recs


def mutation_record(path):
    line = next((l for l in tables.read_lines(path) if re.match(r"Mutation:", l, re.I)), "")
    if not line:
        return None
    tool = re.match(r"Mutation:[ \t]*([^ (,]+)", line, re.I)
    th = re.search(r"([0-9]{1,3})%", line)
    adr = re.search(r"ADR[ \t]+([^,)]+)", line)
    return {"type": "mutation", "tool": tool.group(1) if tool else "none", "threshold": int(th.group(1)) if th else None,
            "adr": adr.group(1).strip() if adr else None}


def case_records(path, problems):
    src = "migrated from " + path
    recs = []
    for line in tables.live(tables.read_lines(path)):
        if not re.match(r"[ \t]*\|", line):
            continue
        f = tables._cells(line)
        cid = tables._f(f, 2)
        if cid == "Case" or re.fullmatch(r"[-: ]*", cid):
            continue
        if len(f) == 10:
            cov, beh, exp, cmd, rep = tables._f(f, 5), tables._f(f, 6), tables._f(f, 7), tables._f(f, 8), tables._f(f, 9)
        elif len(f) == 9:
            cov, beh, exp, cmd, rep = "", tables._f(f, 5), tables._f(f, 6), tables._f(f, 7), tables._f(f, 8)
        else:
            problems.append("%s %s — the row splits into %d cells (a `|` in its command?): fix it in the Markdown first" % (path, cid, len(f) - 2))
            continue
        cmd = cmd[1:] if cmd.startswith("`") else cmd
        cmd = cmd[:-1] if cmd.endswith("`") else cmd
        if cmd in ("", "–", "-"):
            continue          # an N/A row: nothing to run, its excuse lives in Not applicable
        recs.append({"type": "case", "id": cid, "task": tables._f(f, 3), "level": tables._f(f, 4),
                     "covers": split(cov.replace("·", ",")), "behaviour": beh or "—", "expected": exp or "—",
                     "source": src, "command": cmd, "repeat": int(rep) if rep.isdigit() else rep})
    metas = {}
    for raw in tables.list_bullets("Not applicable", [path]):
        m = BULLET.fullmatch(raw.strip())
        if m:
            metas.setdefault(m.group(1), {"na": {}, "waived": {}})["na"][m.group(2)] = m.group(3).strip() or "—"
    task_of = {r["id"]: r["task"] for r in recs}
    for raw in tables.list_bullets("Red waived", [path]):
        m = WAIVER.fullmatch(raw.strip())
        if m and m.group(1) in task_of:
            metas.setdefault(task_of[m.group(1)], {"na": {}, "waived": {}})["waived"][m.group(1)] = m.group(2).strip() or "—"
    seams = ""
    for line in tables.read_lines(path):
        m = re.search(r"Seams:[ \t]*(.*)$", line)
        if m:
            seams = m.group(1).strip()
    for tid, m in sorted(metas.items()):
        recs.append({"type": "meta", "id": tid, "seams": [seams] if seams else [], "na": m["na"], "waived": m["waived"]})
    return recs


def old_hash(task, files):
    """The approval hash 4.2 computed for a task from its Markdown tables, exactly."""
    if not files:
        return "none"
    mine = {r[0] for r in tables.case_rows(tc.LEVELS, files) if r[1] == task}
    lists = ([line for t, _, line in tables.na_rows(files) if t == task]
             + [line for cid, line in tables.waiver_rows(files) if cid in mine])
    return tc.hash_of(tables.case_lines(task, files) + lists)


def cmd_migrate(args):
    write = "--write" in args
    plans, tests = md(OLD_PLANS), md(OLD_TESTS)
    if not plans and not tests:
        tc.say("nothing to migrate: no %s/*.md or %s/*.md" % (OLD_PLANS, OLD_TESTS))
        return 0
    if store.files("plan") or store.files("test"):
        tc.say("FAIL: the stores already hold records (%s) — migrate runs once, into empty stores"
               % ", ".join(store.files("plan") + store.files("test")))
        return 1
    problems, skipped, plan_out, test_out, mut = [], [], {}, {}, None
    home = {}
    for p in plans:
        recs = plan_records(p, problems, skipped)
        plan_out[area(p)] = recs
        for r in recs:
            home.setdefault(r["id"], set()).add(p)
        mut = mutation_record(p) or mut
    dangling = sorted((r["id"], n) for rs in plan_out.values() for r in rs for n in r["needs"] if n not in home)
    for tid, n in dangling[:10]:
        tc.say("note: task %s needs %s, which no plan holds — kept as history (a finished task cannot be edited)" % (tid, n))
    if len(dangling) > 10:
        tc.say("note: … and %d more tasks that need an id no plan holds" % (len(dangling) - 10))
    for tid, ps in sorted(home.items()):
        if len(ps) > 1:
            problems.append("task %s is in %s — one id, one area: rename one (and its cases) before migrating" % (tid, " and ".join(sorted(ps))))
    for p in tests:
        test_out[area(p)] = case_records(p, problems)

    # 4.x let a `Not applicable` line excuse a whole level (`3.3 · unit — …`); the store keeps that on
    # the plan task's own `na`, and only `level.n` ids in the test meta, which is what the gate reads.
    by_id = {r["id"]: r for rs in plan_out.values() for r in rs}
    for rs in test_out.values():
        for m in rs:
            if m["type"] == "meta":
                for k in [k for k in m["na"] if k in store.LEVELS]:
                    if m["id"] in by_id:
                        by_id[m["id"]]["na"].setdefault(k, m["na"][k])
                        del m["na"][k]

    # approvals: kept only where the Markdown still matched what was approved
    recs = tc.records()
    approved = {}
    for r in recs:
        if c.truthy(r.get("approve")):
            approved[c.tostring(r["approve"])] = r.get("hash")
    keep, drop = [], []
    has_cases = {r["task"] for rs in test_out.values() for r in rs if r["type"] == "case"}
    for task, h in sorted(approved.items()):
        (keep if h == old_hash(task, tests) else drop).append(task)
    gone = [t_ for t_ in drop if t_ not in has_cases]
    drop = [t_ for t_ in drop if t_ in has_cases]

    for a, rs in sorted(plan_out.items()):
        n = {s: sum(1 for r in rs if r["status"] == s) for s in store.STATUSES}
        tc.say("plan %-12s %3d tasks — done %d, open %d, superseded %d, void %d → %s"
               % (a, len(rs), n["done"], n["open"], n["superseded"], n["void"], store.path_of("plan", a)))
    if mut:
        tc.say("plan infra       mutation: %s%s" % (mut["tool"], ", %d%%" % mut["threshold"] if mut["threshold"] else ""))
    for a, rs in sorted(test_out.items()):
        tc.say("test %-12s %3d cases, %d task metas → %s" % (a, sum(r["type"] == "case" for r in rs),
                                                          sum(r["type"] == "meta" for r in rs), store.path_of("test", a)))
    tc.say("approvals carried over: %d task(s)" % len(keep))
    if drop:
        tc.say("  not carried, their table changed after approve: " + ", ".join(drop))
    if gone:
        tc.say("  not carried, no cases left to approve: %d task(s)" % len(gone))
    for s in skipped:
        tc.say("skipped: " + s)
    # Everything the writer would refuse is found now, in the dry run too — never half way through a write.
    for a, rs in sorted(plan_out.items()):
        problems += store.write("plan", a, rs, may_tick=True, legacy=True, check_refs=False, dry=True)[0]
    if mut:
        problems += store.write("plan", "infra", [mut], legacy=True, check_refs=False, dry=True)[0]
    for a, rs in sorted(test_out.items()):
        problems += store.write("test", a, rs, legacy=True, check_refs=False, dry=True)[0]
    for p in problems:
        tc.say("FAIL: " + p)
    if problems:
        tc.say("nothing written — fix the lines above in the Markdown, then migrate again")
        return 1
    if not write:
        tc.say("dry run — nothing written. `clio test migrate --write` does it.")
        return 0

    errs = []
    for a, rs in sorted(plan_out.items()):
        errs += store.write("plan", a, rs, may_tick=True, legacy=True, check_refs=False)[0]
    if mut:
        errs += store.write("plan", "infra", [mut], legacy=True, check_refs=False)[0]
    for a, rs in sorted(test_out.items()):
        errs += store.write("test", a, rs, legacy=True, check_refs=False)[0]
    if errs:
        for e in errs:
            tc.say("FAIL: " + e)
        tc.say("partly written — remove %s and %s, fix the Markdown, migrate again" % (store.PLAN_DIR, store.TEST_DIR))
        return 1
    for task in keep:
        tc.append({"date": tc.today(), "approve": task, "hash": tc.table_hash(task),
                   "cases": tc.hash_of(tc.case_part(task)), "lists": tc.hash_of(tc.list_part(task)),
                   "lines": tc.case_part(task) + tc.list_part(task), "migrated_from": approved[task]})
    for d, files in (("plans", plans), ("tests", tests)):
        if files:
            os.makedirs(os.path.join(ARCHIVE, d), exist_ok=True)
        for p in files:
            shutil.move(p, os.path.join(ARCHIVE, d, os.path.basename(p)))
    tc.say("written. The Markdown is in %s for comparison; delete it once `clio q plan --all` reads right." % ARCHIVE)
    tc.say("next: `clio validate all` — it names any task whose needs point at nothing.")
    return 0

