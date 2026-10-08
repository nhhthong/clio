#!/usr/bin/env python3
"""selftest_batch.py — Batch: lines — one runner start for many cases, results read from the JUnit XML it leaves,
fall-backs and the notes that explain them, and red run through a batch."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from selftest_common import (  # noqa: E402
    RUNS, case, done, git, grep, has, lines, miss, ok, out, read, t, task, write)


# batch: cases whose command is a `Batch:` template run in ONE runner start; results come from the
# JUnit XML it writes. fakeunit.sh stands in for mvn/jest/pytest: `fail*` tests fail, `rep*` report
# three repetitions, `gone*` are left out of the report, and every start is counted.
os.makedirs(".claude/rules")
write(".gitignore", "reports/\n", "a")
write("fakeunit.sh", r"""echo x >> starts.log
mkdir -p reports; out=reports/TEST-fake.xml; echo '<testsuite>' > $out
[ -e nobuild ] && { echo '</testsuite>' >> $out; echo "BUILD FAILURE" >&2; exit 2; }   # compile error: no testcase
IFS=, read -ra ts <<<"$1"
for t in "${ts[@]}"; do c=${t%%#*}; m=${t#*#}; [[ $c == *.* ]] && c=${c##*.}
  case $m in
    gone*) ;;
    chk*)  if grep -q new chk77.txt 2>/dev/null; then printf '<testcase name="%s" classname="pkg.%s"/>\n' "$m" "$c" >> $out
           else printf '<testcase name="%s" classname="pkg.%s">\n<failure message="old"/>\n</testcase>\n' "$m" "$c" >> $out; fi ;;
    hang*) sleep 30 ;;
    dup*)  printf '<testcase name="%s" classname="pkg.a.%s"/>\n<testcase name="%s" classname="pkg.b.%s">\n<failure/>\n</testcase>\n' "$m" "$c" "$m" "$c" >> $out ;;
    par*)  for k in 1 2 3; do printf '<testcase name="%s(String)[%d]" classname="pkg.%s"/>\n' "$m" $k "$c" >> $out; done ;;
    fail*) printf '<testcase name="%s" classname="pkg.%s">\n<failure message="x"/>\n</testcase>\n' "$m" "$c" >> $out ;;
    rep*)  for k in 1 2 3; do printf '<testcase name="%s()[%d]" classname="pkg.%s"/>\n' "$m" $k "$c" >> $out; done ;;
    maybe*) [ -e reports/hide ] || printf '<testcase name="%s" classname="pkg.%s"/>\n' "$m" "$c" >> $out ;;
    Multi*) for k in a b c; do printf '<testcase name="%s" classname="pkg.%s"/>\n' "$k" "$c" >> $out; done ;;
    *)     printf '<testcase name="%s" classname="pkg.%s" time="0.1"/>\n' "$m" "$c" >> $out ;;
  esac
done
echo '</testsuite>' >> $out
""")
write(".gitignore", "starts.log\n", "a")
write(".claude/rules/fake.md", "- Batch: `bash fakeunit.sh {tests}` · join: `,` · report: `reports/TEST-*.xml`\n")
task('7.1', ['unit', 'concurrency'])
case('7.1-u1', '7.1', 'unit', 'bash fakeunit.sh K#okOne', covers=['unit.1'])
case('7.1-u2', '7.1', 'unit', 'bash fakeunit.sh K#okTwo', covers=['unit.1'])
case('7.1-u3', '7.1', 'unit', 'bash fakeunit.sh K#failThree', covers=['unit.1'])
case('7.1-c1', '7.1', 'concurrency', 'bash fakeunit.sh K#repFour', 3, covers=['concurrency.1'])


def starts():
    return len(lines(read("starts.log")))


def records():
    return [json.loads(l) for l in lines(read(RUNS))]


write("starts.log", "")
o = out("run-task", "7.1")
if starts() != 1:
    miss("batch started the runner %d times, not once" % starts())
if not grep(r"^pass: 7\.1-u1 \(unit\) 1/1 — batch", o):
    miss("batch pass not read from the report: " + o)
if not grep(r"^fail: 7\.1-u3 \(unit\) 0/1 — batch", o):
    miss("batch failure not read from the report: " + o)
if not grep(r"^pass: 7\.1-c1 \(concurrency\) 3/3 — batch", o):
    miss("repetitions not counted: " + o)
if "task 7.1: 3/4 cases passed" not in o:
    miss("task summary: " + o)
if not any(r.get("case") == "7.1-u1" and r.get("cmd") == "bash fakeunit.sh K#okOne"
           and "K#okOne,K#okTwo" in (r.get("batch") or "") for r in records()):
    miss("batch record lacks the case's own cmd or the batch cmd")
# a case the report leaves out fails; one reported fewer times than its Repeat runs on its own
case('7.1-u4', '7.1', 'unit', 'bash fakeunit.sh K#goneFive', covers=['unit.1'])
case('7.1-c1', '7.1', 'concurrency', 'bash fakeunit.sh K#repFour', 5, covers=['concurrency.1'])
o = out("run-task", "7.1")
if not grep(r"^fail: 7\.1-u4 \(unit\) 0/0 — batch — not in the report", o):
    miss("missing testcase not failed: " + o)
if "7.1-c1's report shows fewer repetitions than its Repeat" not in o:
    miss("short repeat did not fall back: " + o)
# a command that is not the template, word for word, is never merged into the batch
case('7.1-u5', '7.1', 'unit', 'bash fakeunit.sh K#okSix --verbose', covers=['unit.1'])
write("starts.log", "")
t("run-task", "7.1")
if starts() < 3:
    miss("a non-template command was merged into the batch")

# #6 a full classname picks one package; a short one covers every package's class of that name
task('7.2', ['unit'])
case('7.2-u1', '7.2', 'unit', 'bash fakeunit.sh pkg.a.K#dupOne', covers=['unit.1'])
case('7.2-u2', '7.2', 'unit', 'bash fakeunit.sh K#dupTwo', covers=['unit.1'])
o = out("run-task", "7.2")
if not grep(r"^pass: 7\.2-u1 \(unit\) 1/1 — batch", o):
    miss("full classname matched another package: " + o)
if not grep(r"^fail: 7\.2-u2 \(unit\) 0/1 — batch", o):
    miss("short classname missed a failing package: " + o)

# #9 parameter sets are not repetitions: Repeat 1 passes, Repeat 3 falls back to its own command
task('7.3', ['unit', 'concurrency'])
case('7.3-u1', '7.3', 'unit', 'bash fakeunit.sh K#parOne', covers=['unit.1'])
case('7.3-c1', '7.3', 'concurrency', 'bash fakeunit.sh K#parTwo', 3, covers=['concurrency.1'])
o = out("run-task", "7.3")
if not grep(r"^pass: 7\.3-u1 \(unit\) 1/1 — batch", o):
    miss("parameterised Repeat 1: " + o)
if "7.3-c1's report shows fewer repetitions" not in o:
    miss("parameter sets counted as repeats: " + o)

# #7 the batch is capped too: a runner that hangs is killed at CLIO_TIMEOUT, with the whole batch named
task('7.4', ['unit'])
case('7.4-u1', '7.4', 'unit', 'bash fakeunit.sh K#hangOne', covers=['unit.1'])
s0 = time.time()
o = out("run-task", "7.4", env={"CLIO_TIMEOUT": "2"})
if time.time() - s0 >= 20:
    miss("batch not capped (%d s)" % (time.time() - s0))
if "timed out after 2s (whole batch)" not in o:
    miss("batch timeout not reported: " + o)

# two or more cases that end up running alone are named, with the template their own commands fit —
# the `-q` in a template but not in the rows is the usual cause and nothing else shows it
task('7.6', ['unit'])
case('7.6-u1', '7.6', 'unit', 'bash fakeunit.sh -q K#okA', covers=['unit.1'])
case('7.6-u2', '7.6', 'unit', 'bash fakeunit.sh -q K#okB', covers=['unit.1'])
o = out("run-task", "7.6")
if "note: 2 cases run one runner start each — their commands match no `Batch:` template" not in o:
    miss("mismatch not reported: " + o)
if "their own commands fit: Batch: `bash fakeunit.sh -q {tests}`" not in o:
    miss("no template guessed: " + o)
os.rename(".claude/rules/fake.md", ".claude/rules/fake.md.off")
o = out("run-task", "7.6")
if "no `Batch:` line in .claude/rules" not in o:
    miss("missing Batch line not reported: " + o)
os.rename(".claude/rules/fake.md.off", ".claude/rules/fake.md")
if grep("^note: .*runner start each", out("run-task", "7.2")):
    miss("a batched task was reported as unbatched")

# a `red` run is not a run of today's code: running red AFTER a pass must not turn the gate into
# "last run failed" — only the order (red, then run-task) decides whether red counts
git("add", "fakeunit.sh", ".gitignore")
write("chk77.txt", "old\n")
git("add", "chk77.txt")
git("commit", "-qm", "chk77 before the change")
write("chk77.txt", "new\n")
task('7.7', ['unit'], critical=True)
case('7.7-u1', '7.7', 'unit', 'bash fakeunit.sh K#chkSeven', covers=['unit.1'])
t("approve", "7.7")
ok("run-task", "7.7")
o = out("red", "7.7")
if not grep("^red: 7.7-u1 failed on", o):
    miss("batch red not seen: " + o)
if not grep(r"7\.7-u1 \(unit\) .* — batch — on ", o):
    miss("red did not batch (Batch: line read from the worktree?): " + o)
if "last run failed" in out("gate", "7.7"):
    miss("a red run was read as today's last run")
if not any(r.get("case") == "7.7-u1" and r.get("red_base") and r.get("cmd") == "bash fakeunit.sh K#chkSeven"
           and r.get("level") == "unit" for r in records()):
    miss("a batch red run recorded no command (rows read inside the worktree)")
ok("run-task", "7.7")
ok("gate", "7.7")                    # red, then a pass on today's code: counts
if "7.7-u1\tunit\tpass" not in out("coverage", "7.7"):
    miss("coverage read the red run as last: " + out("coverage", "7.7"))

# a red whose runner never ran the test (build error at the base: not in the report) is not a red
task('7.8', ['unit'], critical=True)
case('7.8-u1', '7.8', 'unit', 'bash fakeunit.sh K#chkEight', covers=['unit.1'])
write("nobuild", "x\n")
git("add", "nobuild")
git("commit", "-qm", "base does not build")
os.remove("nobuild")
t("approve", "7.8")
o = out("red", "7.8")
if "NOT RED: 7.8-u1 did not run" not in o:
    miss("build-error red accepted: " + o)
ok("run-task", "7.8")
has("7.8", "never seen red on a critical task")
if not grep("^took [0-9]* s$", out("run-task", "7.8")):
    miss("run-task does not say how long it took")

# a batch record of a case the report did not show (timeout, build error) is not a fail of the case:
# passing again on the same code must not read as flaky
task('7.9', ['unit'])
case('7.9-u1', '7.9', 'unit', 'bash fakeunit.sh K#maybeNine', covers=['unit.1'])
ok("run-task", "7.9")
os.makedirs("reports", exist_ok=True)
write("reports/hide", "x\n")
o = out("run-task", "7.9")
if not grep(r"^fail: 7\.9-u1 \(unit\) 0/0 — batch — not in the report", o):
    miss("hidden case not failed as not-in-report: " + o)
os.remove("reports/hide")
ok("run-task", "7.9")
t("approve", "7.9")
if "flaky" in out("gate", "7.9"):
    miss("a not-in-report batch record read as flaky: " + out("gate", "7.9"))

# a class-wide test id (no `#`) matches every method of the class: three methods are three calls,
# not three repetitions of one — Repeat 3 falls back to its own command
task('7.10', ['unit'])
case('7.10-u1', '7.10', 'unit', 'bash fakeunit.sh MultiCls', 3, covers=['unit.1'])
o = out("run-task", "7.10")
if "7.10-u1's report shows fewer repetitions" not in o:
    miss("distinct methods of one class counted as repetitions: " + o)

# a row that cannot run (bad Repeat) runs nothing and records nothing: run-task and red must not
# read an older record of the case as this call's result
task('7.11', ['unit'], critical=True)
case('7.11-u1', '7.11', 'unit', 'bash fakeunit.sh K#chkEleven', covers=['unit.1'])
if not grep("^red: 7.11-u1 failed", out("red", "7.11", "--base", "HEAD~1")):   # chk77.txt reads "old" there
    miss("7.11 setup: no red to go stale")
ok("run-task", "7.11")
case('7.11-u1', '7.11', 'unit', 'bash fakeunit.sh K#chkEleven', 'x', covers=['unit.1'])
rc, o = t("run-task", "7.11")
if rc == 0 or "1/1 cases passed" in o:
    miss("run-task reported a case that did not run as passed: %d %s" % (rc, o))
rc, o = t("red", "7.11", "--base", "HEAD~1")
if rc == 0 or grep("^red: 7.11-u1 failed", o):
    miss("red reported a case that did not run as red: %d %s" % (rc, o))

done()
