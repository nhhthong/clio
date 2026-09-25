#!/usr/bin/env bash
# selftest.sh — the smallest check that fails if clio-test.sh's gate logic breaks. jq + git only.
set -u
S=$(cd "$(dirname "$0")" && pwd)/clio-test.sh
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT; cd "$d"
git init -q; git config user.email t@t; git config user.name t
mkdir -p .claude/clio/database .claude/clio/docs/tests .claude/clio/docs/plans
echo x > app.txt; git add app.txt; git commit -qm init
bad=0
ok(){ "$@" >/dev/null 2>&1 || { echo "expected pass: $*"; bad=1; }; }
ko(){ "$@" >/dev/null 2>&1 && { echo "expected fail: $*"; bad=1; }; }
okg(){ "$S" approve "$1" >/dev/null; ok "$S" gate "$1"; }   # the user said yes to the table, then gate
has(){ out=$("$S" gate "$1"); grep -q "$2" <<<"$out" || { echo "gate $1 lacks '$2': $out"; bad=1; }; }

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

[ $bad -eq 0 ] && echo OK
exit $bad
