#!/usr/bin/env bash
# clio-test.sh run <case-id> | gate <task-id> | coverage <task-id> | fp
#   run       run one case from .claude/clio/docs/tests/*.md `Repeat` times, append the result to runs.jsonl
#   gate      exit 0 only if every case of a plan task has fresh, complete, passing evidence
#   coverage  per case of a task: level and last recorded result (pass/fail/never) — what /clio:plan
#             reads to decide whether a ticked task's tests fall short
#   fp        print the working-tree fingerprint evidence is bound to
# The model never writes runs.jsonl itself: a pass exists only because this script saw exit 0.
set -uo pipefail

root=$PWD
while [ ! -d "$root/.claude/clio" ] && [ "$root" != "/" ]; do root=$(dirname "$root"); done
[ -d "$root/.claude/clio" ] || { echo "FAIL: no .claude/clio above $PWD"; exit 1; }
cd "$root"
git rev-parse --git-dir >/dev/null 2>&1 || { echo "FAIL: clio-test needs a git repository — evidence is bound to the working tree"; exit 1; }
RUNS=.claude/clio/database/runs.jsonl
TESTS=.claude/clio/docs/tests
PLANS=.claude/clio/docs/plans
touch "$RUNS"

# Paths earlier runs created (coverage files, mutation reports): outputs of a test, not code.
artifacts(){ jq -Rr 'fromjson? | .artifacts[]?' "$RUNS" 2>/dev/null | sort -u; }

# The working tree's content as a git tree id: every tracked and untracked, non-ignored file, minus
# .claude/ and known test artifacts. Content-addressed, so committing the same code keeps the id;
# any edit to code changes it. Built in a copy of the real index so git reuses its stat cache.
# ponytail: re-hashes changed files on each call; fine for repos git itself handles quickly.
fp(){
  local idx gi ex=()
  idx=$(mktemp); gi=$(git rev-parse --git-path index)
  if [ -f "$gi" ]; then cp "$gi" "$idx"; else rm -f "$idx"; fi
  while IFS= read -r a; do [ -n "$a" ] && ex+=(":(exclude,literal)$a"); done < <(artifacts)
  GIT_INDEX_FILE=$idx git rm -r -q --cached --ignore-unmatch -- .claude >/dev/null 2>&1
  for a in "${ex[@]}"; do GIT_INDEX_FILE=$idx git rm -r -q --cached --ignore-unmatch -- "${a#*)}" >/dev/null 2>&1; done
  GIT_INDEX_FILE=$idx git add -A -- . ':(exclude).claude' "${ex[@]}" >/dev/null 2>&1
  GIT_INDEX_FILE=$idx git write-tree | cut -c1-12
  rm -f "$idx"
}
# Untracked paths right now, directories collapsed — diffed around a run to find what it created.
untracked(){ git ls-files -o --exclude-standard --directory -- . ':(exclude).claude' 2>/dev/null | sort; }

# Case table: | Case | Task | Level | Behaviour | Expected (source) | Command | Repeat |
# Prints: case<TAB>task<TAB>level<TAB>command<TAB>repeat, one line per case row, every tests file.
cases(){
  shopt -s nullglob
  local files=("$TESTS"/*.md)
  [ ${#files[@]} -gt 0 ] || return 0
  awk -F'|' 'NF>=9 {
      for(i=2;i<=8;i++){gsub(/^[ \t]+|[ \t]+$/,"",$i)}
      if ($2=="Case" || $2 ~ /^-+$/) next
      c=$7; gsub(/^`|`$/,"",c)
      printf "%s\t%s\t%s\t%s\t%s\n", $2, $3, $4, c, $8
    }' "${files[@]}"
}

run(){
  local id=$1 row task level cmd rep
  row=$(cases | awk -F'\t' -v c="$id" '$1==c')
  [ -n "$row" ] || { echo "FAIL: case $id is in no $TESTS/*.md row"; exit 1; }
  [ "$(wc -l <<<"$row")" -eq 1 ] || { echo "FAIL: case $id appears twice"; exit 1; }
  IFS=$'\t' read -r _ task level cmd rep <<<"$row"
  case $cmd in ''|'–'|'-') echo "FAIL: case $id has no command (N/A row?)"; exit 1 ;; esac
  [[ $rep =~ ^[0-9]+$ ]] && [ "$rep" -ge 1 ] || rep=1

  local f log i passed=0 code=0 before created
  f=$(fp); log=$(mktemp); before=$(untracked)
  for ((i=1; i<=rep; i++)); do
    bash -c "$cmd" >"$log" 2>&1; code=$?
    [ "$code" -eq 0 ] || break
    passed=$((passed+1))
  done
  created=$(comm -13 <(printf '%s\n' "$before") <(untracked) | jq -Rsc 'split("\n") | map(select(.!=""))')
  local result=fail; [ "$passed" -eq "$rep" ] && result=pass
  jq -nc --arg date "$(date +%Y-%m-%d)" --arg case "$id" --arg task "$task" --arg level "$level" \
    --arg cmd "$cmd" --arg commit "$(git rev-parse --short HEAD 2>/dev/null)" --arg fp "$f" \
    --arg result "$result" --argjson runs "$rep" --argjson passed "$passed" --argjson exit "$code" --argjson artifacts "$created" \
    '{date:$date,case:$case,task:$task,level:$level,cmd:$cmd,commit:($commit|select(.!="")//null),
      fp:$fp,result:$result,runs:$runs,passed:$passed,exit:$exit,artifacts:$artifacts}' >> "$RUNS"
  echo "$result: $id ($level) $passed/$rep — exit $code"
  [ "$created" = "[]" ] || echo "note: the run created $created — recorded as test artifacts, excluded from the fingerprint; gitignore them"
  [ "$result" = pass ] || { echo "--- last output"; tail -30 "$log"; }
  rm -f "$log"
  [ "$result" = pass ]
}

# ponytail: fixed floor for concurrency repeats; make it a per-case column if 20 proves wrong somewhere.
CONCURRENCY_MIN_REPEAT=20

gate(){
  local task=$1 fails=0 cur rows levels
  fail(){ echo "FAIL: $*"; fails=$((fails+1)); }
  cur=$(fp)
  rows=$(cases | awk -F'\t' -v t="$task" '$2==t')
  [ -n "$rows" ] || { echo "FAIL: task $task has no cases — run /clio:test $task"; exit 1; }

  # The plan's Levels cell: "critical · unit, api" or "unit, api".
  local found
  # Each table's header says whether its column 5 is Levels or a pre-4.0 Test command.
  found=$(shopt -s nullglob; awk -F'|' -v t="$task" '
      /^\|/ && $2 ~ /^[ \t]*#[ \t]*$/ {lv = ($5 ~ /Levels/)}
      NF>5 {g=$2; gsub(/^[ \t]+|[ \t]+$/,"",g); if(g==t){print (lv ? "row" : "old") $5; exit}}' "$PLANS"/*.md 2>/dev/null)
  [ -n "$found" ] || { echo "FAIL: task $task is in no $PLANS/*.md row — the gate needs the plan's Levels"; exit 1; }
  [ "${found#old}" = "$found" ] || { echo "FAIL: task $task is a pre-4.0 row (Test column, no Levels) — /clio:plan <area> adds a sub-task that brings it under /clio:test; gate that"; exit 1; }
  levels=${found#row}
  local critical=no; [[ $levels == *critical* ]] && critical=yes
  for l in $(tr ',·' '  ' <<<"${levels//critical/}"); do
    awk -F'\t' -v l="$l" '$3==l && $4!~/^(|–|-)$/' <<<"$rows" | grep -q . \
      || fail "$task: plan requires level '$l', no runnable case covers it"
  done
  [ "$critical" = no ] || awk -F'\t' '$3=="mutation"' <<<"$rows" | grep -q . \
    || fail "$task is critical: a mutation case is required"

  local id level cmd rep last
  while IFS=$'\t' read -r id _ level cmd rep; do
    case $cmd in ''|'–'|'-') continue ;; esac
    [[ $rep =~ ^[0-9]+$ ]] || rep=1
    [ "$level" != concurrency ] || [ "$rep" -ge "$CONCURRENCY_MIN_REPEAT" ] \
      || fail "$id: concurrency case repeats $rep < $CONCURRENCY_MIN_REPEAT"
    last=$(jq -Rc --arg c "$id" 'fromjson? | select(.case==$c)' "$RUNS" | tail -1)
    [ -n "$last" ] || { fail "$id: never run"; continue; }
    jq -e '.result=="pass"' >/dev/null <<<"$last" || { fail "$id: last run failed"; continue; }
    jq -e --arg f "$cur" '.fp==$f' >/dev/null <<<"$last" || fail "$id: code changed since the last pass — re-run (see \`git status --short\`; a test output that is not gitignored counts as code)"
    jq -e --arg c "$cmd" '.cmd==$c' >/dev/null <<<"$last" || fail "$id: command changed since the last pass — re-run"
    jq -e --argjson r "$rep" '.runs>=$r' >/dev/null <<<"$last" || fail "$id: ran fewer times than Repeat $rep"
    # A test never seen failing may pass by construction. Regression must prove it reproduced the bug.
    if ! jq -Rc --arg c "$id" 'fromjson? | select(.case==$c and .result=="fail")' "$RUNS" | grep -q .; then
      if [ "$level" = regression ]; then fail "$id: regression case never failed — it does not reproduce the bug"
      else echo "WARN: $id never seen red"; fi
    fi
  done <<<"$rows"

  [ "$fails" -eq 0 ] && echo "OK: task $task — every case passed at $cur"
  [ "$fails" -eq 0 ]
}

coverage(){
  local task=$1 rows id level cmd last
  rows=$(cases | awk -F'\t' -v t="$task" '$2==t && $4!~/^(|–|-)$/')
  [ -n "$rows" ] || { echo "no cases"; return 0; }
  while IFS=$'\t' read -r id _ level cmd _; do
    last=$(jq -Rr --arg c "$id" 'fromjson? | select(.case==$c) | .result' "$RUNS" | tail -1)
    printf '%s\t%s\t%s\n' "$id" "$level" "${last:-never}"
  done <<<"$rows"
}

case ${1:-} in
  coverage) [ -n "${2:-}" ] || { echo "usage: clio-test.sh coverage <task-id>"; exit 1; }; coverage "$2" ;;
  run)  [ -n "${2:-}" ] || { echo "usage: clio-test.sh run <case-id>"; exit 1; }; run "$2" ;;
  gate) [ -n "${2:-}" ] || { echo "usage: clio-test.sh gate <task-id>"; exit 1; }; gate "$2" ;;
  fp)   fp ;;
  *) echo "usage: clio-test.sh run <case-id> | gate <task-id> | coverage <task-id> | fp"; exit 1 ;;
esac
