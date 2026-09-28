#!/usr/bin/env python3
"""selftest_red.py — what counts as red: the test unchanged and the code different, by hand or through `red`
on the base commit in a kept worktree."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from selftest_common import (  # noqa: E402
    CASE_HEAD, PLAN_HEAD, add, done, git, grep, has, ko, miss, ok, okg, out, read, t, write)

P = ".claude/clio/docs/plans/p.md"
write(P, PLAN_HEAD + "| 9.3 | fake red | 1 | critical · unit | – | – | [ ] |\n| 9.4 | real red | 1 | critical · unit | – | – | [ ] |\n")
T2 = ".claude/clio/docs/tests/q.md"
write(T2, CASE_HEAD)

# red counts only with the test unchanged and the code different: breaking the test proves nothing
add(T2, "| 9.3-u1 | 9.3 | unit | unit.1 | x | x | `bash chk_test.sh` | 1 |")
write("chk_test.sh", "exit 1\n")
ko("run", "9.3-u1")
write("chk_test.sh", "exit 0\n")
ok("run", "9.3-u1")
t("approve", "9.3")
has("9.3", "never seen red on a critical task")
add(T2, "| 9.4-u1 | 9.4 | unit | unit.1 | x | x | `bash impl_test.sh` | 1 |")
write("impl_test.sh", "test -f impl94\n")
ko("run", "9.4-u1")
write("impl94", "")
ok("run", "9.4-u1")
okg("9.4")

# red: the cases that must be seen red run on the base commit's code with today's tests — no hand edits
add(P, "| 8.8 | crit red | 1 | critical · unit | – | – | [ ] |", "| 8.9 | plain | 1 | unit | – | – | [ ] |")
write("impl99.txt", "old\n")
git("add", "impl99.txt")
git("commit", "-qm", "impl99 before the change")
write("impl99.txt", "new\n")                        # the change, uncommitted
write("chk99_test.sh", "grep -q new impl99.txt\n")  # its test, a test file by name
add(T2, "| 8.8-u1 | 8.8 | unit | unit.1 | x | x | `bash chk99_test.sh` | 1 |",
    "| 8.9-u1 | 8.9 | unit | unit.1 | x | x | `test -f impl99.txt` | 1 |")
ok("run", "8.8-u1")
t("approve", "8.8")
has("8.8", "clio test red 8.8")                     # green alone is not enough on a critical task
o = out("red", "8.8")
if not grep("red on .*: 1/1 cases failed as they must", o):
    miss("red 8.8: " + o)
# the worktree is kept, under the git dir, and the user's working tree is never touched
wl = git("worktree", "list")
if not grep(r"/\.git/clio-red ", wl):
    miss("red worktree not kept at .git/clio-red: " + wl)
if read("impl99.txt") != "new\n":
    miss("red touched the working tree")
if os.path.exists(".git/clio-red.lock"):
    miss("red left its lock behind")
if "reusing the red worktree" not in out("red", "8.8"):
    miss("same base: worktree not reused")
if "reusing" in out("red", "8.8", "--fresh"):
    miss("--fresh reused the worktree")
os.mkdir(".git/clio-red.lock")
ko("red", "8.8")                                    # one red at a time
os.rmdir(".git/clio-red.lock")
# a nested, ignored dependency dir (frontend/node_modules) is linked into the worktree
write(".gitignore", "node_modules/\n", "a")
write("frontend/node_modules/pkg/i.js", "x\n")
t("red", "8.8")
if not os.path.islink(".git/clio-red/frontend/node_modules"):
    miss("nested node_modules not linked")
ok("run", "8.8-u1")
ok("gate", "8.8")                                   # red then green, same tests: the gate counts it
if "nothing needs red" not in out("red", "8.9"):
    miss("red on a plain task ran something")
git("add", "impl99.txt", "chk99_test.sh")
git("commit", "-qm", "change committed")
if not grep("NOT RED: 8.8-u1.*--base", out("red", "8.8")):   # base == today's code
    miss("committed change not explained")
o = out("red", "8.8", "--base", "HEAD~1")
if "1/1 cases failed as they must" not in o:
    miss("red --base: " + o)
write("pass99_test.sh", "true\n")
add(T2, "| 8.8-u2 | 8.8 | unit | unit.1 | y | y | `bash pass99_test.sh` | 1 |")
if "NOT RED: 8.8-u2" not in out("red", "8.8", "--base", "HEAD~1"):
    miss("a case passing on the base not flagged")

# 8.8-u2 passes on the base: its behaviour predates the task. A green alone does not clear it on a
# critical task; an approved `Red waived:` line does — but only on top of that tried red
t("approve", "8.8")
ok("run-task", "8.8")
has("8.8", "Red waived:` line the user approves")
write(T2, "\nRed waived:\n- 8.8-u2 — correct since before HEAD~1; red --base HEAD~1 passed\n", "a")
has("8.8", "changed: `Not applicable` / `Red waived` lines;")   # the gate says what moved — and only that
t("approve", "8.8")
ok("gate", "8.8")
if "NOTE: 8.8-u2: red waived" not in out("gate", "8.8"):
    miss("waiver not reported")
# a waiver on a case no `red` was ever tried for stands on nothing
add(P, "| 8.6 | untried waiver | 1 | critical · unit | – | – | [ ] |")
write("never_test.sh", "true\n")
add(T2, "| 8.6-u1 | 8.6 | unit | unit.1 | z | z | `bash never_test.sh` | 1 |")
write(T2, "\nRed waived:\n- 8.6-u1 — waived without ever trying red\n", "a")
t("approve", "8.6")
ok("run-task", "8.6")
has("8.6", "8.6-u1: red waived, but no `red` run of it passed")   # a waiver stands only on a tried red

# a passing mutation case on a critical task stands in for red on its other cases
add(P, "| 8.7 | mutation covers | 1 | critical · unit, mutation | – | – | [ ] |")
write("mut_test.sh", "exit 0\n")
add(T2, "| 8.7-u1 | 8.7 | unit | unit.1 | a | a | `bash mut_test.sh` | 1 |",
    "| 8.7-m1 | 8.7 | mutation | – | b | b | `bash mut_test.sh --min-score 90` | 1 |")
t("approve", "8.7")
ok("run-task", "8.7")
ok("gate", "8.7")
if "NOTE: 8.7-u1: no red of its own — covered by mutation case 8.7-m1" not in out("gate", "8.7"):
    miss("mutation did not cover red")

# history: every run of a case, the red ones marked
if not grep("fail .* red@", out("history", "8.8-u1")):
    miss("history lacks the red run: " + out("history", "8.8-u1"))
if out("history", "9.9-nope") != "no runs recorded for 9.9-nope\n":
    miss("history of an unknown case")

done()
