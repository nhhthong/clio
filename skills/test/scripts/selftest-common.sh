# selftest-common.sh — sourced by selftest-*.sh: a throwaway repo with Clio's layout and one commit,
# the script under test ($S) and the check helpers. Each selftest file gets its own repo, so no file
# depends on what another left behind.
set -u
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/clio-test.sh
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT; cd "$d" || exit 1
git init -q; git config user.email t@t; git config user.name t
mkdir -p .claude/clio/database .claude/clio/docs/tests .claude/clio/docs/plans
echo x > app.txt; git add app.txt; git commit -qm init
bad=0
ok(){ "$@" >/dev/null 2>&1 || { echo "expected pass: $*"; bad=1; }; }
ko(){ "$@" >/dev/null 2>&1 && { echo "expected fail: $*"; bad=1; }; }
okg(){ "$S" approve "$1" >/dev/null; ok "$S" gate "$1"; }   # the user said yes to the table, then gate
has(){ out=$("$S" gate "$1"); grep -q "$2" <<<"$out" || { echo "gate $1 lacks '$2': $out"; bad=1; }; }
PLAN_HEAD='| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n'
CASE_HEAD='| Case | Task | Level | Covers | Behaviour | Expected | Command | Repeat |\n|---|---|---|---|---|---|---|---|\n'
