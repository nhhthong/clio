#!/usr/bin/env bash
# clio-test.sh run <case-id> | run-task <task-id>... | red <task-id>... [--base <rev>] | approve <task-id>... | gate <task-id> | coverage <task-id> | fp
#   run       run one case from .claude/clio/docs/tests/*.md `Repeat` times, append the result to runs.jsonl
#   run-task  run every case of each task that way — one call proves a whole task
#   red       run the cases that must be seen red (regression, critical) on the code at a base commit,
#             in a throwaway worktree with today's tests — red without breaking code by hand
#   approve   record the hash of each task's case rows once the user approved them (one batch, one yes);
#             the gate holds each table to its own hash
#   gate      exit 0 only if every case of a plan task has fresh, complete, passing evidence
#   coverage  per case of a task: level and last recorded result (pass/fail/never) — what /clio:plan
#             reads to decide whether a ticked task's tests fall short
#   fp        print the working-tree fingerprint evidence is bound to
# The model never writes runs.jsonl itself: a pass exists only because this script saw exit 0.
set -uo pipefail
export LC_ALL=C   # sort and comm must agree on order; awk matches bytes
# The catalog this script's own repo ships beside it — not the target repo's — so `level_ids` below
# reads the same ids /clio:test wrote from, however clio-test.sh was invoked. $0: SKILL.md calls it
# by full path every time; a relative invocation only breaks the id-coverage check, not run/gate.
LEVELS_FILE=$(cd "$(dirname "$0")/.." && pwd)/LEVELS.md
# Every Markdown table this script reads goes through the shared parser — resolved before the cd below.
. "$(cd "$(dirname "$0")/../.." && pwd)/lib/tables.sh" || { echo "FAIL: cannot load skills/lib/tables.sh"; exit 1; }

root=$PWD
while [ ! -d "$root/.claude/clio" ] && [ "$root" != "/" ]; do root=$(dirname "$root"); done
[ -d "$root/.claude/clio" ] || { echo "FAIL: no .claude/clio above $PWD"; exit 1; }
cd "$root"
git rev-parse --git-dir >/dev/null 2>&1 || { echo "FAIL: clio-test needs a git repository — evidence is bound to the working tree"; exit 1; }
RUNS=$root/.claude/clio/database/runs.jsonl   # absolute: `red` runs cases from a worktree
TESTS=.claude/clio/docs/tests
PLANS=.claude/clio/docs/plans
touch "$RUNS"

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


# The only level names a plan or a case may use — LEVELS.md's catalog, lowercase.
LEVELS="unit integration api contract e2e idempotency concurrency security resilience perf load stress regression smoke mutation"

# Every case row of every tests file — see case_rows in lib/tables.sh for the columns.
cases(){ shopt -s nullglob; case_rows "$LEVELS" "$TESTS"/*.md; }

# All `level.n` ids LEVELS.md's catalog names for a level — the risks a named level must cover or
# excuse. A level whose bullets carry no id (regression, smoke, mutation — each has its own gate
# rule already) returns nothing, which is how gate() knows to skip the check entirely for it.
level_ids(){ grep -oE "\`$1\.[0-9]+\`" "$LEVELS_FILE" 2>/dev/null | tr -d '`' | sort -u; }

# The bullet-scoped Not applicable list test/SKILL.md § 3 describes, for one task: `<id><TAB><line>`.
# The excuse check reads the id, table_hash the line — one parse for both, so a line that excuses an
# id is always a line the user approved.
na_lines(){ shopt -s nullglob; na_rows "$TESTS"/*.md | awk -F'\t' -v t="$1" '$1==t {print $2 "\t" $3}'; }
excused_ids(){ na_lines "$1" | cut -f1; }

# run <case-id> [dir base]: the case's row is read here, in the repo; with dir (a worktree `red` built)
# the fingerprint is taken and the command executed there, and the record notes the base commit.
run(){
  local id=$1 dir=${2:-} base=${3:-} row task level covers cmd rep trk
  row=$(cases | awk -F'\t' -v c="$id" '$1==c')
  [ -n "$row" ] || { echo "FAIL: case $id is in no $TESTS/*.md row"; exit 1; }
  [ "$(wc -l <<<"$row")" -eq 1 ] || { echo "FAIL: case $id appears twice"; exit 1; }
  IFS=$'\t' read -r _ task level covers cmd rep trk err <<<"$row"
  [ -z "$err" ] || { echo "FAIL: case $id: $err"; exit 1; }
  case $cmd in ''|'–'|'-') echo "FAIL: case $id has no command (N/A row?)"; exit 1 ;; esac

  local f tree tfp cfp log i passed=0 code=0 before created
  [ -z "$dir" ] || cd "$dir" || exit 1
  tree=$(fp_tree); f=${tree:0:12}; read -r tfp cfp < <(split_fp "$tree")
  log=$(mktemp); before=$(untracked)
  # Each repeat is capped at CLIO_TIMEOUT seconds (default 600), so a deadlocked case fails instead
  # of hanging the run. `timeout` is coreutils; without it (stock macOS) the cap is skipped, said once.
  local to=(); read -ra to <<<"$(timeout_cmd)"
  [ ${#to[@]} -gt 0 ] || echo "note: no timeout/gtimeout on PATH — case runs uncapped (brew install coreutils)"
  for ((i=1; i<=rep; i++)); do
    ${to[@]+"${to[@]}"} bash -c "$cmd" </dev/null >"$log" 2>&1; code=$?
    [ "$code" -ne 124 ] || [ ${#to[@]} -eq 0 ] || echo "timed out after ${CLIO_TIMEOUT:-600}s (run $i of $rep)" >>"$log"
    [ "$code" -eq 0 ] || break
    passed=$((passed+1))
  done
  # A worktree's leftovers vanish with it — only the repo's own runs name artifacts.
  created=$(comm -13 <(printf '%s\n' "$before") <(untracked) | jq -Rsc 'split("\n") | map(select(.!=""))')
  [ -z "$dir" ] || created='[]'
  local result=fail; [ "$passed" -eq "$rep" ] && result=pass
  jq -nc --arg date "$(date +%Y-%m-%d)" --arg case "$id" --arg task "$task" --arg level "$level" \
    --arg cmd "$cmd" --arg commit "$(git rev-parse --short HEAD 2>/dev/null)" --arg fp "$f" --arg tfp "$tfp" --arg cfp "$cfp" \
    --arg result "$result" --argjson runs "$((passed + (code != 0)))" --argjson passed "$passed" --argjson exit "$code" --argjson artifacts "$created" \
    --arg base "$base" \
    '{date:$date,case:$case,task:$task,level:$level,cmd:$cmd,commit:($commit|select(.!="")//null),
      fp:$fp,tfp:$tfp,cfp:$cfp,result:$result,runs:$runs,passed:$passed,exit:$exit,artifacts:$artifacts}
      + (if $base=="" then {} else {red_base:$base} end)' >> "$RUNS"
  echo "$result: $id ($level) $passed/$rep — exit $code${base:+ — on $base}"
  [ "$created" = "[]" ] || echo "note: the run created $created — recorded as test artifacts, excluded from the fingerprint; gitignore them"
  [ "$result" = pass ] || { echo "--- last output"; tail -30 "$log"; }
  rm -f "$log"
  [ "$result" = pass ]
}

# --- Batch mode: one runner start for many cases -------------------------------------------------
# A runner that boots something heavy (Maven + JVM + Spring: ~7 s) pays it once per case when every
# case is its own command. A `Batch:` line in .claude/rules/*.md (test/SKILL.md § 1b finds and writes
# it) names the one command that runs many tests and the JUnit XML it leaves behind:
#   Batch: `mvn -q -pl api test -Dtest={tests}` · join: `,` · report: `api/target/surefire-reports/TEST-*.xml`
# A case joins a batch only if its own command IS that template with {tests} = its test id, so the
# batch runs exactly the cases' commands, merged. Each case's result is read from the report; nothing
# is inferred from the batch's exit code alone. A case the report does not show, or shows fewer times
# than its Repeat, falls back to its own command.

# One line per template: template<TAB>join<TAB>report glob.
batches(){
  shopt -s nullglob; local files=(.claude/rules/*.md)
  [ ${#files[@]} -gt 0 ] || return 0
  awk "$CLIO_NOCOMMENT"'/^[-* \t]*Batch:/' "${files[@]}" | sed -E 's/^[-* \t]*Batch:[ \t]*//' \
    | awk -F' · ' '{ t=$1; j=","; r=""
        for(i=2;i<=NF;i++){ if($i ~ /^join:/){j=$i; sub(/^join:[ \t]*/,"",j)} else if($i ~ /^report:/){r=$i; sub(/^report:[ \t]*/,"",r)} }
        gsub(/^`|`[ \t]*$/,"",t); gsub(/^`|`[ \t]*$/,"",j); gsub(/^`|`[ \t]*$/,"",r)
        if (index(t,"{tests}") && r!="") print t "\t" j "\t" r }'
}
# The test id a case command fills a template with; fails when the command is not that template.
batch_id(){
  local cmd=$1 tpl=$2 pre suf id
  pre=${tpl%%\{tests\}*}; suf=${tpl#*\{tests\}}
  [[ $cmd == "$pre"* && $cmd == *"$suf" ]] || return 1
  id=${cmd#"$pre"}; id=${id%"$suf"}
  [[ -n $id && $id != *[[:space:],+*]* ]] || return 1   # one plain test id, not a list or a pattern
  printf '%s\n' "$id"
}
# JUnit XML → class<TAB>test<TAB>status<TAB>rep, one line per <testcase>. class is the full classname
# (two packages' OrderTest stay apart); test drops `(…)` and `[n]`; status 0 pass, 1 failure/error,
# 2 skipped; rep is 1 when the entry is a repetition of the same call — a bare name (go -count) or
# `name()[k]` (JUnit 5 @RepeatedTest) — and 0 for a parameterised one (`name(String)[k]`, `name[k]`):
# ten parameter sets are ten different calls, not ten repeats of one.
junit(){
  awk '
    function attr(k,   m){ if (match($0, k "=\"[^\"]*\"")) { m=substr($0,RSTART,RLENGTH); sub(/^[^"]*"/,"",m); sub(/"$/,"",m); return m } return "" }
    /<testcase[ \t>]/ {
      c=attr("classname"); n=attr("name"); r=n; sub(/[\(\[].*/,"",n); r=substr(r, length(n)+1)
      rp = (r=="" || r ~ /^\(\)\[[0-9]+\]$/) ? 1 : 0; st=0; open=1
      if ($0 ~ /<testcase[^>]*\/>/) { print c "\t" n "\t" st "\t" rp; open=0 }
      next }
    open && /<(failure|error)[ \t>\/]/ { st=1 }
    open && /<skipped[ \t>\/]/ && st==0 { st=2 }
    open && /<\/testcase>/ { print c "\t" n "\t" st "\t" rp; open=0 }' "$@"
}

# run_batch dir base tpl join report — stdin: case<TAB>test-id lines. Records one runs.jsonl line
# per case, like run() does, with the batch command beside the case's own.
run_batch(){
  local dir=$1 base=$2 tpl=$3 join=$4 report=$5 pairs tests full marker log code=0 tree f tfp cfp
  pairs=$(cat)
  tests=$(cut -f2 <<<"$pairs" | awk -v j="$join" 'NR>1{printf "%s", j} {printf "%s", $0}')
  full=${tpl//\{tests\}/$tests}
  (
    [ -z "$dir" ] || cd "$dir" || exit 1
    tree=$(fp_tree); f=${tree:0:12}; read -r tfp cfp < <(split_fp "$tree")
    marker=$(mktemp); log=$(mktemp); sleep 1   # reports must be newer than the marker, to the second
    local to=(); read -ra to <<<"$(timeout_cmd)"
    [ ${#to[@]} -gt 0 ] || echo "note: no timeout/gtimeout on PATH — the batch runs uncapped (brew install coreutils)"
    ${to[@]+"${to[@]}"} bash -c "$full" </dev/null >"$log" 2>&1; code=$?
    [ "$code" -ne 124 ] || [ ${#to[@]} -eq 0 ] || echo "timed out after ${CLIO_TIMEOUT:-600}s (whole batch)" >>"$log"
    shopt -s nullglob; local xmls=() r
    for r in $report; do [ "$r" -nt "$marker" ] && xmls+=("$r"); done
    local rows=""; [ ${#xmls[@]} -eq 0 ] || rows=$(junit "${xmls[@]}")
    local id tid row task level cmd rep cnt bad reps result fall=() shown=0
    while IFS=$'\t' read -r id tid; do
      row=$(cases | awk -F'\t' -v c="$id" '$1==c'); IFS=$'\t' read -r _ task level _ cmd rep _ _ <<<"$row"
      # A test id matches a classname in full or by its trailing `.Simple` part — `OrderTest#x`
      # matches every package's OrderTest (as `-Dtest=OrderTest#x` runs them all), `com.a.OrderTest#x`
      # only that one. cnt: entries seen; bad: failed or skipped; reps: repetitions of one call —
      # the fewest any matched class shows, a parameterised test's sets counting once — which is
      # what `Repeat` asks for.
      read -r cnt bad reps < <(awk -F'\t' -v t="$tid" '
        function cls(want) { return $1 == want || substr($1, length($1)-length(want)) == "." want }
        { if (index(t,"#")) { k=t; sub(/#.*/,"",k); m=t; sub(/^[^#]*#/,"",m); hit = ($2 == m && cls(k)) }
          else hit = ($2 == t || cls(t)) }
        hit { n++; if ($3 != 0) b++; rc[$1] += $4; seen[$1] = 1 }
        END { r = -1; for (k in seen) { v = rc[k] > 0 ? rc[k] : 1; if (r < 0 || v < r) r = v }  # per class: two
              print n+0, b+0, (r < 0 ? 0 : r) }' <<<"$rows")   # packages are not two repetitions
      if [ "$cnt" -gt 0 ] && [ "$bad" -eq 0 ] && [ "$reps" -lt "$rep" ]; then fall+=("$id"); continue; fi
      result=fail; [ "$cnt" -gt 0 ] && [ "$bad" -eq 0 ] && result=pass
      jq -nc --arg date "$(date +%Y-%m-%d)" --arg case "$id" --arg task "$task" --arg level "$level" \
        --arg cmd "$cmd" --arg batch "$full" --arg commit "$(git rev-parse --short HEAD 2>/dev/null)" \
        --arg fp "$f" --arg tfp "$tfp" --arg cfp "$cfp" --arg result "$result" \
        --argjson runs "$reps" --argjson passed "$([ "$bad" -eq 0 ] && echo "$reps" || echo 0)" --argjson exit "$code" --arg base "$base" \
        '{date:$date,case:$case,task:$task,level:$level,cmd:$cmd,batch:$batch,commit:($commit|select(.!="")//null),
          fp:$fp,tfp:$tfp,cfp:$cfp,result:$result,runs:$runs,passed:$passed,exit:$exit,artifacts:[]}
          + (if $base=="" then {} else {red_base:$base} end)' >> "$RUNS"
      echo "$result: $id ($level) $([ "$bad" -eq 0 ] && echo "$reps" || echo 0)/$reps — batch${base:+ — on $base}$([ "$cnt" -gt 0 ] || echo ' — not in the report')"
      if [ "$result" = fail ] && [ "$shown" -eq 0 ]; then echo "--- last output"; tail -30 "$log"; shown=1; fi
    done <<<"$pairs"
    rm -f "$marker" "$log"
    local fb bad2=0
    for fb in ${fall[@]+"${fall[@]}"}; do
      echo "note: $fb's report shows fewer repetitions than its Repeat (parameter sets are not repeats) — running it on its own"
      ( run "$fb" "$dir" "$base" ) || bad2=1
    done
    [ "$bad2" -eq 0 ]
  )
}

# run_cases dir base case-id...: every case through a matching `Batch:` template when one fits,
# the rest one command each. Exit non-zero if any case failed; results are in runs.jsonl.
run_cases(){
  local dir=$1 base=$2; shift 2
  local all tpls left=("$@") keep id cmd tid pairs tpl join report bad=0
  all=$(cases); tpls=$(batches)
  while IFS=$'\t' read -r -u 3 tpl join report; do
    [ -n "$tpl" ] || continue
    pairs=""; keep=()
    for id in ${left[@]+"${left[@]}"}; do
      cmd=$(awk -F'\t' -v c="$id" '$1==c {print $5}' <<<"$all")
      if tid=$(batch_id "$cmd" "$tpl"); then pairs+="$id"$'\t'"$tid"$'\n'; else keep+=("$id"); fi
    done
    left=(${keep[@]+"${keep[@]}"})
    [ -z "$pairs" ] || { run_batch "$dir" "$base" "$tpl" "$join" "$report" <<<"${pairs%$'\n'}" || bad=1; }
  done 3<<<"$tpls"
  for id in ${left[@]+"${left[@]}"}; do ( run "$id" "$dir" "$base" ) || bad=1; done
  [ "$bad" -eq 0 ]
}
# The last recorded result per case id given on stdin: id<TAB>pass|fail|never.
last_results(){ jq -Rn -r --arg ids "$(cat)" '($ids | split("\n") | map(select(.!=""))) as $w
  | reduce (inputs | fromjson? | select(.case)) as $r ({}; .[$r.case] = $r.result)
  | . as $m | $w[] | "\(.)\t\($m[.] // "never")"' "$RUNS"; }

# Every runnable case of each task given — all tasks' cases in one run_cases, so a batch template
# starts its runner once for the lot. Keeps going past a failure; exits non-zero if any case failed.
# Every task id is checked before anything runs.
run_task(){
  local task ids="" all res n bad total=0 totalbad=0
  all=$(cases)
  for task in "$@"; do
    awk -F'\t' -v t="$task" '$2==t && $5!~/^(|–|-)$/' <<<"$all" | grep -q . \
      || { echo "FAIL: task $task has no runnable case in $TESTS/*.md — nothing run"; exit 1; }
    ids+=$(awk -F'\t' -v t="$task" '$2==t && $5!~/^(|–|-)$/ {print $1}' <<<"$all")$'\n'
  done
  local list=(); while IFS= read -r id; do [ -n "$id" ] && list+=("$id"); done <<<"$ids"
  run_cases "" "" "${list[@]}"
  res=$(printf '%s\n' "${list[@]}" | last_results)
  for task in "$@"; do
    read -r n bad < <(awk -F'\t' -v t="$task" 'NR==FNR { if ($2==t) mine[$1]=1; next }
      ($1 in mine) { n++; if ($2!="pass") b++ } END { print n+0, b+0 }' <(printf '%s\n' "$all") - <<<"$res")
    echo "task $task: $((n-bad))/$n cases passed"
    total=$((total+n)); totalbad=$((totalbad+bad))
  done
  [ $# -eq 1 ] || echo "all: $((total-totalbad))/$total cases passed across $# tasks"
  [ "$totalbad" -eq 0 ]
}

# red <task-id>... [--base <rev>]: see the cases that must be seen red fail on the code as it was at
# <rev> (default HEAD — the commit before the uncommitted change), without anyone breaking code by
# hand. A throwaway worktree of <rev> gets today's test files (and only those) — so the run has the
# same tfp as the pass and another cfp, which is exactly what the gate counts as red. Which cases:
# every `regression` case, and every non-mutation case of a `critical` task; nothing else needs red.
# Exit 0 only if each of them failed there. It cannot tell a failed assertion from a failed build —
# the output tail is printed for that; a build error is not a real red.
# ponytail: dependency dirs a worktree lacks are linked in by a fixed list; add one when a stack needs it.
red(){
  local base=HEAD tasks=() task ids="" all prow wt id bad=0 n=0 f d
  while [ $# -gt 0 ]; do
    case $1 in
      --base) [ -n "${2:-}" ] || { echo "FAIL: --base needs a commit"; exit 1; }; base=$2; shift 2 ;;
      *) tasks+=("$1"); shift ;;
    esac
  done
  [ ${#tasks[@]} -gt 0 ] || { echo "usage: clio-test.sh red <task-id>... [--base <rev>]"; exit 1; }
  git rev-parse -q --verify "$base^{commit}" >/dev/null || { echo "FAIL: $base is not a commit"; exit 1; }
  all=$(cases)
  for task in "${tasks[@]}"; do
    prow=$(shopt -s nullglob; plan_rows "$PLANS"/*.md | awk -F'\t' -v t="$task" '$2==t {print $5; exit}')
    [ -n "$prow" ] || { echo "FAIL: task $task is in no $PLANS/*.md row — nothing run"; exit 1; }
    ids+=$(awk -F'\t' -v t="$task" -v crit="$([[ $prow == *critical* ]] && echo 1)" \
      '$2==t && $5!~/^(|–|-)$/ && $8=="" && ($3=="regression" || (crit && $3!="mutation")) {print $1}' <<<"$all")$'\n'
  done
  ids=$(grep . <<<"$ids")
  [ -n "$ids" ] || { echo "nothing needs red in ${tasks[*]}: no regression case, no critical task — run-task is enough"; return 0; }

  wt=$(mktemp -d); rmdir "$wt"
  git worktree add -q --detach "$wt" "$base" 2>/dev/null || { echo "FAIL: cannot create a worktree at $base"; exit 1; }
  # expanded now: the trap fires after this function's locals are gone
  trap "git worktree remove --force '$wt' >/dev/null 2>&1" EXIT
  # Test files: the base's are removed, today's copied in — tracked or not, never ignored ones.
  (cd "$wt" && git ls-files | grep -E "$TEST_PATHS" | while IFS= read -r f; do rm -f -- "$f"; done)
  git ls-files -co --exclude-standard -- . ':(exclude).claude' | grep -E "$TEST_PATHS" | while IFS= read -r f; do
    [ -f "$f" ] && mkdir -p "$wt/$(dirname "$f")" && cp -p -- "$f" "$wt/$f"
  done
  for d in node_modules vendor .venv venv; do
    [ -d "$d" ] && [ ! -e "$wt/$d" ] && git check-ignore -q "$d" && ln -s "$root/$d" "$wt/$d"
  done

  local label; label=$(git rev-parse --short "$base")
  local list=(); while IFS= read -r id; do list+=("$id"); done <<<"$ids"
  # Every failure's output is printed by run/run_batch: read it — a red counts only on an assertion.
  run_cases "$wt" "$label" "${list[@]}" | sed 's/^/  | /'
  local res; res=$(printf '%s\n' "${list[@]}" | last_results)
  while IFS=$'\t' read -r id r; do
    n=$((n+1))
    if [ "$r" = pass ]; then
      echo "NOT RED: $id passed on $label — it cannot tell that code from yours (change already committed? --base <the commit before it>)"; bad=$((bad+1))
    else echo "red: $id failed on $label"; fi
  done <<<"$res"
  echo "red on $label: $((n-bad))/$n cases failed as they must"
  [ "$bad" -eq 0 ]
}

# ponytail: fixed floor for concurrency repeats; make it a per-case column if 20 proves wrong somewhere.
CONCURRENCY_MIN_REPEAT=20
# LEVELS.md's mutation default; override per project with `NN%` on the `Mutation:` line in plans/infra.md.
MUTATION_MIN_THRESHOLD=80

# The task's case rows and its `Not applicable` lines, whitespace-normalised: what the user approved.
# An excuse added after approve voids it like an edited case would. A task with no such line hashes
# exactly as before 4.1.2, so its approval still holds.
table_hash(){
  shopt -s nullglob
  local files=("$TESTS"/*.md)
  [ ${#files[@]} -gt 0 ] || { echo none; return; }
  { case_lines "$1" "${files[@]}"
    na_lines "$1" | cut -f2-
  } | git hash-object --stdin | cut -c1-12
}

# One yes can cover a batch: each task still gets its own record and hash, so editing one table later
# voids that task's approval only. All ids are checked first — a typo approves nothing.
approve(){
  local task all h
  all=$(cases)
  for task in "$@"; do
    awk -F'\t' -v t="$task" '$2==t' <<<"$all" | grep -q . || { echo "FAIL: task $task has no case rows to approve — nothing approved"; exit 1; }
  done
  for task in "$@"; do
    h=$(table_hash "$task")
    jq -nc --arg date "$(date +%Y-%m-%d)" --arg task "$task" --arg hash "$h" \
      '{date:$date,approve:$task,hash:$hash}' >> "$RUNS"
    echo "approved: task $task case table $h"
  done
}

gate(){
  local task=$1 fails=0 cur rows levels
  fail(){ echo "FAIL: $*"; fails=$((fails+1)); }
  cur=$(fp)
  rows=$(cases | awk -F'\t' -v t="$task" '$2==t')
  [ -n "$rows" ] || { echo "FAIL: task $task has no cases — run /clio:test $task"; exit 1; }
  local approved
  approved=$(jq -Rr --arg t "$task" 'fromjson? | select(.approve==$t) | .hash' "$RUNS" | tail -1)
  if [ -z "$approved" ]; then fail "$task: case table never approved — show it to the user, then \`clio-test.sh approve $task\`"
  elif [ "$approved" != "$(table_hash "$task")" ]; then fail "$task: case table changed since it was approved ($approved) — a case added, removed or edited needs the user's yes again"; fi

  # The plan's Levels cell: "critical · unit, api" or "unit, api".
  local found
  # plan_rows says, per row, whether its table has a Levels column or a pre-4.0 Test command.
  found=$(shopt -s nullglob; plan_rows "$PLANS"/*.md | awk -F'\t' -v t="$task" '$2==t {print $8 "\t" $7 "\t" $5; exit}')
  [ -n "$found" ] || { echo "FAIL: task $task is in no $PLANS/*.md row — the gate needs the plan's Levels"; exit 1; }
  local kind done
  IFS=$'\t' read -r kind done levels <<<"$found"
  [ "$kind" = row ] || { echo "FAIL: task $task is a pre-4.0 row (Test column, no Levels) — /clio:plan <area> adds a sub-task that brings it under /clio:test; gate that"; exit 1; }
  [[ $done != *superseded* ]] || { echo "FAIL: task $task is superseded (${done# }) — gate the row that replaced it"; exit 1; }
  local critical=no; [[ $levels == *critical* ]] && critical=yes
  # Mutation is required only where the plan names it (the user agreed the task is beyond critical),
  # never implied by `critical`. `Mutation: none` in plans/infra.md is an ADR against it, so a row
  # still naming it is a contradiction to resolve, not a level to waive quietly.
  local no_mutation=no
  grep -qiE '^Mutation: *none' "$PLANS/infra.md" 2>/dev/null && no_mutation=yes
  # The threshold a mutation case's command must show: the project's own `NN%` if it set one,
  # else LEVELS.md's default. Read once so every mutation case in this task is held to the same number.
  local mutation_req=$MUTATION_MIN_THRESHOLD mline
  mline=$(grep -iE '^Mutation:' "$PLANS/infra.md" 2>/dev/null | head -1)
  [[ $mline =~ ([0-9]{1,3})% ]] && mutation_req=${BASH_REMATCH[1]}
  local req_ids covered excused rid
  for l in $(tr ',·' '  ' <<<"${levels//critical/}"); do
    [[ " $LEVELS " == *" $l "* ]] || { fail "$task: plan level '$l' is not one of: $LEVELS"; continue; }
    [ "$l" != mutation ] || [ "$no_mutation" = no ] \
      || { fail "$task: plan names 'mutation' but plans/infra.md says \`Mutation: none\` — re-plan the task without it, or change the ADR"; continue; }
    awk -F'\t' -v l="$l" '$3==l && $5!~/^(|–|-)$/' <<<"$rows" | grep -q . \
      || { fail "$task: plan requires level '$l', no runnable case covers it"; continue; }
    # Bullet coverage: only for a level LEVELS.md gives ids, and only once this task has at least one
    # Covers-tracked row for it — a pre-4.1 case table (no Covers column) is grandfathered, not failed.
    req_ids=$(level_ids "$l")
    [ -n "$req_ids" ] || continue
    awk -F'\t' -v l="$l" '$3==l && $7==1{f=1} END{exit !f}' <<<"$rows" || continue
    covered=$(awk -F'\t' -v l="$l" '$3==l && $7==1{print $4}' <<<"$rows" \
      | tr ',·' '\n\n' | sed 's/^[ \t]*//;s/[ \t]*$//' | grep -vE '^(|–|-)$')
    excused=$(excused_ids "$task")
    while IFS= read -r rid; do
      [ -n "$rid" ] || continue
      grep -qxF "$rid" <<<"$covered" && continue
      grep -qxF "$rid" <<<"$excused" && continue
      fail "$task: $l has no case covering $rid and no \`Not applicable\` line for it — LEVELS.md § $l"
    done <<<"$req_ids"
  done

  # One case, one command: a command reused under another case (or level) proves nothing new.
  local dup
  while IFS= read -r dup; do [ -n "$dup" ] && fail "$task: cases $dup run the same command — one case, one command"
  done < <(awk -F'\t' '$5!~/^(|–|-)$/ {ids[$5]=ids[$5] (ids[$5]==""?"":", ") $1; n[$5]++}
    END {for (c in n) if (n[c]>1) print ids[c]}' <<<"$rows")

  local id level covers cmd rep trk err last flaky red m
  while IFS=$'\t' read -r id _ level covers cmd rep trk err; do
    [ -z "$err" ] || { fail "$id: $err"; continue; }
    case $cmd in ''|'–'|'-') continue ;; esac
    [ "$level" != concurrency ] || [ "$rep" -ge "$CONCURRENCY_MIN_REPEAT" ] \
      || fail "$id: concurrency case repeats $rep < $CONCURRENCY_MIN_REPEAT"
    if [ "$level" = mutation ]; then
      # The tool's own exit code is trusted (LEVELS.md: it fails below threshold) — but a threshold
      # written as 0, or left out, always exits 0 too. So the command must pass it as a flag whose name
      # says so — Stryker `--thresholds.break N`, PIT `-DmutationThreshold=N`, a wrapper's
      # `--threshold N` / `--min-score N` — and every such flag must be >= the bar: a stray 80 elsewhere
      # (a port, `# 80`) no longer counts, and `--threshold 0 --min-score 80` is refused. A `#` is
      # refused outright: bash -c would treat the rest as a comment the tool never sees.
      m=$(grep -oiE '(thresholds\.break|mutationThreshold|threshold|min[-_]score)[ =:]+[0-9]{1,3}' <<<"$cmd" \
        | grep -oE '[0-9]+$' | awk 'NR==1{x=$1+0} {if($1+0<x) x=$1+0} END{print (NR ? x : -1)}')
      if [[ $cmd == *'#'* ]]; then
        fail "$id: mutation command contains \`#\` — bash -c drops everything after it; pass the threshold as a real flag"
      elif [ "$m" -lt "$mutation_req" ]; then
        fail "$id: mutation command shows no threshold >= ${mutation_req}% (lowest threshold flag: ${m/#-1/none}) — pass it as --thresholds.break N / -DmutationThreshold=N / --threshold N / --min-score N; default is $MUTATION_MIN_THRESHOLD, override with \`NN%\` on the \`Mutation:\` line in plans/infra.md"
      fi
    fi
    last=$(jq -Rc --arg c "$id" 'fromjson? | select(.case==$c)' "$RUNS" | tail -1)
    [ -n "$last" ] || { fail "$id: never run"; continue; }
    jq -e '.result=="pass"' >/dev/null <<<"$last" || { fail "$id: last run failed"; continue; }
    jq -e --arg f "$cur" '.fp==$f' >/dev/null <<<"$last" || fail "$id: code changed since the last pass — re-run (see \`git status --short\`; a test output that is not gitignored counts as code)"
    jq -e --arg c "$cmd" '.cmd==$c' >/dev/null <<<"$last" || fail "$id: command changed since the last pass — re-run"
    jq -e --argjson r "$rep" '.runs>=$r' >/dev/null <<<"$last" || fail "$id: ran fewer times than Repeat $rep"
    # Only runs of this command count, in file order (runs.jsonl is append-only).
    #   flaky — it failed on this very code after passing on it: same fp, both results.
    #   red   — it failed before a pass on this code, with the test files as they were at that pass and
    #           the code under test different: the case can tell them apart. A run from before 4.1.2
    #           carries no tfp/cfp and is judged the old way (any other fp).
    # ponytail: a fail at this fp *before* its first pass is forgiven (a DB not yet up); a real flake
    # that happens to fail first slips through — Repeat is what catches those.
    read -r flaky red < <(jq -Rn --arg c "$id" --arg f "$cur" --arg m "$cmd" -r '
      [inputs | fromjson? | select(.case==$c and .cmd==$m)] | to_entries as $r
      | ([$r[] | select(.value.fp==$f and .value.result=="pass") | .key]) as $p
      | [ ($p|length>0) and any($r[]; .key>$p[0] and .value.fp==$f and .value.result=="fail"),
          (if ($p|length)==0 then false else ($r[$p[-1]].value) as $ok
            | any($r[]; .key<$p[-1] and .value.result=="fail" and
                (if .value.tfp and $ok.tfp then .value.tfp==$ok.tfp and .value.cfp!=$ok.cfp
                 else .value.fp!=$f end)) end) ]
      | "\(.[0]) \(.[1])"' "$RUNS")
    [ "$flaky" = false ] || fail "$id: flaky — failed on this code after passing on it; /clio:memo files it as code-debt \`flaky:\`"
    if [ "$red" = false ]; then
      # A test never seen failing may pass by construction. Regression must prove it reproduced the bug;
      # on a critical task every case must. A mutation case is exempt: its red is a score below threshold.
      # Only these two need red; any other case was checked by its spec-sourced Expected and the approval.
      if [ "$level" = regression ]; then fail "$id: regression case never failed, with this command and these test files, on code before the fix — \`clio-test.sh red $task\`, then run-task"
      elif [ "$level" = mutation ]; then :
      elif [ "$critical" = yes ]; then
        fail "$id: never seen red on a critical task — \`clio-test.sh red $task\` (add --base <commit> if the change is committed), then run-task"
      fi
    fi
  done <<<"$rows"

  [ "$fails" -eq 0 ] && echo "OK: task $task — every case passed at $cur"
  [ "$fails" -eq 0 ]
}

coverage(){
  local task=$1 rows id level covers cmd last
  rows=$(cases | awk -F'\t' -v t="$task" '$2==t && $5!~/^(|–|-)$/')
  [ -n "$rows" ] || { echo "no cases"; return 0; }
  while IFS=$'\t' read -r id _ level covers cmd _ _ _; do
    last=$(jq -Rr --arg c "$id" 'fromjson? | select(.case==$c) | .result' "$RUNS" | tail -1)
    printf '%s\t%s\t%s\n' "$id" "$level" "${last:-never}"
  done <<<"$rows"
}

case ${1:-} in
  coverage) [ -n "${2:-}" ] || { echo "usage: clio-test.sh coverage <task-id>"; exit 1; }; coverage "$2" ;;
  run)  [ -n "${2:-}" ] || { echo "usage: clio-test.sh run <case-id>"; exit 1; }; run "$2" ;;
  run-task) [ -n "${2:-}" ] || { echo "usage: clio-test.sh run-task <task-id>..."; exit 1; }; shift; run_task "$@" ;;
  red)  [ -n "${2:-}" ] || { echo "usage: clio-test.sh red <task-id>... [--base <rev>]"; exit 1; }; shift; red "$@" ;;
  approve) [ -n "${2:-}" ] || { echo "usage: clio-test.sh approve <task-id>..."; exit 1; }; shift; approve "$@" ;;
  gate) [ -n "${2:-}" ] || { echo "usage: clio-test.sh gate <task-id>"; exit 1; }; gate "$2" ;;
  fp)   fp ;;
  *) echo "usage: clio-test.sh run <case-id> | run-task <task-id>... | red <task-id>... [--base <rev>] | approve <task-id>... | gate <task-id> | coverage <task-id> | fp"; exit 1 ;;
esac
