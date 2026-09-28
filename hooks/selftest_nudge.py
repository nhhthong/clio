#!/usr/bin/env python3
"""selftest_nudge.py — the smallest check that fails if clio_nudge.py's logic breaks. git only."""
import json
import os
import random
import subprocess
import sys
import tempfile

H = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clio_nudge.py")
tmp = tempfile.TemporaryDirectory()
d = os.path.join(tmp.name, "repo")
marks = os.path.join(tmp.name, "marks")   # outside the repo: markers must not show up in git status
os.makedirs(d)
os.makedirs(marks)
os.chdir(d)
IDX = ".claude/clio/database/index.jsonl"
sid = ""


def git(*a):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t"] + list(a), check=True,
                          stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()


def send(tmpdir=marks):
    env = dict(os.environ, TMPDIR=tmpdir)
    return subprocess.run([sys.executable, H], input=json.dumps({"session_id": sid, "cwd": d}), env=env,
                          stdout=subprocess.PIPE, universal_newlines=True).stdout


def run(**k):
    """A fresh session."""
    global sid
    sid = str(random.getrandbits(48))
    return send(**k)


def fail(msg, out):
    print(msg)
    print(out)
    sys.exit(1)


def quiet(why, **k):
    out = run(**k)
    if out:
        fail("expected silence: " + why, out)


def loud(why, want):
    out = run()
    if want not in out:
        fail("expected '%s': %s" % (want, why), out)


def write(path, text, mode="w"):
    with open(path, mode) as f:
        f.write(text)


def idx(commits):
    write(IDX, json.dumps({"date": "2026-01-01", "type": "task", "doc": "d.md", "commits": commits}) + "\n")


git("init", "-q", ".")
os.makedirs(".claude/clio/database")
write("a.txt", "x\n")
git("add", "-A")
git("commit", "-qm", "one")
quiet("no index.jsonl at all")

idx([])
loud("HEAD in no index record", "appears in no index record")

head = git("rev-parse", "--short=6", "HEAD")
idx([head])
quiet("HEAD indexed, tree clean")

write(IDX, "{broken\n" + json.dumps({"commits": [head]}) + "\n")
quiet("a malformed ledger line must not fake an unindexed HEAD")

write("a.txt", "y\n", "a")
loud("tracked file dirty", "1 uncommitted change")
git("checkout", "-q", "--", "a.txt")

write("b.txt", "new\n")                 # never `git add`ed — `git diff HEAD` cannot see this one
loud("untracked new file", "1 uncommitted change")
# memo ran on uncommitted work: b.txt is in an index record's files, so it is not memo-owed anymore
write(IDX, json.dumps({"commits": [head], "files": ["b.txt"]}) + "\n", "a")
quiet("uncommitted file already recorded by a memo")
os.remove("b.txt")
write("c d é.txt", "new\n")            # git quotes this name without -z; the ledger holds it raw
write(IDX, json.dumps({"commits": [head], "files": ["c d é.txt"]}, ensure_ascii=False) + "\n", "a")
quiet("a recorded path with a space and an accent still matches")
os.remove("c d é.txt")
os.makedirs(".claude/clio/docs/tasks")
write(".claude/clio/docs/tasks/d.md", "z\n")
git("add", "-A")
quiet("only .claude/ changed — that is memo's own output")

write("a.txt", "y\n", "a")
if not run():
    fail("expected a nudge before the dedup check", "")
if send():
    fail("nudged twice in one session", "")

write(IDX, "")
quiet("empty index.jsonl — loop never started")

idx([])                                                   # would nudge — but the marker cannot be written
quiet("marker dir unwritable — silence, not a nag on every prompt", tmpdir=os.path.join(marks, "does/not/exist"))

os.chdir("/")
tmp.cleanup()
print("OK")
