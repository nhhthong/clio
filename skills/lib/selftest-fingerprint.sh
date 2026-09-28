#!/usr/bin/env bash
# selftest-fingerprint.sh — fingerprint.sh on a throwaway repo: what moves the fp and what must not,
# the test/code split, artifacts, and the timeout wrapper. Prints OK or each mismatch.
set -u
export LC_ALL=C
L=$(cd "$(dirname "$0")" && pwd)
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT; cd "$d" || exit 1
git init -q; git config user.email t@t; git config user.name t
mkdir -p .claude/clio/database src tests; RUNS=$d/.claude/clio/database/runs.jsonl; : > "$RUNS"
. "$L/fingerprint.sh"
bad=0
same(){ [ "$1" = "$2" ] || { echo "FAIL (should not move) $3: $1 → $2"; bad=1; }; }
moved(){ [ "$1" != "$2" ] || { echo "FAIL (should move) $3: stayed $1"; bad=1; }; }
halves(){ split_fp "$(fp_tree)"; }   # "<tfp> <cfp>"

echo 'code v1' > src/app.txt; echo 'test v1' > tests/app_test.txt; git add -A; git commit -qm init

# content, not history: committing the same bytes keeps the fp; any edit moves it
f0=$(fp); git commit -qm empty --allow-empty; same "$f0" "$(fp)" "an empty commit"
echo 'code v2' > src/app.txt; f1=$(fp); moved "$f0" "$f1" "an edit"
git add src/app.txt; git commit -qm v2; same "$f1" "$(fp)" "committing the edited bytes"
echo 'scratch' > src/new.txt; f2=$(fp); moved "$f1" "$f2" "an untracked, non-ignored file"
echo 'src/new.txt' > .gitignore; git add .gitignore; git commit -qm ignore
f3=$(fp); echo 'scratch 2' > src/new.txt; same "$f3" "$(fp)" "an ignored file"
mkdir -p .claude/clio/docs; echo x > .claude/clio/docs/a.md; same "$f3" "$(fp)" "anything under .claude/"

# racy git: a same-size edit in the second of its `git add`, fingerprinted a second later
echo 'aaa' > src/racy.txt; git add src/racy.txt; echo 'bbb' > src/racy.txt; sleep 1; f4=$(fp)
git add src/racy.txt; same "$f4" "$(fp)" "a same-size edit right after git add (racy git)"

# the split: a test edit moves tfp only, a code edit cfp only
read -r t0 c0 < <(halves)
echo 'test v2' > tests/app_test.txt; read -r t1 c1 < <(halves)
moved "$t0" "$t1" "tfp on a test edit"; same "$c0" "$c1" "cfp on a test edit"
echo 'code v3' > src/app.txt; read -r t2 c2 < <(halves)
same "$t1" "$t2" "tfp on a code edit"; moved "$c1" "$c2" "cfp on a code edit"
for p in foo_test.go a.test.ts b.spec.js tests/x.py test_y.py src/test/java/ATest.java spec/m_spec.rb __tests__/c.js; do
  mkdir -p "$(dirname "$p")"; echo x > "$p"; read -r ta ca < <(halves)
  echo y > "$p"; read -r tb cb < <(halves)
  moved "$ta" "$tb" "tfp for $p"; same "$ca" "$cb" "cfp for $p"
done

# artifacts: a file a run created is not code — until it is tracked; a non-ASCII path too
echo 'report v1' > coverage.out; echo 'gen v1' > 'src/tệp.ts'
echo '{"case":"x","artifacts":["coverage.out","src/tệp.ts"]}' >> "$RUNS"
f5=$(fp); echo 'report v2' > coverage.out; same "$f5" "$(fp)" "an artifact edit"
git add 'src/tệp.ts'; git commit -qm "generated file kept"
f6=$(fp); echo 'gen v2' > 'src/tệp.ts'; moved "$f6" "$(fp)" "a tracked former artifact (non-ASCII path)"

# untracked lists files, never a directory entry
mkdir -p gen/sub; echo x > gen/sub/a.txt
untracked | grep -qx 'gen/sub/a.txt' || { echo "FAIL untracked: file not listed"; bad=1; }
untracked | grep -q '/$' && { echo "FAIL untracked: a directory entry listed"; bad=1; }

# timeout_cmd: coreutils timeout (or gtimeout) with CLIO_TIMEOUT, else nothing
if command -v timeout >/dev/null; then
  [ "$(timeout_cmd)" = "timeout 600" ] || { echo "FAIL timeout_cmd default: $(timeout_cmd)"; bad=1; }
  [ "$(CLIO_TIMEOUT=5 timeout_cmd)" = "timeout 5" ] || { echo "FAIL timeout_cmd CLIO_TIMEOUT"; bad=1; }
fi
[ -z "$(PATH=/nonexistent timeout_cmd)" ] || { echo "FAIL timeout_cmd without either"; bad=1; }

[ $bad -eq 0 ] && echo OK
exit $bad
