#!/usr/bin/env python3
"""selftest_gate.py — run, approve, gate and tick: evidence, flaky, regression, mutation, malformed
records, Not applicable, Covers, timeouts, batch approve, one id one area, the store's bad lines."""
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from selftest_common import (  # noqa: E402
    RUNS, add_records, case, clio, done, git, grep, has, ko, lines, meta, miss, mutation, ok, okg, out, raw, read, t, task, write)
from cliolib import store  # noqa: E402

task("1.1", ["unit"])
task("1.2", ["unit"], critical=True)
task("1.3", ["regression"])
task("1.4", ["concurrency"])
case("1.1-u1", "1.1", "unit", "true", 3)
case("1.2-u1", "1.2", "unit", "true")
case("1.3-r1", "1.3", "regression", "test -f fixed")
case("1.4-c1", "1.4", "concurrency", "true", 5)

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
case("1.1-u2", "1.1", "unit", "echo c > cover.out")
ok("run", "1.1-u2")
okg("1.1")
case("9.9-u1", "9.9", "unit", "true")
ok("run", "9.9-u1")
ko("gate", "9.9")                  # task in no plan: no levels to hold it to

# superseded and void tasks are never gated; the task that replaced one is
task("5.1", ["unit"], status="superseded", by="5.1.1")
task("5.1.1", ["unit"])
task("5.2", ["unit"], status="void")
case("5.1-u1", "5.1", "unit", "true")
case("5.1.1-u1", "5.1.1", "unit", "true")
case("5.2-u1", "5.2", "unit", "true")
ok("run", "5.1-u1")
has("5.1", "is superseded")
ok("run", "5.2-u1")
has("5.2", "is void")
ok("run", "5.1.1-u1")
okg("5.1.1")

task("5.9", ["unit"], status="void")      # no cases at all: the gate says the task is void, not "run /clio:test"
if "is void" not in out("gate", "5.9"):
    miss("a void task without cases: " + out("gate", "5.9"))

# coverage: what a re-plan reads — level and last result per case
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
# a money task names `mutation` itself; a mutation record with tool none waives it
task("1.6", ["unit", "mutation"], critical=True)
case("1.6-u1", "1.6", "unit", "true")
t("run", "1.6-u1")
has("1.6", "plan requires level 'mutation'")
mutation("none")
has("1.6", "says tool none")      # a task naming mutation against the ADR is refused, not waived
case("1.2-u2", "1.2", "unit", "test -f crit-ok")
ko("run", "1.2-u2")
write("crit-ok", "")
ok("run", "1.2-u2")
if "1.2-u2: never seen red" in out("gate", "1.2"):
    miss("a case seen red still flagged")

# mutation: the command's own exit code is not trusted alone — its text must show a real threshold
mutation("stryker")
task("1.7", ["mutation"])
task("1.8", ["mutation"])
case("1.7-m1", "1.7", "mutation", "true --thresholds.break 0")
case("1.8-m1", "1.8", "mutation", "true --thresholds.break 85")
t("approve", "1.7")
t("run", "1.7-m1")
has("1.7", "no threshold >= 80%")   # 0 does not clear the default
t("approve", "1.8")
t("run", "1.8-m1")
okg("1.8")                          # 85 clears it
# a project threshold above default (90%) holds even a normally-fine 85 to the higher bar
mutation("stryker", 90)
has("1.8", "no threshold >= 90%")
mutation("stryker")

# the approved table is the definition of done: lowering Repeat or removing a case voids it
t("run", "1.1-u1")
t("run", "1.1-u2")
has("1.1", "OK: task 1.1")
case("1.1-u1", "1.1", "unit", "true", 1)
has("1.1", "changed since it was approved")
t("approve", "1.1")
has("1.1", "OK: task 1.1")
case("1.1-u2", "1.1", "unit", "echo c > cover.out", status="removed")
has("1.1", "changed since it was approved")
t("approve", "1.1")
case("1.1-u1", "1.1", "unit", "true", 1, date="2026-02-02")   # re-recorded unchanged: the date is not hashed
has("1.1", "OK: task 1.1")
task("2.1", ["unit"], area="q")
case("2.1-u1", "2.1", "unit", "true", area="q")
t("run", "2.1-u1")
has("2.1", "never approved")

# flaky: red then green on the same code is not a pass; nor is red then green on the same code later
task("2.2", ["unit"], area="q")
task("2.3", ["regression"], area="q")
task("2.5", ["Concurrency"], area="q")
case("2.2-u1", "2.2", "unit", "bash flaky.sh", area="q")
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
case("2.3-r1", "2.3", "regression", "false", area="q")
t("run", "2.3-r1")
case("2.3-r1", "2.3", "regression", "true", area="q")
t("approve", "2.3")
ok("run", "2.3-r1")
has("2.3", "regression case never failed")

# malformed records fail loudly: a level outside the catalog, a two-line command, a bad repeat
case("2.5-c1", "2.5", "Concurrency", "true", area="q")
ko("run", "2.5-c1")
t("approve", "2.5")
has("2.5", "plan level 'Concurrency'")
case("2.2-u2", "2.2", "unit", "true\nfalse", 3, area="q")
o = out("run", "2.2-u2")
if "command must be one non-empty line" not in o:
    miss("two-line command ran: " + o)
case("2.2-u3", "2.2", "unit", "true", "many", area="q")
o = out("run", "2.2-u3")
if "whole number" not in o:
    miss("bad repeat ran: " + o)
# a `|` is just shell now: the cell boundary it used to break is gone
task("2.6", ["unit"], area="q")
case("2.6-u1", "2.6", "unit", "true || false", area="q")
t("approve", "2.6")
ok("run", "2.6-u1")
okg("2.6")

# one id, one area: a task held by two plan files is refused, so neither borrows the other's evidence
task("2.6", ["unit"], area="r")
has("2.6", "lives in")
case("2.6-u1", "2.6", "unit", "true", area="r")
o = out("run", "2.6-u1")
if "two area files" not in o:
    miss("a case in two areas ran: " + o)
os.remove(store.path_of("plan", "r"))
os.remove(store.path_of("test", "r"))
okg("2.6")

# a store line that is not JSON may be the newer state of the very case being gated: refuse until fixed
p = store.path_of("test", "q")
keep = read(p)
write(p, "{broken\n", "a")
has("2.6", "is not a JSON record")
write(p, keep)
okg("2.6")

# one case, one command: a second level riding on the same command is refused
task("3.2", ["api", "security"], area="q")
case("3.2-a1", "3.2", "api", "test -d .git", area="q")
case("3.2-s1", "3.2", "security", "test -d .git", area="q")
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
task("3.3", ["unit"], area="q")
case("3.3-u1", "3.3", "unit", "mkdir -p gen && echo a > gen/out.txt", area="q")
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
case("1.3-r2", "1.3", "regression", "true")
t("run", "1.3-r2")
ko("gate", "1.3")

# Covers: LEVELS.md gives `contract` two ids. One covered by a case, no case and no excuse for the
# other — the gate names the missing one.
task("4.1", ["contract"], area="q")
task("4.2", ["contract"], area="q")
case("4.1-c1", "4.1", "contract", "true c1", area="q", covers=["contract.1"])
t("approve", "4.1")
t("run", "4.1-c1")
has("4.1", "no case covering contract.2")
case("4.1-c2", "4.1", "contract", "true c2", area="q", covers=["contract.2"])
t("approve", "4.1")
t("run", "4.1-c2")
okg("4.1")                           # both ids now covered

# a meta `na` entry excuses an id without a case for it
case("4.2-c1", "4.2", "contract", "true c3", area="q", covers=["contract.1"])
meta("4.2", area="q", na={"contract.2": "the provider will not run a contract test"})
t("approve", "4.2")
t("run", "4.2-c1")
okg("4.2")

# a case that names no covers (migrated from a pre-4.1 table) is held to none, as it was before
o = out("gate", "1.2")
if "no case covering" in o:
    miss("a covers-less case was held to an id: " + o)
if not grep("4.1-c1\tcontract\tpass", out("coverage", "4.1")):
    miss("coverage lost a covers case: " + out("coverage", "4.1"))

# run-task: every case of a task in one call — what /clio:test hands the user — then the gate holds
o = out("run-task", "1.1")
if "task 1.1: 1/1 cases passed" not in o:
    miss("run-task 1.1: " + o)
okg("1.1")
task("8.1", ["unit"], area="q")
case("8.1-u1", "8.1", "unit", "false", area="q")
case("8.1-u2", "8.1", "unit", "true", area="q")
rc, o = t("run-task", "8.1")
if rc == 0:
    miss("run-task with a red case exited 0")
if "task 8.1: 1/2 cases passed" not in o:
    miss("run-task stopped at the first red: " + o)

# an excuse added after approve voids the approval, like an edited case
for tid in ("9.1", "9.2", "9.5", "9.6", "9.7"):
    task(tid, ["mutation"] if tid == "9.2" else ["unit"], area="q")
case("9.1-u1", "9.1", "unit", "true", area="q", covers=["unit.1"])
ok("run", "9.1-u1")
okg("9.1")
meta("9.1", area="q", na={"unit.1": "slipped in after the yes"})
has("9.1", "changed since it was approved")
okg("9.1")                           # the user approves the excuse too: holds again


# mutation: only a named threshold flag counts, every one of them, and a `#` is refused
def mut(cmd):
    case("9.2-m1", "9.2", "mutation", cmd, area="q")
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

# exit 0 without a test is not a pass: a deleted or renamed test must not keep its case green
task("9.8", ["unit"], area="q")
for n, cmd in enumerate(("echo 'ok  \tgoremi/internal/ui\t(cached) [no tests to run]'",
                         "printf 'running 0 tests\\n'", "echo 'Ran 0 tests in 0.000s'")):
    case("9.8-v%d" % n, "9.8", "unit", cmd, area="q", covers=["unit.1"])
    rc, o = t("run", "9.8-v%d" % n)
    if rc == 0 or "ran no test" not in o:
        miss("a command that ran no test passed (%s): %s" % (cmd[:30], o))
case("9.8-p1", "9.8", "unit", "printf 'ok  \\tpkg/a\\t0.2s [no tests to run]\\nok  \\tpkg/b\\t0.3s\\n'", area="q", covers=["unit.1"])
if t("run", "9.8-p1")[0] != 0:
    miss("one package ran, the others had none: that is a pass")

# a hung case fails at CLIO_TIMEOUT instead of blocking the run
case("9.5-u1", "9.5", "unit", "sleep 5", area="q", covers=["unit.1"])
rc, o = t("run", "9.5-u1", env={"CLIO_TIMEOUT": "1"})
if rc == 0:
    miss("hung case passed")
if "timed out after 1s" not in o:
    miss("timeout not reported: " + o)
rc, o = t("run", "9.5-u1", env={"CLIO_TIMEOUT": "3", "CLIO_HEARTBEAT": "1"})
if "still running after 1 s (cap 3 s" not in o or "still running after 3 s" in o or "timed out after 3s" not in o:
    miss("heartbeat wrong: " + o)

# batch: one approve and one run-task over several tasks; a bad id in the batch approves/runs nothing
case("9.6-u1", "9.6", "unit", "true", area="q", covers=["unit.1"])
case("9.7-u1", "9.7", "unit", "test -d .", area="q", covers=["unit.1"])
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
case("9.7-u1", "9.7", "unit", "test -d ./", area="q", covers=["unit.1"])   # edit 9.7's case: only its approval is void
ok("gate", "9.6")
has("9.7", "changed since it was approved")

# run-task names the other tasks whose touches overlap, open or done: a change here may break them
task("6.1", ["unit"], area="q", touches=["orders/"])
task("6.2", ["unit"], area="q", touches=["orders/repo.go"])
task("6.3", ["unit"], area="q", touches=["billing/x.go"])
task("6.4", ["unit"], area="q", touches=["orders/repo.go"], status="void")
for tid in ("6.1", "6.2", "6.3", "6.4"):
    case(tid + "-u1", tid, "unit", "true " + tid, area="q")
o = out("run-task", "6.1")
if not grep(r"^      6\.2 \(orders/repo\.go\)$", o) or "6.3" in o or "6.4" in o:
    miss("shared-touches note wrong: " + o)

# a hub file shared by many tasks is counted, not listed in full
for n in range(12):
    task("6.9%d" % n, ["unit"], area="q", touches=["orders/repo.go"])
    case("6.9%d-u1" % n, "6.9%d" % n, "unit", "true h%d" % n, area="q")
o = out("run-task", "6.2")
if "13 other task(s)" not in o and "12 other task(s)" not in o:
    miss("hub note has no count: " + o)
if not grep(r"… and [0-9]+ more", o) or len(re.findall(r"(?m)^      6\.", o)) > 10:
    miss("hub note not capped: " + o)

# diff: what changed since the approval, one line per kind of edit across cases
task("6.5", ["unit"], area="q")
case("6.5-u1", "6.5", "unit", "true a", area="q", expected="100")
case("6.5-u2", "6.5", "unit", "true b", area="q", expected="100")
t("approve", "6.5")
if "no change since" not in out("diff", "6.5"):
    miss("diff right after approve: " + out("diff", "6.5"))
case("6.5-u1", "6.5", "unit", "true a", area="q", expected="99")
case("6.5-u2", "6.5", "unit", "true b", area="q", expected="99")
case("6.5-u3", "6.5", "unit", "true c", area="q")
meta("6.5", area="q", na={"unit.1": "x"})
o = out("diff", "6.5")
for want in ('expected: "100" → "99" — 6.5-u1, 6.5-u2', "added: 6.5-u3", "+ - 6.5 · unit.1 — x"):
    if want not in o:
        miss("diff lacks [%s]: %s" % (want, o))

# tick: the only way to done, and only on a passing gate; a done task then takes only its commit
plan_q = store.path_of("plan", "q")
o = out("tick", "9.7")
if "not ticked" not in o:
    miss("tick passed a failing gate: " + o)
if '"status":"done"' in read(plan_q):
    miss("a failed tick still wrote done")
ok("tick", "9.6")
if '"id":"9.6","date"' not in read(plan_q) or '"status":"done"' not in read(plan_q):
    miss("tick did not record done: " + read(plan_q))
ok("tick", "9.6", "--commit", "abc1234")
if '"commit":"abc1234"' not in read(plan_q):
    miss("tick --commit on a done task did not record the hash")
o = out("tick", "9.6", "--commit", "def5678")
if "is not overwritten" not in o or '"commit":"def5678"' in read(plan_q):
    miss("a recorded commit was overwritten: " + o)
if not grep(r"^q: done=1 ", clio("q", "summary")[1]):
    miss("summary does not count the ticked task: " + clio("q", "summary")[1])
raw("plan", "q", {"type": "task", "id": "9.6", "date": "x", "task": "t", "req": [], "levels": ["unit"],
                  "critical": False, "needs": [], "touches": [], "na": {}, "status": "open", "by": None,
                  "commit": None, "delta": None})   # a later record is the task's state, whatever came before
if not grep(r"^q: done=0 ", clio("q", "summary")[1]):
    miss("summary does not read the last record per id: " + clio("q", "summary")[1])

# withdraw: done work that never left the working tree can be taken back, and only that
INDEX = ".claude/clio/database/index.jsonl"
os.makedirs("w", exist_ok=True)
write("w/a.txt", "a\n")
git("add", "w/a.txt")
git("commit", "-qm", "w base")                      # w/ is clean at HEAD
task("8.51", ["unit"], area="w", touches=["w/a.txt"])
task("8.52", ["unit"], area="w", touches=["w/"], needs=["8.51"])
task("8.53", ["unit"], area="w", touches=["w/b.txt"])
task("8.54", ["unit"], area="w")
for tid in ("8.51", "8.52", "8.53", "8.54"):
    case(tid + "-u1", tid, "unit", "true " + tid, area="w", covers=["unit.1"])
    t("approve", tid)
    ok("run", tid + "-u1")
    ok("tick", tid)
write(INDEX, '{"date":"2026-10-08","id":"1","type":"task","doc":"d1.md","domain":"x","plan_tasks":["8.51","8.52"],"files":[],"commits":[],"keywords":["k"],"specs":[],"req":[]}\n'
     '{"date":"2026-10-08","id":"2","type":"task","doc":"d2.md","domain":"x","plan_tasks":["8.54","8.60"],"files":[],"commits":[],"keywords":["k"],"specs":[],"req":[]}\n', "a")
o = out("withdraw", "8.51")                           # 8.52 is done and needs it
if "8.52 is done and needs 8.51" not in o or "nothing withdrawn" not in o:
    miss("withdrew a task a done task stands on: " + o)
write("w/a.txt", "changed\n")
o = out("withdraw", "8.51", "8.52")                   # its touches still differ from git
if "still differ from git" not in o:
    miss("withdrew a task whose files are not restored: " + o)
git("checkout", "--", "w/a.txt")
ok("tick", "8.53", "--commit", "abc1234")
o = out("withdraw", "8.53")
if "is committed (abc1234)" not in o:
    miss("withdrew committed work: " + o)
o = out("withdraw", "8.99")
if "is in no plan" not in o:
    miss("withdrew a task in no plan: " + o)
o = out("withdraw", "1.1")                            # a task still done in the ledger of the first part, but let a non-done one in
task("8.55", ["unit"], area="w")
o = out("withdraw", "8.55")
if "is open, not done" not in o:
    miss("withdrew an open task: " + o)
rc, o = t("withdraw", "8.51", "8.52", "8.54")
if rc != 0 or "withdrawn: 8.51, 8.52, 8.54" not in o or "3 case(s) removed" not in o:
    miss("withdraw: %d %s" % (rc, o))
for want in ("doc: d1.md  [8.51, 8.52]  relabel Summary and Decisions", "doc: d2.md  [8.54]  also covers 8.60"):
    if want not in o:
        miss("withdraw does not list [%s]: %s" % (want, o))
p8 = store.path_of("plan", "w")
if not grep(r'"id":"8\.51".*"status":"void"', read(p8)) or '"status":"done"' not in read(p8):
    miss("the done record must stay in the file as history, the void one after it")
if "is void" not in out("gate", "8.51"):
    miss("gate of a withdrawn task: " + out("gate", "8.51"))
if "no cases" not in out("coverage", "8.51"):
    miss("a withdrawn task still has cases: " + out("coverage", "8.51"))
if "8.51" in clio("q", "plan")[1] or "void" not in clio("q", "plan", "--all", "--id", "8.51")[1]:
    miss("q plan shows a withdrawn task as open")
rc, o = add_records("plan", "w", {"type": "task", "id": "8.53", "task": "edited"})
if rc == 0:
    miss("clio add edited a done task")
if len(lines(read(RUNS))) < 10:
    miss("withdraw touched runs.jsonl")

done()
