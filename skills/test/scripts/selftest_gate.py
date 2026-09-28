#!/usr/bin/env python3
"""selftest_gate.py — run, approve and gate: evidence, flaky, regression, mutation, malformed rows, Not applicable,
Covers, timeouts, batch approve."""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from selftest_common import (  # noqa: E402
    RUNS, add, done, git, grep, has, ko, lines, miss, ok, okg, out, read, sub, t, write)

P = ".claude/clio/docs/plans/p.md"
Q = ".claude/clio/docs/plans/q.md"
INFRA = ".claude/clio/docs/plans/infra.md"
write(P, "| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n"
      "| 1.1 | a | 1 | unit | – | – | [ ] |\n| 1.2 | b | 1 | critical · unit | – | – | [ ] |\n"
      "| 1.3 | c | 1 | regression | – | – | [ ] |\n| 1.4 | d | 1 | concurrency | – | – | [ ] |\n")
T = ".claude/clio/docs/tests/p.md"
write(T, "| Case | Task | Level | Behaviour | Expected (source) | Command | Repeat |\n|---|---|---|---|---|---|---|\n")
add(T, "| 1.1-u1 | 1.1 | unit | ok | exit 0 | `true` | 3 |",
    "| 1.2-u1 | 1.2 | unit | ok | exit 0 | `true` | 1 |",
    "| 1.3-r1 | 1.3 | regression | bug | exit 0 | `test -f fixed` | 1 |",
    "| 1.4-c1 | 1.4 | concurrency | race | exit 0 | `true` | 5 |")

ko("gate", "1.1")                  # never run
ok("run", "1.1-u1")
okg("1.1")
write("app.txt", "y\n", "a")
ko("gate", "1.1")                  # code changed after the pass
ok("run", "1.1-u1")
okg("1.1")
ok("run", "1.2-u1")
ko("gate", "1.2")                  # critical: a case never seen red
ko("run", "1.3-r1")                # red: bug not fixed yet
write("fixed", "")
ok("run", "1.3-r1")                # then green
okg("1.3")
ok("run", "1.4-c1")
ko("gate", "1.4")                  # concurrency repeat 5 < floor
ko("run", "nope")                  # unknown case
ko("run-task", "7.7")              # a task with no cases
if len(lines(read(RUNS))) < 6:
    miss("runs.jsonl not appended")

# committing the same code keeps the evidence; an artifact the test writes does not invalidate it
ok("run", "1.1-u1")                # 'fixed' above changed the code since the last pass
okg("1.1")
git("add", "-A", "--", ".", ":(exclude).claude")
git("commit", "-qm", "work")
okg("1.1")
add(T, "| 1.1-u2 | 1.1 | unit | writes coverage | exit 0 | `echo c > cover.out` | 1 |")
ok("run", "1.1-u2")
okg("1.1")
add(T, "| 9.9-u1 | 9.9 | unit | orphan | exit 0 | `true` | 1 |")
ok("run", "9.9-u1")
ko("gate", "9.9")                  # task in no plan: no Levels to hold it to

# a pre-4.0 plan table: never gated directly; its sub-task in the re-planned table is
write(".claude/clio/docs/plans/old.md",
      "| # | Task | req | Test that proves it | Needs | Done |\n|---|---|---|---|---|---|\n"
      "| 5.1 | old | 1 | `go test ./x` | – | [x] 2026-01-01 |\n\n## Re-planned\n\n"
      "| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n"
      "| 5.1.1 | bring 5.1 under test | 1 | unit | 5.1 | – | [ ] |\n")
add(T, "| 5.1-u1 | 5.1 | unit | old | exit 0 | `true` | 1 |",
    "| 5.1.1-u1 | 5.1.1 | unit | new | exit 0 | `true` | 1 |")
ok("run", "5.1-u1")
o = out("gate", "5.1")
if "pre-4.0 row" not in o:
    miss("old row not refused: " + o)
ok("run", "5.1.1-u1")
okg("5.1.1")

# coverage: what a re-plan reads — level and last result per case, "no cases" for a pre-4.0 row
if not lines(out("coverage", "1.3")):
    miss("coverage empty")
if not grep("1.3-r1\tregression\tpass", out("coverage", "1.3")):
    miss("coverage lost last result: " + out("coverage", "1.3"))
if out("coverage", "7.7") != "no cases\n":
    miss("coverage of an uncovered task")

# critical: every non-mutation case must have been seen red, but critical alone never asks for mutation
o = out("gate", "1.2")
if "never seen red on a critical task" not in o:
    miss("critical never-red not refused: " + o)
if "level 'mutation'" in o:
    miss("critical demanded mutation: " + o)
# a money task names `mutation` itself; `Mutation: none` in infra.md waives it
add(P, "| 1.6 | money | 1 | critical · unit, mutation | – | – | [ ] |")
add(T, "| 1.6-u1 | 1.6 | unit | x | x | `true` | 1 |")
t("run", "1.6-u1")
has("1.6", "plan requires level 'mutation'")
write(INFRA, "# Plan — infra\nMutation: none (ADR 1790000000_no-mutation)\n")
has("1.6", "says `Mutation: none`")   # a row naming mutation against the ADR is refused, not waived
add(T, "| 1.2-u2 | 1.2 | unit | critical red then green | exit 0 | `test -f crit-ok` | 1 |")
ko("run", "1.2-u2")
write("crit-ok", "")
ok("run", "1.2-u2")
if "1.2-u2: never seen red" in out("gate", "1.2"):
    miss("a case seen red still flagged")

# mutation: the command's own exit code is not trusted alone — its text must show a real threshold
write(INFRA, "# Plan — infra\nMutation: stryker (ADR 1790000000_stryker)\n")
add(P, "| 1.7 | zeroed | 1 | mutation | – | – | [ ] |", "| 1.8 | honest | 1 | mutation | – | – | [ ] |")
add(T, "| 1.7-m1 | 1.7 | mutation | x | x | `true --thresholds.break 0` | 1 |",
    "| 1.8-m1 | 1.8 | mutation | x | x | `true --thresholds.break 85` | 1 |")
t("approve", "1.7")
t("run", "1.7-m1")
has("1.7", "no threshold >= 80%")   # 0 does not clear the default
t("approve", "1.8")
t("run", "1.8-m1")
okg("1.8")                          # 85 clears it
# a project threshold above default (90%) holds even a normally-fine 85 to the higher bar
write(INFRA, "# Plan — infra\nMutation: stryker (ADR 1790000000_stryker, 90%)\n")
has("1.8", "no threshold >= 90%")
os.remove(INFRA)

# the approved table is the definition of done: deleting a failing case or lowering Repeat voids it
t("run", "1.1-u1")
t("run", "1.1-u2")
has("1.1", "OK: task 1.1")
sub(T, "| `true` | 3 |", "| `true` | 1 |")
has("1.1", "changed since it was approved")
t("approve", "1.1")
has("1.1", "OK: task 1.1")
write(Q, "| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n"
      "| 2.1 | never approved | 1 | unit | – | – | [ ] |\n")
add(T, "| 2.1-u1 | 2.1 | unit | x | x | `true` | 1 |")
t("run", "2.1-u1")
has("2.1", "never approved")

# flaky: red then green on the same code is not a pass; nor is red then green on the same code later
add(Q, "| 2.2 | flaky | 1 | unit | – | – | [ ] |", "| 2.3 | reg | 1 | regression | – | – | [ ] |",
    "| 2.4 | sup | 1 | unit | – | – | superseded 2026-01-01 → 2.4.1 |",
    "| 2.5 | bad level | 1 | Concurrency | – | – | [ ] |")
add(T, "| 2.2-u1 | 2.2 | unit | x | x | `bash flaky.sh` | 1 |")
write("flaky.sh", "test -f .f1 || { touch .f1; exit 1; }\n")
git("add", "flaky.sh")
git("commit", "-qm", "f")
write(".gitignore", ".f1\n")
t("approve", "2.2")
t("run", "2.2-u1")
ok("run", "2.2-u1")
ok("gate", "2.2")                   # fail before the first pass: forgiven
os.remove(".f1")
t("run", "2.2-u1")
ok("run", "2.2-u1")
has("2.2", "flaky")                 # fail after a pass, same code

# regression red must be the same command, on other code: swapping `false` → `true` proves nothing
add(T, "| 2.3-r1 | 2.3 | regression | x | x | `false` | 1 |")
t("run", "2.3-r1")
sub(T, "| 2.3-r1 | 2.3 | regression | x | x | `false` | 1 |", "| 2.3-r1 | 2.3 | regression | x | x | `true` | 1 |")
t("approve", "2.3")
ok("run", "2.3-r1")
has("2.3", "regression case never failed")

# malformed rows fail loudly: superseded task, level outside the catalog, `|` in a command, bad Repeat
add(T, "| 2.4-u1 | 2.4 | unit | x | x | `true` | 1 |")
t("approve", "2.4")
t("run", "2.4-u1")
has("2.4", "superseded")
add(T, "| 2.5-c1 | 2.5 | Concurrency | x | x | `true` | 1 |")
ko("run", "2.5-c1")
t("approve", "2.5")
has("2.5", "plan level 'Concurrency'")
add(T, "| 2.2-u2 | 2.2 | unit | pipe | x | `true || false` | 3 |")
o = out("run", "2.2-u2")
if "splits into" not in o:
    miss("pipe row ran: " + o)
add(T, "| 2.2-u3 | 2.2 | unit | rep | x | `true` | many |")
o = out("run", "2.2-u3")
if "not a whole number" not in o:
    miss("bad Repeat ran: " + o)

# a table inside <!-- --> is not read: its task is in no plan, its cases in no tests file
write(".claude/clio/docs/plans/hid.md", "<!--\n| # | Task | req | Levels | Needs | Touches | Done |\n"
      "|---|---|---|---|---|---|---|\n| 3.1 | hidden | 1 | unit | – | – | [ ] |\n-->\n")
add(T, "<!-- | 3.1-u1 | 3.1 | unit | x | x | `true` | 1 | -->")
o = out("run", "3.1-u1")
if "in no" not in o:
    miss("commented case ran: " + o)
add(T, "| 3.1-u2 | 3.1 | unit | x | x | `true` | 1 |")
t("approve", "3.1")
t("run", "3.1-u2")
has("3.1", "in no .claude/clio/docs/plans")

# one case, one command: a second level riding on the same command is refused
add(Q, "| 3.2 | dup | 1 | api, security | – | – | [ ] |")
add(T, "| 3.2-a1 | 3.2 | api | x | x | `test -d .git` | 1 |", "| 3.2-s1 | 3.2 | security | x | x | `test -d .git` | 1 |")
t("approve", "3.2")
t("run", "3.2-a1")
t("run", "3.2-s1")
has("3.2", "run the same command")

# .claude never counts, even staged and then edited again (git rm --cached refuses that without -f)
write(".claude/note.txt", "0\n")
git("add", ".claude/note.txt")
write(".claude/note.txt", "1\n", "a")
f1 = out("fp")
git("add", ".claude/note.txt")
write(".claude/note.txt", "2\n", "a")
f2 = out("fp")
if f1 != f2:
    miss("a staged-and-edited file under .claude moved the fingerprint")
git("rm", "-q", "-f", "--cached", ".claude/note.txt")
os.remove(".claude/note.txt")

# a directory a run created is not a hiding place: code written into it later changes the fingerprint
add(T, "| 3.3-u1 | 3.3 | unit | gen | x | `mkdir -p gen && echo a > gen/out.txt` | 1 |")
t("run", "3.3-u1")
f1 = out("fp")
write("gen/logic.go", "code\n")
f2 = out("fp")
if f1 == f2:
    miss("source added to an artifact directory is invisible to fp")
write("gen/out.txt", "y\n")
if f2 != out("fp"):
    miss("the artifact file itself changed fp")
shutil.rmtree("gen")

# regression that never failed is rejected
add(T, "| 1.3-r2 | 1.3 | regression | bug2 | exit 0 | `true` | 1 |")
t("run", "1.3-r2")
ko("gate", "1.3")

# Covers: LEVELS.md gives `contract` two ids. A new-format table (with the Covers column) is held to
# both — one covered by a case, no case and no excuse for the other — the gate names the missing one.
add(Q, "| 4.1 | sync | 1 | contract | – | – | [ ] |", "| 4.2 | sync2 | 1 | contract | – | – | [ ] |")
write(T, "\n| Case | Task | Level | Covers | Behaviour | Expected (source) | Command | Repeat |\n"
      "|---|---|---|---|---|---|---|---|\n", "a")
add(T, "| 4.1-c1 | 4.1 | contract | contract.1 | consumer | x | `true c1` | 1 |")
t("approve", "4.1")
t("run", "4.1-c1")
has("4.1", "no case covering contract.2")
add(T, "| 4.1-c2 | 4.1 | contract | contract.2 | provider | x | `true c2` | 1 |")
t("approve", "4.1")
t("run", "4.1-c2")
okg("4.1")                           # both ids now covered

# a `Not applicable` line excuses an id without a case for it
add(T, "| 4.2-c1 | 4.2 | contract | contract.1 | consumer | x | `true c3` | 1 |")
write(T, "\nNot applicable:\n- 4.2 · contract.2 — the provider will not run a contract test\n", "a")
t("approve", "4.2")
t("run", "4.2-c1")
okg("4.2")

# pre-4.1 rows (no Covers column) are grandfathered: task 1.2's `unit` case above never names
# `unit.1`, and every case run earlier in this file passed gate all along — nothing new to flag here.
o = out("gate", "1.2")
if "no case covering" in o:
    miss("a pre-4.1 row was held to a Covers id it never had a column for: " + o)

# coverage() reads the shifted Covers-column layout too, not just gate()
if not grep("4.1-c1\tcontract\tpass", out("coverage", "4.1")):
    miss("coverage lost a Covers-column case: " + out("coverage", "4.1"))

# a malformed row (a `|` inside its command) must not leak the PRECEDING row's Covers value into the
# next task's coverage — even across a task boundary, since cases() sees every file's rows in order
# before gate() ever filters by task. Before the fix this let an unrelated bullet look covered.
add(Q, "| 4.4 | leakA | 1 | security | – | – | [ ] |", "| 4.5 | leakB | 1 | security | – | – | [ ] |")
add(T, "| 4.4-s1 | 4.4 | security | security.1 | authn | x | `true c7` | 1 |",
    "| 4.5-s1 | 4.5 | security | security.2 | x | x | `true || false` | 1 |",    # malformed, right after 4.4-s1
    "| 4.5-s2 | 4.5 | security | security.6 | biz | x | `true c8` | 1 |")        # legit: satisfies "a case exists"
t("approve", "4.4")
t("run", "4.4-s1")
t("approve", "4.5")
t("run", "4.5-s1")
t("run", "4.5-s2")
o = out("gate", "4.5")
if "no case covering security.1" not in o:
    miss("a malformed row leaked another task's Covers value: " + o)

# run-task: every case of a task in one call — what /clio:test hands the user — then the gate holds
o = out("run-task", "1.1")
if "task 1.1: 2/2 cases passed" not in o:
    miss("run-task 1.1: " + o)
okg("1.1")
add(T, "| 8.1-u1 | 8.1 | unit | red | exit 0 | `false` | 1 |", "| 8.1-u2 | 8.1 | unit | green | exit 0 | `true` | 1 |")
rc, o = t("run-task", "8.1")
if rc == 0:
    miss("run-task with a red case exited 0")
if "task 8.1: 1/2 cases passed" not in o:
    miss("run-task stopped at the first red: " + o)

# 4.2.0 — a `Not applicable` line added after approve voids the approval, like an edited case
add(P, "| 9.1 | na | 1 | unit | – | – | [ ] |", "| 9.2 | mut | 1 | mutation | – | – | [ ] |",
    "| 9.3 | fake red | 1 | critical · unit | – | – | [ ] |", "| 9.4 | real red | 1 | critical · unit | – | – | [ ] |",
    "| 9.5 | hang | 1 | unit | – | – | [ ] |")
T2 = ".claude/clio/docs/tests/q.md"
write(T2, "| Case | Task | Level | Covers | Behaviour | Expected | Command | Repeat |\n|---|---|---|---|---|---|---|---|\n")
add(T2, "| 9.1-u1 | 9.1 | unit | unit.1 | x | x | `true` | 1 |")
ok("run", "9.1-u1")
okg("9.1")
write(T2, "\nNot applicable:\n- 9.1 · unit.1 — slipped in after the yes\n", "a")
has("9.1", "changed since it was approved")
okg("9.1")                           # the user approves the excuse too: holds again

# mutation: only a named threshold flag counts, every one of them, and a `#` is refused
write(INFRA, "# Plan — infra\nMutation: stryker (ADR 1790000000_stryker)\n")


def mut(cmd):
    write(T2, "".join(l for l in read(T2).splitlines(True) if not l.startswith("| 9.2-m1 ")))
    add(T2, "| 9.2-m1 | 9.2 | mutation | – | x | x | `%s` | 1 |" % cmd)
    t("approve", "9.2")
    t("run", "9.2-m1")


mut("true --thresholds.break 0 # 80")
has("9.2", "contains `#`")
mut("true --thresholds.break 0 --min-score 90")
has("9.2", "no threshold >= 80%")
mut("true --port 8080 --thresholds.break 0")
has("9.2", "no threshold >= 80%")
mut("true -DmutationThreshold=85")
ok("gate", "9.2")

# a hung case fails at CLIO_TIMEOUT instead of blocking the run
add(T2, "| 9.5-u1 | 9.5 | unit | unit.1 | x | x | `sleep 5` | 1 |")
rc, o = t("run", "9.5-u1", env={"CLIO_TIMEOUT": "1"})
if rc == 0:
    miss("hung case passed")
if "timed out after 1s" not in o:
    miss("timeout not reported: " + o)

# batch: one approve and one run-task over several tasks; a bad id in the batch approves/runs nothing
add(P, "| 9.6 | b1 | 1 | unit | – | – | [ ] |", "| 9.7 | b2 | 1 | unit | – | – | [ ] |")
add(T2, "| 9.6-u1 | 9.6 | unit | unit.1 | x | x | `true` | 1 |", "| 9.7-u1 | 9.7 | unit | unit.1 | x | x | `test -d .` | 1 |")
n0 = len(lines(read(RUNS)))
ko("approve", "9.6", "9.9x")
ko("run-task", "9.6", "9.9x")
if len(lines(read(RUNS))) != n0:
    miss("a batch with a bad id still wrote records")
o = out("run-task", "9.6", "9.7")
if "all: 2/2 cases passed across 2 tasks" not in o:
    miss("batch run-task: " + o)
ok("approve", "9.6", "9.7")
ok("gate", "9.6")
ok("gate", "9.7")
sub(T2, "| `test -d .` |", "| `test -d ./` |")      # edit 9.7's table: only its approval is void
ok("gate", "9.6")
has("9.7", "changed since it was approved")

done()
