#!/usr/bin/env bash
# clio-test.sh run <case-id> | approve <task-id> | gate <task-id> | coverage <task-id> | fp
#   run       run one case from .claude/clio/docs/tests/*.md `Repeat` times, append the result to runs.jsonl
#   approve   record the hash of a task's case rows once the user approved them; the gate holds the table to it
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

root=$PWD
while [ ! -d "$root/.claude/clio" ] && [ "$root" != "/" ]; do root=$(dirname "$root"); done
[ -d "$root/.claude/clio" ] || { echo "FAIL: no .claude/clio above $PWD"; exit 1; }
cd "$root"
git rev-parse --git-dir >/dev/null 2>&1 || { echo "FAIL: clio-test needs a git repository — evidence is bound to the working tree"; exit 1; }
RUNS=.claude/clio/database/runs.jsonl
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
fp(){
  local idx gi ex=()
  idx=$(mktemp); gi=$(git rev-parse --git-path index)
  if [ -f "$gi" ]; then cp "$gi" "$idx"; else rm -f "$idx"; fi
  while IFS= read -r a; do [ -n "$a" ] && ex+=(":(exclude,literal)$a"); done < <(artifacts)
  # -f: without it git refuses a path staged and then edited again (a ledger mid-memo), silently
  # leaving its staged copy in the tree — every later `git add` of that ledger then moves the fp.
  GIT_INDEX_FILE=$idx git rm -r -q -f --cached --ignore-unmatch -- .claude >/dev/null 2>&1
  for a in "${ex[@]}"; do GIT_INDEX_FILE=$idx git rm -r -q -f --cached --ignore-unmatch -- "${a#*)}" >/dev/null 2>&1; done
  GIT_INDEX_FILE=$idx git add -A -- . ':(exclude).claude' "${ex[@]}" >/dev/null 2>&1
  GIT_INDEX_FILE=$idx git write-tree | cut -c1-12
  rm -f "$idx"
}
# Untracked files right now — diffed around a run to find what it created. Files, not directories:
# excluding a whole new directory would hide code written into it after the run.
# ponytail: a run that emits thousands of non-ignored files makes a long exclude list; gitignore them.
untracked(){ git ls-files -o --exclude-standard -- . ':(exclude).claude' 2>/dev/null | sort; }

# awk prelude: skip lines inside <!-- … --> — a table commented out is not a table.
NOCOMMENT='/<!--/ {incom=1} incom { if (/-->/) incom=0; next }'

# The only level names a plan or a case may use — LEVELS.md's catalog, lowercase.
LEVELS="unit integration api contract e2e idempotency concurrency security resilience perf load stress regression smoke mutation"

# Case table, current: | Case | Task | Level | Covers | Behaviour | Expected (source) | Command | Repeat |
# Case table, pre-4.1 (no Covers column, accepted unchanged — its rows just carry no id to enforce):
#   | Case | Task | Level | Behaviour | Expected (source) | Command | Repeat |
# Prints: case<TAB>task<TAB>level<TAB>covers<TAB>command<TAB>repeat<TAB>tracked<TAB>error, one line
# per case row, every tests file. tracked is 1 for a Covers-column row, 0 for a pre-4.1 one — the
# id-coverage check in gate() only ever counts a tracked row's Covers cell. error is empty for a
# well-formed row; a malformed one is still printed, so the case it belongs to fails loudly instead
# of running a truncated command.
cases(){
  shopt -s nullglob
  local files=("$TESTS"/*.md)
  [ ${#files[@]} -gt 0 ] || return 0
  awk -F'|' -v lv=" $LEVELS " "$NOCOMMENT"'
    /^[ \t]*\|/ {
      for(i=2;i<NF;i++){gsub(/^[ \t]+|[ \t]+$/,"",$i)}
      if ($2=="Case" || $2 ~ /^[-: ]+$/) next
      e=""; trk=1; cov=""; c=""; rep=""   # reset every row: an unset global here would leak
      if (NF==9)      { trk=0; c=$7; rep=$8 }                    # the previous row value forward
      else if (NF==10) { cov=$5; c=$8; rep=$9 }
      else e=sprintf("the row splits into %d cells, not 7 (pre-4.1) or 8 — a `|` in the command? wrap it in a script", NF-2)
      if (e=="") {
        gsub(/^`|`$/,"",c); na=(c ~ /^(|–|-)$/)
        if (index(lv, " " $4 " ")==0) e="level " $4 " is not one of: " substr(lv,2,length(lv)-2)
        else if (!na && (rep !~ /^[0-9]+$/ || rep+0<1)) e="Repeat " rep " is not a whole number >= 1"
      }
      printf "%s\t%s\t%s\t%s\t%s\t%s\t%d\t%s\n", z($2), z($3), z($4), z(cov), z(c), z(rep), trk, e
    }
    function z(x){ return x=="" ? "–" : x }   # read collapses empty tab fields; keep every cell' "${files[@]}"
}

# All `level.n` ids LEVELS.md's catalog names for a level — the risks a named level must cover or
# excuse. A level whose bullets carry no id (regression, smoke, mutation — each has its own gate
# rule already) returns nothing, which is how gate() knows to skip the check entirely for it.
level_ids(){ grep -oE "\`$1\.[0-9]+\`" "$LEVELS_FILE" 2>/dev/null | tr -d '`' | sort -u; }

# `- <task> · <level.n> — <reason>` lines from every tests file: the bullet-scoped Not applicable
# list § test/SKILL.md § 3 describes, for one task. `·` is multi-byte; tr's SET2 padding (as the
# Levels-cell parsing above already relies on) turns each of its bytes into a space on its own.
excused_ids(){
  local t=$1
  shopt -s nullglob; local files=("$TESTS"/*.md)
  [ ${#files[@]} -gt 0 ] || return 0
  awk "$NOCOMMENT"'/^-[ \t]*[^ \t]/' "${files[@]}" | tr '·' ' ' | sed -E 's/^-[ \t]*//' \
    | while read -r ln_task ln_id _; do [ "$ln_task" = "$t" ] && echo "$ln_id"; done
}

run(){
  local id=$1 row task level covers cmd rep trk
  row=$(cases | awk -F'\t' -v c="$id" '$1==c')
  [ -n "$row" ] || { echo "FAIL: case $id is in no $TESTS/*.md row"; exit 1; }
  [ "$(wc -l <<<"$row")" -eq 1 ] || { echo "FAIL: case $id appears twice"; exit 1; }
  IFS=$'\t' read -r _ task level covers cmd rep trk err <<<"$row"
  [ -z "$err" ] || { echo "FAIL: case $id: $err"; exit 1; }
  case $cmd in ''|'–'|'-') echo "FAIL: case $id has no command (N/A row?)"; exit 1 ;; esac

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
# LEVELS.md's mutation default; override per project with `NN%` on the `Mutation:` line in plans/infra.md.
MUTATION_MIN_THRESHOLD=80

# The task's case rows as written, whitespace-normalised: what the user approved.
table_hash(){
  shopt -s nullglob
  local files=("$TESTS"/*.md)
  [ ${#files[@]} -gt 0 ] || { echo none; return; }
  awk -F'|' -v t="$1" "$NOCOMMENT"'
    /^[ \t]*\|/ {g=$3; gsub(/^[ \t]+|[ \t]+$/,"",g); if(g==t){gsub(/[ \t]+/," "); print}}' "${files[@]}" \
    | git hash-object --stdin | cut -c1-12
}

approve(){
  local task=$1
  cases | awk -F'\t' -v t="$task" '$2==t' | grep -q . || { echo "FAIL: task $task has no case rows to approve"; exit 1; }
  jq -nc --arg date "$(date +%Y-%m-%d)" --arg task "$task" --arg hash "$(table_hash "$task")" \
    '{date:$date,approve:$task,hash:$hash}' >> "$RUNS"
  echo "approved: task $task case table $(table_hash "$task")"
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
  # Each table's header says whether its column 5 is Levels or a pre-4.0 Test command.
  found=$(shopt -s nullglob; awk -F'|' -v t="$task" "$NOCOMMENT"'
      /^\|/ && $2 ~ /^[ \t]*#[ \t]*$/ {lv = ($5 ~ /Levels/)}
      NF>5 {g=$2; gsub(/^[ \t]+|[ \t]+$/,"",g); if(g==t){print (lv ? "row" : "old") "\t" $(NF-1) "\t" $5; exit}}' "$PLANS"/*.md 2>/dev/null)
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
      # written as 0, or left out, always exits 0 too. Biggest 1-3 digit number in the command text:
      # not proof the tool honors it, only that the "set threshold to 0" cheat leaves no number to find.
      m=$(grep -oE '[0-9]{1,3}' <<<"$cmd" | awk 'BEGIN{x=0} {if($1+0<=100 && $1+0>x) x=$1+0} END{print x}')
      [ "$m" -ge "$mutation_req" ] || fail "$id: mutation command shows no threshold >= ${mutation_req}% — looks cheatable (e.g. --thresholds.break 0); default is $MUTATION_MIN_THRESHOLD, override with \`NN%\` on the \`Mutation:\` line in plans/infra.md"
    fi
    last=$(jq -Rc --arg c "$id" 'fromjson? | select(.case==$c)' "$RUNS" | tail -1)
    [ -n "$last" ] || { fail "$id: never run"; continue; }
    jq -e '.result=="pass"' >/dev/null <<<"$last" || { fail "$id: last run failed"; continue; }
    jq -e --arg f "$cur" '.fp==$f' >/dev/null <<<"$last" || fail "$id: code changed since the last pass — re-run (see \`git status --short\`; a test output that is not gitignored counts as code)"
    jq -e --arg c "$cmd" '.cmd==$c' >/dev/null <<<"$last" || fail "$id: command changed since the last pass — re-run"
    jq -e --argjson r "$rep" '.runs>=$r' >/dev/null <<<"$last" || fail "$id: ran fewer times than Repeat $rep"
    # Only runs of this command count, in file order (runs.jsonl is append-only).
    #   flaky — it failed on this very code after passing on it: same fp, both results.
    #   red   — it failed on other code before a pass on this code: the case can tell them apart.
    # ponytail: a fail at this fp *before* its first pass is forgiven (a DB not yet up); a real flake
    # that happens to fail first slips through — Repeat is what catches those.
    read -r flaky red < <(jq -Rn --arg c "$id" --arg f "$cur" --arg m "$cmd" -r '
      [inputs | fromjson? | select(.case==$c and .cmd==$m)] | to_entries as $r
      | ([$r[] | select(.value.fp==$f and .value.result=="pass") | .key]) as $p
      | [ ($p|length>0) and any($r[]; .key>$p[0] and .value.fp==$f and .value.result=="fail"),
          ($p|length>0) and any($r[]; .key<$p[-1] and .value.fp!=$f and .value.result=="fail") ]
      | "\(.[0]) \(.[1])"' "$RUNS")
    [ "$flaky" = false ] || fail "$id: flaky — failed on this code after passing on it; /clio:memo files it as code-debt \`flaky:\`"
    if [ "$red" = false ]; then
      # A test never seen failing may pass by construction. Regression must prove it reproduced the bug;
      # on a critical task every case must. A mutation case is exempt: its red is a score below threshold.
      if [ "$level" = regression ]; then fail "$id: regression case never failed, with this command, on code before the fix — it does not reproduce the bug"
      elif [ "$level" = mutation ]; then :
      elif [ "$critical" = yes ]; then
        fail "$id: never seen red on a critical task — break the code once on purpose and re-run it"
      else echo "WARN: $id never seen red"; fi
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
  approve) [ -n "${2:-}" ] || { echo "usage: clio-test.sh approve <task-id>"; exit 1; }; approve "$2" ;;
  gate) [ -n "${2:-}" ] || { echo "usage: clio-test.sh gate <task-id>"; exit 1; }; gate "$2" ;;
  fp)   fp ;;
  *) echo "usage: clio-test.sh run <case-id> | approve <task-id> | gate <task-id> | coverage <task-id> | fp"; exit 1 ;;
esac
