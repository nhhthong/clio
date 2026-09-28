#!/usr/bin/env bash
# selftest-red.sh — what counts as red: the test unchanged and the code different, by hand or through `red`
# on the base commit in a throwaway worktree.
. "$(dirname "$0")/selftest-common.sh"

printf "$PLAN_HEAD| 9.3 | fake red | 1 | critical · unit | – | – | [ ] |\n| 9.4 | real red | 1 | critical · unit | – | – | [ ] |\n" > .claude/clio/docs/plans/p.md
T2=.claude/clio/docs/tests/q.md; printf "$CASE_HEAD" > $T2

# red counts only with the test unchanged and the code different: breaking the test proves nothing
echo '| 9.3-u1 | 9.3 | unit | unit.1 | x | x | `bash chk_test.sh` | 1 |' >> $T2
echo 'exit 1' > chk_test.sh; ko "$S" run 9.3-u1
echo 'exit 0' > chk_test.sh; ok "$S" run 9.3-u1
"$S" approve 9.3 >/dev/null; has 9.3 'never seen red on a critical task'
echo '| 9.4-u1 | 9.4 | unit | unit.1 | x | x | `bash impl_test.sh` | 1 |' >> $T2
echo 'test -f impl94' > impl_test.sh; ko "$S" run 9.4-u1
touch impl94; ok "$S" run 9.4-u1; okg 9.4

# red: the cases that must be seen red run on the base commit's code with today's tests — no hand edits
printf '| 8.8 | crit red | 1 | critical · unit | – | – | [ ] |\n| 8.9 | plain | 1 | unit | – | – | [ ] |\n' >> .claude/clio/docs/plans/p.md
echo old > impl99.txt; git add impl99.txt; git commit -qm "impl99 before the change"
echo new > impl99.txt                                      # the change, uncommitted
echo 'grep -q new impl99.txt' > chk99_test.sh              # its test, a test file by name
echo '| 8.8-u1 | 8.8 | unit | unit.1 | x | x | `bash chk99_test.sh` | 1 |' >> $T2
echo '| 8.9-u1 | 8.9 | unit | unit.1 | x | x | `test -f impl99.txt` | 1 |' >> $T2
ok "$S" run 8.8-u1; "$S" approve 8.8 >/dev/null
has 8.8 'clio-test.sh red 8.8'                             # green alone is not enough on a critical task
out=$("$S" red 8.8); grep -q 'red on .*: 1/1 cases failed as they must' <<<"$out" || { echo "red 8.8: $out"; bad=1; }
[ -z "$(git worktree list | sed 1d)" ] || { echo "red left a worktree behind"; bad=1; }
ok "$S" run 8.8-u1; ok "$S" gate 8.8                       # red then green, same tests: the gate counts it
"$S" red 8.9 | grep -q 'nothing needs red' || { echo "red on a plain task ran something"; bad=1; }
git add impl99.txt chk99_test.sh; git commit -qm "change committed"
"$S" red 8.8 | grep -q 'NOT RED: 8.8-u1.*--base' || { echo "committed change not explained"; bad=1; }  # base == today's code
out=$("$S" red 8.8 --base HEAD~1); grep -q '1/1 cases failed as they must' <<<"$out" || { echo "red --base: $out"; bad=1; }
echo 'true' > pass99_test.sh; echo '| 8.8-u2 | 8.8 | unit | unit.1 | y | y | `bash pass99_test.sh` | 1 |' >> $T2
"$S" red 8.8 --base HEAD~1 | grep -q 'NOT RED: 8.8-u2' || { echo "a case passing on the base not flagged"; bad=1; }

[ $bad -eq 0 ] && echo OK
exit $bad
