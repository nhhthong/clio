#!/usr/bin/env python3
"""selftest_guard.py — the smallest check that fails if clio_guard.py stops guarding runs.jsonl or the stores."""
import json
import os
import subprocess
import sys
import tempfile

H = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clio_guard.py")
R = ".claude/clio/database/runs.jsonl"
bad = 0
tmp = tempfile.TemporaryDirectory()
C = os.path.join(tmp.name, "clio")        # a repo with .claude/clio
N = os.path.join(tmp.name, "none")        # one without
os.makedirs(os.path.join(C, ".claude/clio/database"))
os.makedirs(N)


def call(tool, key, val, cwd=C):
    inp = json.dumps({"tool_name": tool, "tool_input": {key: val}, "cwd": cwd})
    return subprocess.run([sys.executable, H], input=inp, universal_newlines=True,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode


def deny(*a, **k):
    global bad
    if call(*a, **k) != 2:
        print("expected deny: %s" % (a,))
        bad = 1


def allow(*a, **k):
    global bad
    if call(*a, **k) != 0:
        print("expected allow: %s" % (a,))
        bad = 1


deny("Write", "file_path", "/repo/" + R)
deny("Edit", "file_path", "/repo/" + R)
deny("Bash", "command", "echo '{\"case\":\"x\",\"result\":\"pass\"}' >> " + R)
deny("Bash", "command", "jq -c . x.json | tee -a " + R)
deny("Bash", "command", "sed -i '$d' " + R)
deny("Bash", "command", "cd /repo && rm " + R)
deny("Bash", "command", "cp /tmp/fake " + R)
allow("Bash", "command", "jq -c 'select(.case==\"3.3-u1\")' %s | tail -1" % R)
allow("Bash", "command", "cat %s; grep pass %s" % (R, R))
allow("Bash", "command", "/p/bin/clio test run 3.3-u1   # appends to runs.jsonl")
deny("Bash", "command", "echo x >> %s && /p/bin/clio test run 3.3-u1" % R)   # the writer excuses its own part only
deny("Bash", "command", "/p/bin/myclio tests >> " + R)                        # a look-alike name is no writer
allow("Write", "file_path", "/repo/.claude/clio/docs/tests/auth.md")
allow("Bash", "command", "git status")
deny("Bash", "command", "git restore " + R)                       # reverting drops every uncommitted fail
deny("Bash", "command", "git checkout HEAD -- " + R)
deny("Bash", "command", "mv %s /tmp/old.jsonl" % R)
allow("Bash", "command", "cp %s /tmp/backup.jsonl" % R)            # a copy *from* it is a read
deny("Bash", "command", "echo x >> runs.jsonl", cwd=os.path.join(C, ".claude/clio/database"))   # bare name, inside Clio
allow("Bash", "command", "python train.py > logs/runs.jsonl", cwd=N)                           # another tool, no Clio
deny("Bash", "command", "/p/bin/clio test run 3.3-u1 $(rm %s)" % R)          # a substitution is its own command
deny("Bash", "command", "/p/bin/clio test run 3.3-u1\nrm %s" % R)            # a newline starts another command
deny("Bash", "command", "rm %s  # clio test cleanup" % R)                    # naming the writer in a comment excuses nothing
deny("Bash", "command", "(rm %s)" % R)                                       # a subshell is still rm
deny("Bash", "command", "echo x >| " + R)                                    # clobber redirect
deny("Bash", "command", "sed -E -i s/a/b/ " + R)                             # -i need not come first
# cp/install fail closed: the only pass is `cp <this runs.jsonl> <outside the database dir>`
deny("Bash", "command", "cp /tmp/fake %s  # restoring last week's backup" % R)   # a trailing comment hides no destination
deny("Bash", "command", "cp /tmp/fake %s --preserve=mode" % R)               # an option after the destination
deny("Bash", "command", "cp '/tmp/fake #1' " + R)                            # a quoted # is no comment
deny("Bash", "command", "cp 'a;b' " + R)                                     # a quoted ; splits nothing
deny("Bash", "command", "cp -t .claude/clio/database /tmp/runs.jsonl")       # target-directory form
deny("Bash", "command", "cp /tmp/runs.jsonl .claude/clio/database/")         # a directory destination
deny("Bash", "command", "install -m 644 /tmp/fake " + R)
deny("Bash", "command", "cp 'unbalanced " + R)                               # unparseable → refused
allow("Bash", "command", "cp -p %s /tmp/" % R)
allow("Bash", "command", "ls .claude/clio/database  # runs.jsonl is there")   # a comment is not a write
allow("Bash", "command", "grep pass %s > /tmp/out.txt" % R)

# the plan and test stores: written only by `clio add` and `clio test` (tick) — a hand-written
# `"status":"done"` would tick a task the gate never passed
S = ".claude/clio/database/plan/orders.jsonl"
deny("Write", "file_path", "/repo/" + S)
deny("Edit", "file_path", ".claude/clio/database/test/orders.jsonl")
deny("Bash", "command", "echo '{\"type\":\"task\",\"id\":\"3.1\",\"status\":\"done\"}' >> " + S)
deny("Bash", "command", "cat >> %s <<'EOF'\n{}\nEOF" % S)
deny("Bash", "command", "sed -i '$d' " + S)
deny("Bash", "command", "rm -r .claude/clio/database/test")
deny("Bash", "command", "git checkout -- " + S)
allow("Bash", "command", "/p/bin/clio add plan orders <<'EOF'\n{\"type\":\"task\",\"id\":\"3.1\"}\nEOF")
allow("Bash", "command", "/p/bin/clio test tick 3.1")
allow("Bash", "command", "jq -c . " + S)
allow("Bash", "command", "cp %s /tmp/plan-backup.jsonl" % S)
allow("Write", "file_path", "/repo/test/fixtures/orders.jsonl")                 # the user's own test data
allow("Bash", "command", "echo x >> test/fixtures/orders.jsonl", cwd=N)
allow("Bash", "command", "echo x > src/database/test/seed.sql")                # a project's own database/test dir, in a Clio repo
allow("Bash", "command", "rm -r db/database/plan")

tmp.cleanup()
if bad == 0:
    print("OK")
sys.exit(bad)
