#!/usr/bin/env bash
# selftest-batch.sh — Batch: lines — one runner start for many cases, results read from the JUnit XML it leaves,
# fall-backs and the notes that explain them, and red run through a batch.
. "$(dirname "$0")/selftest-common.sh"

printf "$PLAN_HEAD" > .claude/clio/docs/plans/p.md

# batch: cases whose command is a `Batch:` template run in ONE runner start; results come from the
# JUnit XML it writes. fakeunit.sh stands in for mvn/jest/pytest: `fail*` tests fail, `rep*` report
# three repetitions, `gone*` are left out of the report, and every start is counted.
mkdir -p .claude/rules; echo 'reports/' >> .gitignore
cat > fakeunit.sh <<'SH'
echo x >> starts.log
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
    *)     printf '<testcase name="%s" classname="pkg.%s" time="0.1"/>\n' "$m" "$c" >> $out ;;
  esac
done
echo '</testsuite>' >> $out
SH
echo 'starts.log' >> .gitignore
printf -- '- Batch: `bash fakeunit.sh {tests}` · join: `,` · report: `reports/TEST-*.xml`\n' > .claude/rules/fake.md
printf '| 7.1 | batch | 1 | unit, concurrency | – | – | [ ] |\n' >> .claude/clio/docs/plans/p.md
T3=.claude/clio/docs/tests/r.md
printf '| Case | Task | Level | Covers | Behaviour | Expected | Command | Repeat |\n|---|---|---|---|---|---|---|---|\n' > $T3
echo '| 7.1-u1 | 7.1 | unit | unit.1 | a | a | `bash fakeunit.sh K#okOne` | 1 |' >> $T3
echo '| 7.1-u2 | 7.1 | unit | unit.1 | b | b | `bash fakeunit.sh K#okTwo` | 1 |' >> $T3
echo '| 7.1-u3 | 7.1 | unit | unit.1 | c | c | `bash fakeunit.sh K#failThree` | 1 |' >> $T3
echo '| 7.1-c1 | 7.1 | concurrency | concurrency.1 | d | d | `bash fakeunit.sh K#repFour` | 3 |' >> $T3
: > starts.log
out=$("$S" run-task 7.1)
[ "$(wc -l < starts.log)" -eq 1 ] || { echo "batch started the runner $(wc -l < starts.log) times, not once"; bad=1; }
grep -q '^pass: 7.1-u1 (unit) 1/1 — batch' <<<"$out" || { echo "batch pass not read from the report: $out"; bad=1; }
grep -q '^fail: 7.1-u3 (unit) 0/1 — batch' <<<"$out" || { echo "batch failure not read from the report: $out"; bad=1; }
grep -q '^pass: 7.1-c1 (concurrency) 3/3 — batch' <<<"$out" || { echo "repetitions not counted: $out"; bad=1; }
grep -q 'task 7.1: 3/4 cases passed' <<<"$out" || { echo "task summary: $out"; bad=1; }
jq -e 'select(.case=="7.1-u1") | .cmd=="bash fakeunit.sh K#okOne" and (.batch|test("K#okOne,K#okTwo"))' .claude/clio/database/runs.jsonl >/dev/null \
  || { echo "batch record lacks the case's own cmd or the batch cmd"; bad=1; }
# a case the report leaves out fails; one reported fewer times than its Repeat runs on its own
echo '| 7.1-u4 | 7.1 | unit | unit.1 | e | e | `bash fakeunit.sh K#goneFive` | 1 |' >> $T3
sed -i 's/K#repFour` | 3 |/K#repFour` | 5 |/' $T3
out=$("$S" run-task 7.1)
grep -q '^fail: 7.1-u4 (unit) 0/0 — batch — not in the report' <<<"$out" || { echo "missing testcase not failed: $out"; bad=1; }
grep -q "7.1-c1's report shows fewer repetitions than its Repeat" <<<"$out" || { echo "short repeat did not fall back: $out"; bad=1; }
# a command that is not the template, word for word, is never merged into the batch
echo '| 7.1-u5 | 7.1 | unit | unit.1 | f | f | `bash fakeunit.sh K#okSix --verbose` | 1 |' >> $T3
: > starts.log; "$S" run-task 7.1 >/dev/null
[ "$(wc -l < starts.log)" -ge 3 ] || { echo "a non-template command was merged into the batch"; bad=1; }

# #6 a full classname picks one package; a short one covers every package's class of that name
printf '| 7.2 | pkgs | 1 | unit | – | – | [ ] |\n' >> .claude/clio/docs/plans/p.md
echo '| 7.2-u1 | 7.2 | unit | unit.1 | a | a | `bash fakeunit.sh pkg.a.K#dupOne` | 1 |' >> $T3
echo '| 7.2-u2 | 7.2 | unit | unit.1 | b | b | `bash fakeunit.sh K#dupTwo` | 1 |' >> $T3
out=$("$S" run-task 7.2)
grep -q '^pass: 7.2-u1 (unit) 1/1 — batch' <<<"$out" || { echo "full classname matched another package: $out"; bad=1; }
grep -q '^fail: 7.2-u2 (unit) 0/1 — batch' <<<"$out" || { echo "short classname missed a failing package: $out"; bad=1; }

# #9 parameter sets are not repetitions: Repeat 1 passes, Repeat 3 falls back to its own command
printf '| 7.3 | params | 1 | unit, concurrency | – | – | [ ] |\n' >> .claude/clio/docs/plans/p.md
echo '| 7.3-u1 | 7.3 | unit | unit.1 | a | a | `bash fakeunit.sh K#parOne` | 1 |' >> $T3
echo '| 7.3-c1 | 7.3 | concurrency | concurrency.1 | b | b | `bash fakeunit.sh K#parTwo` | 3 |' >> $T3
out=$("$S" run-task 7.3)
grep -q '^pass: 7.3-u1 (unit) 1/1 — batch' <<<"$out" || { echo "parameterised Repeat 1: $out"; bad=1; }
grep -q "7.3-c1's report shows fewer repetitions" <<<"$out" || { echo "parameter sets counted as repeats: $out"; bad=1; }

# #7 the batch is capped too, also where only gtimeout exists (macOS + coreutils)
if command -v timeout >/dev/null; then
  echo 'fakebin/' >> .gitignore; fb=$d/fakebin; mkdir -p "$fb"; for d0 in ${PATH//:/ }; do for f in "$d0"/*; do n=${f##*/}
    [ "$n" = timeout ] || [ -e "$fb/$n" ] || ln -s "$f" "$fb/$n" 2>/dev/null; done; done
  # a wrapper, not a symlink: a multicall coreutils (uutils) refuses to run under another name
  printf '#!/bin/sh\nexec %s "$@"\n' "$(command -v timeout)" > "$fb/gtimeout"; chmod +x "$fb/gtimeout"
  printf '| 7.4 | hang | 1 | unit | – | – | [ ] |\n' >> .claude/clio/docs/plans/p.md
  echo '| 7.4-u1 | 7.4 | unit | unit.1 | a | a | `bash fakeunit.sh K#hangOne` | 1 |' >> $T3
  s0=$(date +%s); out=$(PATH=$fb CLIO_TIMEOUT=2 "$S" run-task 7.4); s1=$(date +%s)
  [ $((s1-s0)) -lt 20 ] || { echo "batch not capped with only gtimeout on PATH ($((s1-s0)) s)"; bad=1; }
  grep -q 'timed out after 2s (whole batch)' <<<"$out" || { echo "batch timeout not reported: $out"; bad=1; }
fi


# two or more cases that end up running alone are named, with the template their own commands fit —
# the `-q` in a template but not in the rows is the usual cause and nothing else shows it
printf '| 7.6 | mismatch | 1 | unit | – | – | [ ] |\n' >> .claude/clio/docs/plans/p.md
echo '| 7.6-u1 | 7.6 | unit | unit.1 | a | a | `bash fakeunit.sh -q K#okA` | 1 |' >> $T3
echo '| 7.6-u2 | 7.6 | unit | unit.1 | b | b | `bash fakeunit.sh -q K#okB` | 1 |' >> $T3
out=$("$S" run-task 7.6)
grep -q 'note: 2 cases run one runner start each — their commands match no `Batch:` template' <<<"$out" || { echo "mismatch not reported: $out"; bad=1; }
grep -q 'their own commands fit: Batch: `bash fakeunit.sh -q {tests}`' <<<"$out" || { echo "no template guessed: $out"; bad=1; }
mv .claude/rules/fake.md .claude/rules/fake.md.off
out=$("$S" run-task 7.6)
grep -q 'no `Batch:` line in .claude/rules' <<<"$out" || { echo "missing Batch line not reported: $out"; bad=1; }
mv .claude/rules/fake.md.off .claude/rules/fake.md
"$S" run-task 7.2 | grep -q '^note: .*runner start each' && { echo "a batched task was reported as unbatched"; bad=1; }

# a `red` run is not a run of today's code: running red AFTER a pass must not turn the gate into
# "last run failed" — only the order (red, then run-task) decides whether red counts
git add fakeunit.sh .gitignore; echo old > chk77.txt; git add chk77.txt; git commit -qm "chk77 before the change"
echo new > chk77.txt
printf '| 7.7 | red after pass | 1 | critical · unit | – | – | [ ] |\n' >> .claude/clio/docs/plans/p.md
echo '| 7.7-u1 | 7.7 | unit | unit.1 | a | a | `bash fakeunit.sh K#chkSeven` | 1 |' >> $T3
"$S" approve 7.7 >/dev/null; ok "$S" run-task 7.7
out=$("$S" red 7.7); grep -q '^red: 7.7-u1 failed on' <<<"$out" || { echo "batch red not seen: $out"; bad=1; }
"$S" gate 7.7 | grep -q 'last run failed' && { echo "a red run was read as today's last run"; bad=1; }
jq -e 'select(.case=="7.7-u1" and .red_base) | .cmd=="bash fakeunit.sh K#chkSeven" and .level=="unit"' .claude/clio/database/runs.jsonl >/dev/null \
  || { echo "a batch red run recorded no command (rows read inside the worktree)"; bad=1; }
ok "$S" run-task 7.7; ok "$S" gate 7.7                    # red, then a pass on today's code: counts
"$S" coverage 7.7 | grep -q $'7.7-u1\tunit\tpass' || { echo "coverage read the red run as last: $("$S" coverage 7.7)"; bad=1; }

# a red whose runner never ran the test (build error at the base: not in the report) is not a red
printf '| 7.8 | build broke | 1 | critical · unit | – | – | [ ] |\n' >> .claude/clio/docs/plans/p.md
echo '| 7.8-u1 | 7.8 | unit | unit.1 | a | a | `bash fakeunit.sh K#chkEight` | 1 |' >> $T3
echo x > nobuild; git add nobuild; git commit -qm "base does not build"; rm nobuild
"$S" approve 7.8 >/dev/null
out=$("$S" red 7.8); grep -q 'NOT RED: 7.8-u1 did not run' <<<"$out" || { echo "build-error red accepted: $out"; bad=1; }
ok "$S" run-task 7.8; has 7.8 'never seen red on a critical task'
"$S" run-task 7.8 | grep -q '^took [0-9]* s$' || { echo "run-task does not say how long it took"; bad=1; }

[ $bad -eq 0 ] && echo OK
exit $bad
