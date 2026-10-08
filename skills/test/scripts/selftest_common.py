"""selftest_common.py — imported by selftest_*.py: a throwaway repo with Clio's layout and one commit, and
the check helpers for `clio test`. Each selftest file gets its own repo, so no file depends on what
another left behind. Case commands are shell, as a user's are: `clio test` runs them with bash -c."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from cliolib import common as c  # noqa: E402
from cliolib import store  # noqa: E402
from cliolib import testkit  # noqa: E402
from cliolib.testkit import clio, git, lines, read, write  # noqa: E402,F401

d = testkit.scratch()
git("init", "-q")
git("config", "user.email", "t@t")   # the scratch repo only — its commits need an author
git("config", "user.name", "t")
for p in (".claude/clio/database", store.PLAN_DIR, store.TEST_DIR):
    os.makedirs(p)
write("app.txt", "x\n")
git("add", "app.txt")
git("commit", "-qm", "init")
RUNS = ".claude/clio/database/runs.jsonl"


def t(*args, env=None):
    """`clio test <args>` → (exit code, stdout)."""
    rc, out, _ = clio("test", *args, env=env)
    return rc, out


def out(*args, **k):
    return t(*args, **k)[1]


def miss(msg):
    print(msg)
    testkit.bad = 1


def ok(*args):
    if t(*args)[0] != 0:
        miss("expected pass: clio test " + " ".join(args))


def ko(*args):
    if t(*args)[0] == 0:
        miss("expected fail: clio test " + " ".join(args))


def okg(task):
    """The user said yes to the table, then gate."""
    t("approve", task)
    ok("gate", task)


def grep(pat, text):
    """grep -q: a line of text matches the regex."""
    return re.search(pat, text, re.M) is not None


def has(task, pat):
    o = out("gate", task)
    if not grep(pat, o):
        miss("gate %s lacks '%s': %s" % (task, pat, o))


def raw(kind, area, rec):
    """Append one record straight to a store file — no merge, no checks — so the readers and the gate
    are tested against whatever a file may hold, not only what `clio add` lets in."""
    write(store.path_of(kind, area), c.dumps(rec) + "\n", "a")


def task(tid, levels, area="p", critical=False, needs=(), status="open", by=None, **kw):
    rec = {"type": "task", "id": tid, "date": "2026-01-01", "task": "t " + tid, "req": ["1"],
           "levels": list(levels), "critical": critical, "tier": "full", "needs": list(needs), "touches": [], "na": {},
           "status": status, "by": by, "commit": None, "delta": None}
    rec.update(kw)
    raw("plan", area, rec)


def case(cid, tid, level, cmd, repeat=1, area="p", covers=(), status="active", **kw):
    rec = {"type": "case", "id": cid, "date": "2026-01-01", "task": tid, "level": level,
           "covers": list(covers), "behaviour": "b", "expected": "e", "source": "s", "command": cmd,
           "repeat": repeat, "status": status}
    rec.update(kw)
    raw("test", area, rec)


def meta(tid, area="p", na=None, waived=None):
    raw("test", area, {"type": "meta", "id": tid, "date": "2026-01-01", "seams": [], "na": na or {},
                       "waived": waived or {}})


def mutation(tool, threshold=None, area="infra"):
    raw("plan", area, {"type": "mutation", "date": "2026-01-01", "tool": tool, "threshold": threshold, "adr": None})


def add_records(kind, area, *recs):
    """`clio add <kind> <area>` with these records on stdin → (exit code, stdout)."""
    rc, o, _ = clio("add", kind, area, input="".join(c.dumps(r) + "\n" for r in recs))
    return rc, o


def done():
    testkit.done()
