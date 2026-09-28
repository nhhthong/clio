# fingerprint.sh — what a test run is bound to: the working tree's content as a git tree id, split
# into test files and the code under test; plus the timeout every run is capped by. Sourced, never run.
# The caller sets RUNS (runs.jsonl, whose `artifacts` are excluded from the tree) and cds to the repo
# — or a `red` worktree — first; every function works on the current directory's git repo.
# selftest: skills/lib/selftest-fingerprint.sh

# Files earlier runs created (coverage files, mutation reports): outputs of a test, not code.
# Files only: a directory entry (ends in /, written before 4.1) would hide any source added to it later.
artifacts(){ jq -Rr 'fromjson? | .artifacts[]? | select(endswith("/") | not)' "$RUNS" 2>/dev/null | sort -u; }

# The working tree's content as a git tree id: every tracked and untracked, non-ignored file, minus
# .claude/ and known test artifacts. Content-addressed, so committing the same code keeps the id;
# any edit to code changes it. Built in a copy of the real index so git reuses its stat cache.
# ponytail: re-hashes changed files on each call; fine for repos git itself handles quickly.
# fp_tree prints the full tree id (its objects land in .git, so split_fp can list it); fp the short form.
fp(){ fp_tree | cut -c1-12; }
fp_tree(){
  local idx gi ex=()
  idx=$(mktemp); gi=$(git rev-parse --git-path index)
  # -p keeps the index's mtime: git re-hashes a file whose mtime is not older than the index ("racy
  # git"). A plain cp stamps the copy "now", so a same-size edit made in the second after a `git add`
  # passed as unchanged and the fp did not move.
  if [ -f "$gi" ]; then cp -p "$gi" "$idx"; else rm -f "$idx"; fi
  # An artifact that has since been tracked is source now (a generated file committed, a snapshot
  # kept): it counts again, or edits to it would never move the fp.
  while IFS= read -r a; do [ -n "$a" ] && ex+=(":(exclude,literal)$a"); done < <(comm -23 <(artifacts) <(git -c core.quotePath=false ls-files | sort -u))
  # -f: without it git refuses a path staged and then edited again (a ledger mid-memo), silently
  # leaving its staged copy in the tree — every later `git add` of that ledger then moves the fp.
  GIT_INDEX_FILE=$idx git rm -r -q -f --cached --ignore-unmatch -- .claude >/dev/null 2>&1
  for a in "${ex[@]}"; do GIT_INDEX_FILE=$idx git rm -r -q -f --cached --ignore-unmatch -- "${a#*)}" >/dev/null 2>&1; done
  GIT_INDEX_FILE=$idx git add -A -- . ':(exclude).claude' "${ex[@]}" >/dev/null 2>&1
  GIT_INDEX_FILE=$idx git write-tree
  rm -f "$idx"
}

# The cap every run uses — run() per repeat, run_batch() per batch: CLIO_TIMEOUT seconds (default
# 600) through coreutils `timeout`, or `gtimeout` (Homebrew coreutils on macOS). Prints nothing when
# neither exists; callers then run uncapped and say so.
timeout_cmd(){
  local t; for t in timeout gtimeout; do command -v "$t" >/dev/null && { echo "$t ${CLIO_TIMEOUT:-600}"; return; }; done
}

# Paths that are test code, not the code under test. A red run counts only if these were the same as
# at the pass and the rest was not — "same test, other code" — so breaking the test instead of the code
# proves nothing. Covers the usual layouts: Go `_test.go`, JS/TS `.test.`/`.spec.`, pytest `test_*.py`,
# JVM `src/test/`, Rails `spec/`, `tests/`, `__tests__/`, `testdata/`, `*Test.java`.
# ponytail: one fixed pattern; make it a per-repo setting when a real layout falls outside it.
TEST_PATHS='(^|/)(tests?|__tests__|specs?|testdata|e2e|cypress)/|[_.](test|spec)\.[^/]*$|(^|/)(test_[^/]*|conftest)\.py$|Tests?\.(java|kt|scala|cs|swift|php)$'
# "<test-fp> <code-fp>" of a tree from fp_tree: each is a hash of that half's `ls-tree` listing.
split_fp(){
  local ls; ls=$(git ls-tree -r "$1")
  printf '%s %s\n' \
    "$(awk -F'\t' -v re="$TEST_PATHS" '$2 ~ re' <<<"$ls" | git hash-object --stdin | cut -c1-12)" \
    "$(awk -F'\t' -v re="$TEST_PATHS" '$2 !~ re' <<<"$ls" | git hash-object --stdin | cut -c1-12)"
}
# Untracked files right now — diffed around a run to find what it created. Files, not directories:
# excluding a whole new directory would hide code written into it after the run.
# ponytail: a run that emits thousands of non-ignored files makes a long exclude list; gitignore them.
untracked(){ git ls-files -o --exclude-standard -- . ':(exclude).claude' 2>/dev/null | sort; }
