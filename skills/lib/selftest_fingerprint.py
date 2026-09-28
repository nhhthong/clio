#!/usr/bin/env python3
"""selftest_fingerprint.py — cliolib.fingerprint on a throwaway repo: what moves the fp and what must
not, the test/code split, artifacts. Prints OK or each mismatch; exit 1 on any."""
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cliolib import fingerprint as fpm  # noqa: E402

bad = 0


def same(a, b, what):
    global bad
    if a != b:
        print("FAIL (should not move) %s: %s → %s" % (what, a, b))
        bad = 1


def moved(a, b, what):
    global bad
    if a == b:
        print("FAIL (should move) %s: stayed %s" % (what, a))
        bad = 1


def sh(*args):
    subprocess.run(list(args), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text + "\n")


with tempfile.TemporaryDirectory() as d:
    os.chdir(d)
    sh("git", "init", "-q")
    sh("git", "config", "user.email", "t@t")
    sh("git", "config", "user.name", "t")
    os.makedirs(".claude/clio/database")
    runs = os.path.join(d, ".claude/clio/database/runs.jsonl")
    open(runs, "w").close()

    def fp():
        return fpm.fp(d, runs)

    def halves():
        return fpm.split_fp(d, fpm.fp_tree(d, runs))

    write("src/app.txt", "code v1")
    write("tests/app_test.txt", "test v1")
    sh("git", "add", "-A")
    sh("git", "commit", "-qm", "init")

    # content, not history: committing the same bytes keeps the fp; any edit moves it
    f0 = fp()
    sh("git", "commit", "-qm", "empty", "--allow-empty")
    same(f0, fp(), "an empty commit")
    write("src/app.txt", "code v2")
    f1 = fp()
    moved(f0, f1, "an edit")
    sh("git", "add", "src/app.txt")
    sh("git", "commit", "-qm", "v2")
    same(f1, fp(), "committing the edited bytes")
    write("src/new.txt", "scratch")
    f2 = fp()
    moved(f1, f2, "an untracked, non-ignored file")
    write(".gitignore", "src/new.txt")
    sh("git", "add", ".gitignore")
    sh("git", "commit", "-qm", "ignore")
    f3 = fp()
    write("src/new.txt", "scratch 2")
    same(f3, fp(), "an ignored file")
    write(".claude/clio/docs/a.md", "x")
    same(f3, fp(), "anything under .claude/")

    # racy git: a same-size edit in the second of its `git add`, fingerprinted a second later
    write("src/racy.txt", "aaa")
    sh("git", "add", "src/racy.txt")
    write("src/racy.txt", "bbb")
    time.sleep(1)
    f4 = fp()
    sh("git", "add", "src/racy.txt")
    same(f4, fp(), "a same-size edit right after git add (racy git)")

    # the split: a test edit moves tfp only, a code edit cfp only
    t0, c0 = halves()
    write("tests/app_test.txt", "test v2")
    t1, c1 = halves()
    moved(t0, t1, "tfp on a test edit")
    same(c0, c1, "cfp on a test edit")
    write("src/app.txt", "code v3")
    t2, c2 = halves()
    same(t1, t2, "tfp on a code edit")
    moved(c1, c2, "cfp on a code edit")
    for p in ("foo_test.go", "a.test.ts", "b.spec.js", "tests/x.py", "test_y.py",
              "src/test/java/ATest.java", "spec/m_spec.rb", "__tests__/c.js"):
        write(p, "x")
        ta, ca = halves()
        write(p, "y")
        tb, cb = halves()
        moved(ta, tb, "tfp for " + p)
        same(ca, cb, "cfp for " + p)

    # artifacts: a file a run created is not code — until it is tracked; a non-ASCII path too
    write("coverage.out", "report v1")
    write("src/tệp.ts", "gen v1")
    with open(runs, "a", encoding="utf-8") as f:
        f.write('{"case":"x","artifacts":["coverage.out","src/tệp.ts"]}\n')
    f5 = fp()
    write("coverage.out", "report v2")
    same(f5, fp(), "an artifact edit")
    sh("git", "add", "src/tệp.ts")
    sh("git", "commit", "-qm", "generated file kept")
    f6 = fp()
    write("src/tệp.ts", "gen v2")
    moved(f6, fp(), "a tracked former artifact (non-ASCII path)")

    # untracked lists files, never a directory entry
    write("gen/sub/a.txt", "x")
    u = fpm.untracked(d)
    if "gen/sub/a.txt" not in u:
        print("FAIL untracked: file not listed")
        bad = 1
    if any(p.endswith("/") for p in u):
        print("FAIL untracked: a directory entry listed")
        bad = 1

    os.chdir("/")

if bad == 0:
    print("OK")
sys.exit(bad)
