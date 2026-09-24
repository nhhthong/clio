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

printf '| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n| 1.1 | a | 1 | unit | – | – | [ ] |\n| 1.2 | b | 1 | critical · unit | – | – | [ ] |\n| 1.3 | c | 1 | regression | – | – | [ ] |\n| 1.4 | d | 1 | concurrency | – | – | [ ] |\n' > .claude/clio/docs/plans/p.md
T=.claude/clio/docs/tests/p.md
printf '| Case | Task | Level | Behaviour | Expected (source) | Command | Repeat |\n|---|---|---|---|---|---|---|\n' > $T
echo '| 1.1-u1 | 1.1 | unit | ok | exit 0 | `true` | 3 |' >> $T
echo '| 1.2-u1 | 1.2 | unit | ok | exit 0 | `true` | 1 |' >> $T
echo '| 1.3-r1 | 1.3 | regression | bug | exit 0 | `test -f fixed` | 1 |' >> $T
echo '| 1.4-c1 | 1.4 | concurrency | race | exit 0 | `true` | 5 |' >> $T

ko "$S" gate 1.1                  # never run
ok "$S" run 1.1-u1
ok "$S" gate 1.1
echo y >> app.txt; ko "$S" gate 1.1   # code changed after the pass
ok "$S" run 1.1-u1; ok "$S" gate 1.1
ok "$S" run 1.2-u1; ko "$S" gate 1.2  # critical without a mutation case
ko "$S" run 1.3-r1                   # red: bug not fixed yet
touch fixed; ok "$S" run 1.3-r1; ok "$S" gate 1.3   # then green
ok "$S" run 1.4-c1; ko "$S" gate 1.4  # concurrency repeat 5 < floor
ko "$S" run nope                     # unknown case
[ "$(wc -l < .claude/clio/database/runs.jsonl)" -ge 6 ] || { echo "runs.jsonl not appended"; bad=1; }

# committing the same code keeps the evidence; an artifact the test writes does not invalidate it
ok "$S" run 1.1-u1; ok "$S" gate 1.1   # 'fixed' above changed the code since the last pass
git add -A -- . ':(exclude).claude'; git commit -qm work; ok "$S" gate 1.1
echo '| 1.1-u2 | 1.1 | unit | writes coverage | exit 0 | `echo c > cover.out` | 1 |' >> $T
ok "$S" run 1.1-u2; ok "$S" gate 1.1
echo '| 9.9-u1 | 9.9 | unit | orphan | exit 0 | `true` | 1 |' >> $T
ok "$S" run 9.9-u1; ko "$S" gate 9.9      # task in no plan: no Levels to hold it to

# a pre-4.0 plan table: never gated directly; its sub-task in the re-planned table is
printf '| # | Task | req | Test that proves it | Needs | Done |\n|---|---|---|---|---|---|\n| 5.1 | old | 1 | `go test ./x` | – | [x] 2026-01-01 |\n\n## Re-planned\n\n| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n| 5.1.1 | bring 5.1 under test | 1 | unit | 5.1 | – | [ ] |\n' > .claude/clio/docs/plans/old.md
echo '| 5.1-u1 | 5.1 | unit | old | exit 0 | `true` | 1 |' >> $T
echo '| 5.1.1-u1 | 5.1.1 | unit | new | exit 0 | `true` | 1 |' >> $T
ok "$S" run 5.1-u1; out=$("$S" gate 5.1); grep -q 'pre-4.0 row' <<<"$out" || { echo "old row not refused: $out"; bad=1; }
ok "$S" run 5.1.1-u1; ok "$S" gate 5.1.1

# coverage: what a re-plan reads — level and last result per case, "no cases" for a pre-4.0 row
[ "$("$S" coverage 1.3 | grep -c .)" -ge 1 ] || { echo "coverage empty"; bad=1; }
"$S" coverage 1.3 | grep -q "1.3-r1	regression	pass" || { echo "coverage lost last result: $("$S" coverage 1.3)"; bad=1; }
[ "$("$S" coverage 7.7)" = "no cases" ] || { echo "coverage of an uncovered task"; bad=1; }

# regression that never failed is rejected
echo '| 1.3-r2 | 1.3 | regression | bug2 | exit 0 | `true` | 1 |' >> $T
"$S" run 1.3-r2 >/dev/null; ko "$S" gate 1.3

[ $bad -eq 0 ] && echo OK
exit $bad
