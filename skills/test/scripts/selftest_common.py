"""selftest_common.py — imported by selftest_*.py: a throwaway repo with Clio's layout and one commit, and
the check helpers for `clio test`. Each selftest file gets its own repo, so no file depends on what
another left behind. Case commands are shell, as a user's are: `clio test` runs them with bash -c."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from cliolib import testkit  # noqa: E402
from cliolib.testkit import clio, git, lines, read, write  # noqa: E402,F401

d = testkit.scratch()
git("init", "-q")
git("config", "user.email", "t@t")   # the scratch repo only — its commits need an author
git("config", "user.name", "t")
for p in (".claude/clio/database", ".claude/clio/docs/tests", ".claude/clio/docs/plans"):
    os.makedirs(p)
write("app.txt", "x\n")
git("add", "app.txt")
git("commit", "-qm", "init")
RUNS = ".claude/clio/database/runs.jsonl"
PLAN_HEAD = "| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n"
CASE_HEAD = "| Case | Task | Level | Covers | Behaviour | Expected | Command | Repeat |\n|---|---|---|---|---|---|---|---|\n"


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


def add(path, *rows):
    """Append rows to a table file, one per line."""
    write(path, "".join(r + "\n" for r in rows), "a")


def sub(path, old, new):
    """sed -i s/old/new/ on a fixed string: every occurrence."""
    write(path, read(path).replace(old, new))


def done():
    testkit.done()
