#!/usr/bin/env bash
# selftest-gate.sh — run, approve and gate: evidence, flaky, regression, mutation, malformed rows, Not applicable,
# Covers, timeouts, batch approve. jq + git only.
. "$(dirname "$0")/selftest-common.sh"

printf '| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n| 1.1 | a | 1 | unit | – | – | [ ] |\n| 1.2 | b | 1 | critical · unit | – | – | [ ] |\n| 1.3 | c | 1 | regression | – | – | [ ] |\n| 1.4 | d | 1 | concurrency | – | – | [ ] |\n' > .claude/clio/docs/plans/p.md
T=.claude/clio/docs/tests/p.md
printf '| Case | Task | Level | Behaviour | Expected (source) | Command | Repeat |\n|---|---|---|---|---|---|---|\n' > $T
echo '| 1.1-u1 | 1.1 | unit | ok | exit 0 | `true` | 3 |' >> $T
echo '| 1.2-u1 | 1.2 | unit | ok | exit 0 | `true` | 1 |' >> $T
echo '| 1.3-r1 | 1.3 | regression | bug | exit 0 | `test -f fixed` | 1 |' >> $T
echo '| 1.4-c1 | 1.4 | concurrency | race | exit 0 | `true` | 5 |' >> $T

ko "$S" gate 1.1                  # never run
ok "$S" run 1.1-u1
okg 1.1
echo y >> app.txt; ko "$S" gate 1.1   # code changed after the pass
ok "$S" run 1.1-u1; okg 1.1
ok "$S" run 1.2-u1; ko "$S" gate 1.2  # critical: a case never seen red
ko "$S" run 1.3-r1                   # red: bug not fixed yet
touch fixed; ok "$S" run 1.3-r1; okg 1.3   # then green
ok "$S" run 1.4-c1; ko "$S" gate 1.4  # concurrency repeat 5 < floor
ko "$S" run nope                     # unknown case
ko "$S" run-task 7.7                 # a task with no cases
[ "$(wc -l < .claude/clio/database/runs.jsonl)" -ge 6 ] || { echo "runs.jsonl not appended"; bad=1; }

# committing the same code keeps the evidence; an artifact the test writes does not invalidate it
ok "$S" run 1.1-u1; okg 1.1   # 'fixed' above changed the code since the last pass
git add -A -- . ':(exclude).claude'; git commit -qm work; okg 1.1
echo '| 1.1-u2 | 1.1 | unit | writes coverage | exit 0 | `echo c > cover.out` | 1 |' >> $T
ok "$S" run 1.1-u2; okg 1.1
echo '| 9.9-u1 | 9.9 | unit | orphan | exit 0 | `true` | 1 |' >> $T
ok "$S" run 9.9-u1; ko "$S" gate 9.9      # task in no plan: no Levels to hold it to

# a pre-4.0 plan table: never gated directly; its sub-task in the re-planned table is
printf '| # | Task | req | Test that proves it | Needs | Done |\n|---|---|---|---|---|---|\n| 5.1 | old | 1 | `go test ./x` | – | [x] 2026-01-01 |\n\n## Re-planned\n\n| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n| 5.1.1 | bring 5.1 under test | 1 | unit | 5.1 | – | [ ] |\n' > .claude/clio/docs/plans/old.md
echo '| 5.1-u1 | 5.1 | unit | old | exit 0 | `true` | 1 |' >> $T
echo '| 5.1.1-u1 | 5.1.1 | unit | new | exit 0 | `true` | 1 |' >> $T
ok "$S" run 5.1-u1; out=$("$S" gate 5.1); grep -q 'pre-4.0 row' <<<"$out" || { echo "old row not refused: $out"; bad=1; }
ok "$S" run 5.1.1-u1; okg 5.1.1

# coverage: what a re-plan reads — level and last result per case, "no cases" for a pre-4.0 row
[ "$("$S" coverage 1.3 | grep -c .)" -ge 1 ] || { echo "coverage empty"; bad=1; }
"$S" coverage 1.3 | grep -q "1.3-r1	regression	pass" || { echo "coverage lost last result: $("$S" coverage 1.3)"; bad=1; }
[ "$("$S" coverage 7.7)" = "no cases" ] || { echo "coverage of an uncovered task"; bad=1; }

# critical: every non-mutation case must have been seen red, but critical alone never asks for mutation
out=$("$S" gate 1.2); grep -q 'never seen red on a critical task' <<<"$out" || { echo "critical never-red not refused: $out"; bad=1; }
grep -q "level 'mutation'" <<<"$out" && { echo "critical demanded mutation: $out"; bad=1; }
# a money task names `mutation` itself; `Mutation: none` in infra.md waives it
printf '| 1.6 | money | 1 | critical · unit, mutation | – | – | [ ] |\n' >> .claude/clio/docs/plans/p.md
echo '| 1.6-u1 | 1.6 | unit | x | x | `true` | 1 |' >> $T
"$S" run 1.6-u1 >/dev/null; has 1.6 "plan requires level 'mutation'"
printf '# Plan — infra\nMutation: none (ADR 1790000000_no-mutation)\n' > .claude/clio/docs/plans/infra.md
has 1.6 "says \`Mutation: none\`"   # a row naming mutation against the ADR is refused, not waived
echo '| 1.2-u2 | 1.2 | unit | critical red then green | exit 0 | `test -f crit-ok` | 1 |' >> $T
ko "$S" run 1.2-u2; touch crit-ok; ok "$S" run 1.2-u2
"$S" gate 1.2 | grep -q '1.2-u2: never seen red' && { echo "a case seen red still flagged"; bad=1; }

# mutation: the command's own exit code is not trusted alone — its text must show a real threshold
printf '# Plan — infra\nMutation: stryker (ADR 1790000000_stryker)\n' > .claude/clio/docs/plans/infra.md
printf '| 1.7 | zeroed | 1 | mutation | – | – | [ ] |\n| 1.8 | honest | 1 | mutation | – | – | [ ] |\n' >> .claude/clio/docs/plans/p.md
echo '| 1.7-m1 | 1.7 | mutation | x | x | `true --thresholds.break 0` | 1 |' >> $T
echo '| 1.8-m1 | 1.8 | mutation | x | x | `true --thresholds.break 85` | 1 |' >> $T
"$S" approve 1.7 >/dev/null; "$S" run 1.7-m1 >/dev/null; has 1.7 'no threshold >= 80%'   # 0 does not clear the default
"$S" approve 1.8 >/dev/null; "$S" run 1.8-m1 >/dev/null; okg 1.8                          # 85 clears it
# a project threshold above default (90%) holds even a normally-fine 85 to the higher bar
printf '# Plan — infra\nMutation: stryker (ADR 1790000000_stryker, 90%%)\n' > .claude/clio/docs/plans/infra.md
has 1.8 'no threshold >= 90%'
rm .claude/clio/docs/plans/infra.md

# the approved table is the definition of done: deleting a failing case or lowering Repeat voids it
"$S" run 1.1-u1 >/dev/null; "$S" run 1.1-u2 >/dev/null; has 1.1 'OK: task 1.1'
sed -i 's/| `true` | 3 |/| `true` | 1 |/' $T; has 1.1 'changed since it was approved'
"$S" approve 1.1 >/dev/null; has 1.1 'OK: task 1.1'
printf '| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n| 2.1 | never approved | 1 | unit | – | – | [ ] |\n' > .claude/clio/docs/plans/q.md
echo '| 2.1-u1 | 2.1 | unit | x | x | `true` | 1 |' >> $T
"$S" run 2.1-u1 >/dev/null; has 2.1 'never approved'

# flaky: red then green on the same code is not a pass; nor is red then green on the same code later
printf '| 2.2 | flaky | 1 | unit | – | – | [ ] |\n| 2.3 | reg | 1 | regression | – | – | [ ] |\n| 2.4 | sup | 1 | unit | – | – | superseded 2026-01-01 → 2.4.1 |\n| 2.5 | bad level | 1 | Concurrency | – | – | [ ] |\n' >> .claude/clio/docs/plans/q.md
echo '| 2.2-u1 | 2.2 | unit | x | x | `bash flaky.sh` | 1 |' >> $T
printf 'test -f .f1 || { touch .f1; exit 1; }\n' > flaky.sh; git add flaky.sh; git commit -qm f; echo .f1 > .gitignore
"$S" approve 2.2 >/dev/null
"$S" run 2.2-u1 >/dev/null; ok "$S" run 2.2-u1; ok "$S" gate 2.2   # fail before the first pass: forgiven
rm .f1; "$S" run 2.2-u1 >/dev/null; ok "$S" run 2.2-u1; has 2.2 'flaky'   # fail after a pass, same code

# regression red must be the same command, on other code: swapping `false` → `true` proves nothing
echo '| 2.3-r1 | 2.3 | regression | x | x | `false` | 1 |' >> $T
"$S" run 2.3-r1 >/dev/null; sed -i 's/| 2.3-r1 | 2.3 | regression | x | x | `false` | 1 |/| 2.3-r1 | 2.3 | regression | x | x | `true` | 1 |/' $T
"$S" approve 2.3 >/dev/null; ok "$S" run 2.3-r1; has 2.3 'regression case never failed'

# malformed rows fail loudly: superseded task, level outside the catalog, `|` in a command, bad Repeat
echo '| 2.4-u1 | 2.4 | unit | x | x | `true` | 1 |' >> $T
"$S" approve 2.4 >/dev/null; "$S" run 2.4-u1 >/dev/null; has 2.4 'superseded'
echo '| 2.5-c1 | 2.5 | Concurrency | x | x | `true` | 1 |' >> $T
ko "$S" run 2.5-c1; "$S" approve 2.5 >/dev/null; has 2.5 "plan level 'Concurrency'"
echo '| 2.2-u2 | 2.2 | unit | pipe | x | `true || false` | 3 |' >> $T
out=$("$S" run 2.2-u2); grep -q 'splits into' <<<"$out" || { echo "pipe row ran: $out"; bad=1; }
echo '| 2.2-u3 | 2.2 | unit | rep | x | `true` | many |' >> $T
out=$("$S" run 2.2-u3); grep -q 'not a whole number' <<<"$out" || { echo "bad Repeat ran: $out"; bad=1; }

# a table inside <!-- --> is not read: its task is in no plan, its cases in no tests file
printf '<!--\n| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n| 3.1 | hidden | 1 | unit | – | – | [ ] |\n-->\n' > .claude/clio/docs/plans/hid.md
printf '<!-- | 3.1-u1 | 3.1 | unit | x | x | `true` | 1 | -->\n' >> $T
out=$("$S" run 3.1-u1); grep -q 'in no' <<<"$out" || { echo "commented case ran: $out"; bad=1; }
echo '| 3.1-u2 | 3.1 | unit | x | x | `true` | 1 |' >> $T
"$S" approve 3.1 >/dev/null; "$S" run 3.1-u2 >/dev/null; has 3.1 'in no .claude/clio/docs/plans'

# one case, one command: a second level riding on the same command is refused
printf '| 3.2 | dup | 1 | api, security | – | – | [ ] |\n' >> .claude/clio/docs/plans/q.md
echo '| 3.2-a1 | 3.2 | api | x | x | `test -d .git` | 1 |' >> $T
echo '| 3.2-s1 | 3.2 | security | x | x | `test -d .git` | 1 |' >> $T
"$S" approve 3.2 >/dev/null; "$S" run 3.2-a1 >/dev/null; "$S" run 3.2-s1 >/dev/null; has 3.2 'run the same command'

# .claude never counts, even staged and then edited again (git rm --cached refuses that without -f)
echo 0 > .claude/note.txt; git add .claude/note.txt; echo 1 >> .claude/note.txt
f1=$("$S" fp); git add .claude/note.txt; echo 2 >> .claude/note.txt; f2=$("$S" fp)
[ "$f1" = "$f2" ] || { echo "a staged-and-edited file under .claude moved the fingerprint"; bad=1; }
git rm -q -f --cached .claude/note.txt; rm .claude/note.txt

# a directory a run created is not a hiding place: code written into it later changes the fingerprint
echo '| 3.3-u1 | 3.3 | unit | gen | x | `mkdir -p gen && echo a > gen/out.txt` | 1 |' >> $T
"$S" run 3.3-u1 >/dev/null; f1=$("$S" fp); echo 'code' > gen/logic.go; f2=$("$S" fp)
[ "$f1" != "$f2" ] || { echo "source added to an artifact directory is invisible to fp"; bad=1; }
echo y > gen/out.txt; [ "$f2" = "$("$S" fp)" ] || { echo "the artifact file itself changed fp"; bad=1; }
rm -rf gen

# regression that never failed is rejected
echo '| 1.3-r2 | 1.3 | regression | bug2 | exit 0 | `true` | 1 |' >> $T
"$S" run 1.3-r2 >/dev/null; ko "$S" gate 1.3

# Covers: LEVELS.md gives `contract` two ids. A new-format table (with the Covers column) is held to
# both — one covered by a case, no case and no excuse for the other — the gate names the missing one.
printf '| 4.1 | sync | 1 | contract | – | – | [ ] |\n| 4.2 | sync2 | 1 | contract | – | – | [ ] |\n' >> .claude/clio/docs/plans/q.md
printf '\n| Case | Task | Level | Covers | Behaviour | Expected (source) | Command | Repeat |\n|---|---|---|---|---|---|---|---|\n' >> $T
echo '| 4.1-c1 | 4.1 | contract | contract.1 | consumer | x | `true c1` | 1 |' >> $T
"$S" approve 4.1 >/dev/null; "$S" run 4.1-c1 >/dev/null
has 4.1 'no case covering contract.2'
echo '| 4.1-c2 | 4.1 | contract | contract.2 | provider | x | `true c2` | 1 |' >> $T
"$S" approve 4.1 >/dev/null; "$S" run 4.1-c2 >/dev/null; okg 4.1   # both ids now covered

# a `Not applicable` line excuses an id without a case for it
echo '| 4.2-c1 | 4.2 | contract | contract.1 | consumer | x | `true c3` | 1 |' >> $T
printf '\nNot applicable:\n- 4.2 · contract.2 — the provider will not run a contract test\n' >> $T
"$S" approve 4.2 >/dev/null; "$S" run 4.2-c1 >/dev/null; okg 4.2

# pre-4.1 rows (no Covers column) are grandfathered: task 1.2's `unit` case above never names
# `unit.1`, and every case run earlier in this file passed gate all along — nothing new to flag here.
out=$("$S" gate 1.2)
grep -q 'no case covering' <<<"$out" && { echo "a pre-4.1 row was held to a Covers id it never had a column for: $out"; bad=1; }

# coverage() reads the shifted Covers-column layout too, not just gate()
"$S" coverage 4.1 | grep -q '4.1-c1	contract	pass' || { echo "coverage lost a Covers-column case: $("$S" coverage 4.1)"; bad=1; }

# a malformed row (a `|` inside its command) must not leak the PRECEDING row's Covers value into the
# next task's coverage — even across a task boundary, since cases() sees every file's rows in order
# before gate() ever filters by task. Before the fix this let an unrelated bullet look covered.
printf '| 4.4 | leakA | 1 | security | – | – | [ ] |\n| 4.5 | leakB | 1 | security | – | – | [ ] |\n' >> .claude/clio/docs/plans/q.md
echo '| 4.4-s1 | 4.4 | security | security.1 | authn | x | `true c7` | 1 |' >> $T
echo '| 4.5-s1 | 4.5 | security | security.2 | x | x | `true || false` | 1 |' >> $T   # malformed, right after 4.4-s1
echo '| 4.5-s2 | 4.5 | security | security.6 | biz | x | `true c8` | 1 |' >> $T          # legit: satisfies "a case exists"
"$S" approve 4.4 >/dev/null; "$S" run 4.4-s1 >/dev/null
"$S" approve 4.5 >/dev/null; "$S" run 4.5-s1 >/dev/null; "$S" run 4.5-s2 >/dev/null
out=$("$S" gate 4.5)
grep -q 'no case covering security.1' <<<"$out" || { echo "a malformed row leaked another task's Covers value: $out"; bad=1; }

# run-task: every case of a task in one call — what /clio:test hands the user — then the gate holds
out=$("$S" run-task 1.1); grep -q 'task 1.1: 2/2 cases passed' <<<"$out" || { echo "run-task 1.1: $out"; bad=1; }
okg 1.1
echo '| 8.1-u1 | 8.1 | unit | red | exit 0 | `false` | 1 |' >> $T
echo '| 8.1-u2 | 8.1 | unit | green | exit 0 | `true` | 1 |' >> $T
out=$("$S" run-task 8.1) && { echo "run-task with a red case exited 0"; bad=1; }
grep -q 'task 8.1: 1/2 cases passed' <<<"$out" || { echo "run-task stopped at the first red: $out"; bad=1; }

# 4.1.2 — a `Not applicable` line added after approve voids the approval, like an edited case
printf '| 9.1 | na | 1 | unit | – | – | [ ] |\n| 9.2 | mut | 1 | mutation | – | – | [ ] |\n| 9.3 | fake red | 1 | critical · unit | – | – | [ ] |\n| 9.4 | real red | 1 | critical · unit | – | – | [ ] |\n| 9.5 | hang | 1 | unit | – | – | [ ] |\n' >> .claude/clio/docs/plans/p.md
T2=.claude/clio/docs/tests/q.md
printf '| Case | Task | Level | Covers | Behaviour | Expected | Command | Repeat |\n|---|---|---|---|---|---|---|---|\n' > $T2
echo '| 9.1-u1 | 9.1 | unit | unit.1 | x | x | `true` | 1 |' >> $T2
ok "$S" run 9.1-u1; okg 9.1
printf '\nNot applicable:\n- 9.1 · unit.1 — slipped in after the yes\n' >> $T2
has 9.1 'changed since it was approved'
okg 9.1                                  # the user approves the excuse too: holds again

# mutation: only a named threshold flag counts, every one of them, and a `#` is refused
printf '# Plan — infra\nMutation: stryker (ADR 1790000000_stryker)\n' > .claude/clio/docs/plans/infra.md
mut(){ sed -i '/^| 9.2-m1 /d' $T2; echo "| 9.2-m1 | 9.2 | mutation | – | x | x | \`$1\` | 1 |" >> $T2
       "$S" approve 9.2 >/dev/null; "$S" run 9.2-m1 >/dev/null; }
mut 'true --thresholds.break 0 # 80';            has 9.2 'contains `#`'
mut 'true --thresholds.break 0 --min-score 90';  has 9.2 'no threshold >= 80%'
mut 'true --port 8080 --thresholds.break 0';     has 9.2 'no threshold >= 80%'
mut 'true -DmutationThreshold=85';               ok "$S" gate 9.2

# a hung case fails at CLIO_TIMEOUT instead of blocking the run
if command -v timeout >/dev/null; then
  echo '| 9.5-u1 | 9.5 | unit | unit.1 | x | x | `sleep 5` | 1 |' >> $T2
  out=$(CLIO_TIMEOUT=1 "$S" run 9.5-u1) && { echo "hung case passed"; bad=1; }
  grep -q 'timed out after 1s' <<<"$out" || { echo "timeout not reported: $out"; bad=1; }
fi


# batch: one approve and one run-task over several tasks; a bad id in the batch approves/runs nothing
printf '| 9.6 | b1 | 1 | unit | – | – | [ ] |\n| 9.7 | b2 | 1 | unit | – | – | [ ] |\n' >> .claude/clio/docs/plans/p.md
echo '| 9.6-u1 | 9.6 | unit | unit.1 | x | x | `true` | 1 |' >> $T2
echo '| 9.7-u1 | 9.7 | unit | unit.1 | x | x | `test -d .` | 1 |' >> $T2
n0=$(grep -c . .claude/clio/database/runs.jsonl)
ko "$S" approve 9.6 9.9x; ko "$S" run-task 9.6 9.9x
[ "$(grep -c . .claude/clio/database/runs.jsonl)" -eq "$n0" ] || { echo "a batch with a bad id still wrote records"; bad=1; }
out=$("$S" run-task 9.6 9.7); grep -q 'all: 2/2 cases passed across 2 tasks' <<<"$out" || { echo "batch run-task: $out"; bad=1; }
ok "$S" approve 9.6 9.7; ok "$S" gate 9.6; ok "$S" gate 9.7
sed -i 's#| `test -d .` |#| `test -d ./` |#' $T2          # edit 9.7's table: only its approval is void
ok "$S" gate 9.6; has 9.7 'changed since it was approved'

[ $bad -eq 0 ] && echo OK
exit $bad
