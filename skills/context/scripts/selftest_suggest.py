#!/usr/bin/env python3
"""selftest_suggest.py — the `suggest:` lines of `clio q summary`: what to do next, from the state alone."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from cliolib import store  # noqa: E402
from cliolib.testkit import clio, done, git, ok, out, scratch, write  # noqa: E402

scratch()
git("init", "-q")
os.makedirs(".claude/clio/database/plan")
os.makedirs(".claude/clio/database/test")
for f in ("index", "debt", "runs"):
    write(".claude/clio/database/%s.jsonl" % f, "")
write("app.txt", "x\n")
git("add", "app.txt")
git("commit", "-qm", "init")
IDX, DEBT = ".claude/clio/database/index.jsonl", ".claude/clio/database/debt.jsonl"


def suggest():
    return [l for l in out("q", "summary").split("\n") if l.startswith("suggest:")]


def task(tid, area="a", status="open", needs=(), delta=None):
    write(".claude/clio/database/plan/%s.jsonl" % area, json.dumps({
        "type": "task", "id": tid, "date": "2026-10-08", "task": "t " + tid, "req": [], "levels": ["unit"], "critical": False,
        "tier": "full", "needs": list(needs), "touches": [], "na": {}, "status": status, "by": None, "commit": None,
        "delta": delta}) + "\n", "a")


def case(cid, tid, area="a"):
    write(".claude/clio/database/test/%s.jsonl" % area, json.dumps({
        "type": "case", "id": cid, "date": "2026-10-08", "task": tid, "level": "unit", "covers": ["unit.1"], "behaviour": "b",
        "expected": "e", "source": "s", "command": "true", "repeat": 1, "status": "active"}) + "\n", "a")


def debt(i, kind, blocked_by=None, status="pending", domain="a"):
    write(DEBT, json.dumps({"date": "2026-10-08", "id": i, "kind": kind, "status": status, "domain": domain, "what": ["w"], "req": [],
                            "specs": [], "docs": [], "code": [], "action": "a", "source": None, "blocked_by": blocked_by,
                            "issue": None}) + "\n", "a")


# nothing waiting: the line says where a new requirement or task goes
s = suggest()
ok(len(s) == 1 and "/clio:ingest" in s[0] and "/clio:plan" in s[0], "empty project: %s" % s)

# a ready task without cases → /clio:test, naming the task and how many lack cases
task("1.1")
task("1.2", needs=["1.1"])
s = suggest()
ok(s == ["suggest: /clio:test 1.1 — 1 task(s) ready, 1 without cases"], "ready task, no cases: %s" % s)
case("1.1-u1", "1.1")
s = suggest()
ok(s and s[0] == "suggest: /clio:test 1.1 — 1 task(s) ready, 0 without cases", "ready task with cases: %s" % s)
task("1.1", status="done")
s = suggest()
ok(s and s[0].startswith("suggest: /clio:test 1.2"), "a done need makes the next task ready: %s" % s)

# an unblocked spec-delta no task carries → /clio:plan <domain>; once a task carries it, not any more
debt("d1", "spec-delta", domain="a")
s = suggest()
ok(any(l.startswith("suggest: /clio:plan a — spec-delta d1") for l in s), "unabsorbed delta: %s" % s)
task("1.3", delta="d1")
ok(not any("spec-delta d1" in l for l in suggest()), "a delta carried by a task is still suggested")

# a delta blocked on someone → the question to answer, not a plan
debt("d2", "spec-delta", blocked_by="user: which width?", domain="a")
debt("d3", "spec-blocked", blocked_by="user: which key?", domain="a")
s = suggest()
ok(not any("spec-delta d2" in l for l in s), "a blocked delta was sent to plan: %s" % s)
ok(any("answer first — user: which width? (debt d2) and 1 more, then /clio:ingest" in l for l in s), "the open question: %s" % s)
debt("d3", "spec-blocked", blocked_by="user: which key?", status="done", domain="a")
debt("d2", "spec-delta", blocked_by="user: which width?", status="done", domain="a")
ok(not any("answer first" in l for l in suggest()), "a closed question is still asked")

# before the first memo nothing is "owed": files and commits stay quiet, like the drift hook
write("new.txt", "n\n")
ok(not any("/clio:memo" in l for l in suggest()), "memo suggested before any memo: %s" % suggest())
write(IDX, json.dumps({"date": "2026-10-07", "id": "0", "type": "task", "doc": "d0.md", "domain": "a", "plan_tasks": [], "files": [],
                       "commits": [git("rev-parse", "--short", "HEAD")], "keywords": ["k"], "req": [], "specs": []}) + "\n")

# work in the tree → /clio:memo, until a memo records this very code
s = suggest()
ok(any(l == "suggest: /clio:memo — 1 file(s) changed since the last memo" for l in s), "uncommitted file: %s" % s)
fp = out("test", "fp")
write(IDX, json.dumps({"date": "2026-10-08", "id": "1", "type": "task", "doc": "d.md", "domain": "a", "plan_tasks": [], "files": ["new.txt"],
                       "commits": [], "keywords": ["k"], "req": [], "specs": [], "fp": fp}) + "\n", "a")
ok(not any("/clio:memo" in l for l in suggest()), "the code is the memoed one, memo still suggested: %s" % suggest())
write("new.txt", "changed\n")
ok(any("/clio:memo" in l for l in suggest()), "edited after the memo, memo not suggested")
os.remove("new.txt")

# a commit no record names → memo (the user can say it is a chore)
write("c.txt", "c\n")
git("add", "c.txt")
git("commit", "-qm", "c")
ok(any(re.match(r"suggest: /clio:memo — commit [0-9a-f]{7} is in no record", l) for l in suggest()), "unrecorded commit: %s" % suggest())

# a 4.x Markdown plan comes first, whatever else waits
write(".claude/clio/docs/plans/old.md", "| # | Task |\n")
s = suggest()
ok(s and s[0].startswith("suggest: /clio:plan — 4.x Markdown plans"), "migration is not first: %s" % s)

# never more than four lines
ok(len(suggest()) <= 4, "more than four suggestions")
done()
