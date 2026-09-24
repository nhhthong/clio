#!/usr/bin/env bash
# validate.sh [index|debt|all] — run from anywhere inside a project that has .claude/clio/
#   index  validate the LAST line appended to index.jsonl
#   debt   validate the LAST line appended to debt.jsonl
#   all    repo-wide audit (the "coverage" hop nothing else computes)
# Exit 1 if any FAIL. WARN and INFO never fail the run.
set -uo pipefail

root=$PWD
while [ ! -d "$root/.claude/clio" ] && [ "$root" != "/" ]; do root=$(dirname "$root"); done
[ -d "$root/.claude/clio" ] || { echo "FAIL: no .claude/clio above $PWD"; exit 1; }
cd "$root"
IDX=.claude/clio/database/index.jsonl
DEBT=.claude/clio/database/debt.jsonl
REQ=.claude/clio/docs/specs/requirements.md
fails=0
fail(){ echo "FAIL: $*"; fails=$((fails+1)); }
warn(){ echo "WARN: $*"; }
info(){ echo "INFO: $*"; }

# Every field the schema files say is always present (null / [] allowed, absence is not).
IDX_FIELDS='date id type doc domain plan_tasks files commits keywords req specs'                   # INDEX-IT.md
DEBT_FIELDS='date id kind status domain what req specs docs code action source blocked_by issue'  # DEBT-IT.md, all 14
# ponytail: one global the `all` mode flips to warn. A record written before 2.1 may lack a field;
# the fix is appending a full record under the same key (readers take the last line), so an audit
# names it and moves on, while the write path (`index` / `debt` mode) refuses the line outright.
sev=fail
# `req` holds requirement row numbers as strings: as JSON numbers 7.1 and 7.10 are the same value.
# Write path refuses a number; `all` names pre-4.0 records, which q.sh still reads via tostring.
check_req_type(){ # $1 ledger name, $2 line
  jq -e '(.req // []) | all(type=="string")' >/dev/null 2>&1 <<<"$2" \
    || "$sev" "$1 .req holds a number — write row numbers as strings (\"7.10\", not 7.10)"
}
check_fields(){ # $1 ledger name, $2 field list, $3 line
  local missing
  missing=$(jq -r --arg f "$2" '(($f | split(" ")) - keys) | join(" ")' <<<"$3" 2>/dev/null)
  [ -z "$missing" ] || "$sev" "$1 record is missing: $missing — append a full record, readers take the last line"
}

rows=$([ -f "$REQ" ] && awk -F'|' '/^\|/{gsub(/[ \t]/,"",$2); if($2 ~ /^[0-9]+(\.[0-9]+)*$/) print $2}' "$REQ")
# Same parse over the plan tables: the ids `plan_tasks` is allowed to name. No plan file at all is
# normal (Lite mode, an area nobody planned), and then nothing here can be checked.
shopt -s nullglob
plans=(.claude/clio/docs/plans/*.md)
tasks=$([ ${#plans[@]} -gt 0 ] && awk -F'|' '/^\|/{gsub(/[ \t]/,"",$2); if($2 ~ /^[0-9]+(\.[0-9]+)*$/) print $2}' "${plans[@]}")

check_req(){   # $1 ledger name, $2 line
  while read -r n; do
    [ -z "$n" ] && continue
    printf '%s\n' "$rows" | grep -qx "$n" || fail "$1 .req $n has no requirements.md row"
  done < <(jq -r '.req[]?' <<<"$2")
}
check_plan_tasks(){ # $2 line — an id naming no plan row sends /clio:memo to tick the wrong one
  [ -n "$tasks" ] || return 0
  while read -r t; do
    [ -z "$t" ] && continue
    printf '%s\n' "$tasks" | grep -qx "$t" || fail "$1 .plan_tasks $t is in no .claude/clio/docs/plans/*.md row"
  done < <(jq -r '.plan_tasks[]?' <<<"$2")
}
check_specs(){ # $1 ledger name, $2 line
  while read -r p; do [ -z "$p" ] || [ -f "$p" ] || fail "$1 .specs missing: $p"; done < <(jq -r '.specs[]?' <<<"$2")
}

check_index_line(){
  local line=$1
  jq -e '.date and .doc and ((.keywords|length)>0) and (.type|IN("task","adr"))
         and (.files|type=="array") and (.commits|type=="array")
         and (.req|type=="array") and (.specs|type=="array")
         and ((.plan_tasks|type=="array") or (has("plan_tasks")|not))' >/dev/null 2>&1 <<<"$line" \
    || { fail "index line missing a required field, bad type, or not valid JSON"; return 1; }
  check_fields index "$IDX_FIELDS" "$line"; check_req_type index "$line"
  local doc; doc=$(jq -r .doc <<<"$line")
  # A migrated doc leaves its pre-3.0 records keyed on the old path, which is now gone. `all` mode's
  # own sweep reports those as INFO once it finds the record that supersedes them — so only FAIL
  # here when nothing does. `idxjson` is unset in `index` mode, so the write path stays strict.
  if [ ! -f "$doc" ]; then
    jq -e --arg d "$doc" 'select(.supersedes==$d)' <<<"${idxjson:-}" >/dev/null 2>&1 \
      || fail "index .doc points at a missing file: $doc"
  fi
  # `id` is the doc's creation timestamp AND its filename prefix (INDEX-IT.md). Enforcing the
  # binding is what stops two docs sharing one id: a collision leaves the losing file on disk with
  # no record of its own, which the orphan check below then names. Only for the two directories
  # whose filenames Clio chooses — a ledger may also index a spec or a rules file, and those are
  # named by content.
  local id; id=$(jq -r '.id // empty' <<<"$line")
  case $doc in
    .claude/clio/docs/tasks/*|.claude/clio/docs/decisions/*)
      [ -z "$id" ] || case ${doc##*/} in "${id}_"*) ;;
        *) fail "index .id $id is not the filename prefix of $doc" ;; esac ;;
  esac
  check_specs index "$line"; check_req index "$line"; check_plan_tasks index "$line"
}

check_debt_line(){
  local line=$1
  jq -e '.id and (.what|length>0)
         and (.kind|IN("code-debt","unverified","doc-stale","spec-delta","spec-blocked"))
         and (.status|IN("pending","in-process","done"))
         and (.req|type=="array") and (.specs|type=="array") and (.code|type=="array")
         and has("blocked_by")' >/dev/null 2>&1 <<<"$line" \
    || { fail "debt line missing a required field, bad kind/status, or not valid JSON"; return 1; }
  check_fields debt "$DEBT_FIELDS" "$line"; check_req_type debt "$line"
  check_specs debt "$line"; check_req debt "$line"
}

# The record that FILES a spec-blocked must name its blocker; a later record may legitimately null
# it once the answer lands (DEBT-IT.md § 1). So the rule is judged on each id's FIRST record, never
# its last — one jq, called by both modes, so `all` cannot report the same id twice.
check_filed_blocked(){   # $1 debt json stream, $2 a single id, or "" for every id
  while read -r id; do
    [ -n "$id" ] && fail "debt $id: the record that files a spec-blocked needs a non-null blocked_by"
  done < <(jq -s -r --arg only "${2:-}" 'group_by(.id)[]
    | select($only == "" or .[0].id == $only)
    | select(.[0].kind == "spec-blocked" and .[0].blocked_by == null) | .[0].id' <<<"$1")
}

mode=${1:-all}
case $mode in
  index) [ -s "$IDX" ]  || { echo "FAIL: $IDX is empty"; exit 1; }
    last=$(tail -1 "$IDX")
    if check_index_line "$last"; then
      jq -e '.type=="task" and (.files|length)==0' >/dev/null 2>&1 <<<"$last" && warn "index .files is empty — a task doc with no source files?"
    fi ;;
  debt) [ -s "$DEBT" ] || { echo "FAIL: $DEBT is empty"; exit 1; }
    last=$(tail -1 "$DEBT")
    check_debt_line "$last"
    check_filed_blocked "$(jq -Rc 'fromjson? // empty' "$DEBT" 2>/dev/null)" "$(jq -r '.id // empty' <<<"$last" 2>/dev/null)" ;;
  all)
    for f in "$IDX" "$DEBT"; do
      [ -f "$f" ] || { fail "missing $f"; continue; }
      n=0; while IFS= read -r l; do n=$((n+1))
        [ -z "$l" ] && continue
        jq -e . >/dev/null 2>&1 <<<"$l" || fail "$f line $n is not valid JSON"
      done < "$f"
    done
    # jq reading a file whole aborts at the first malformed line (already FAILed above) and its
    # non-zero exit then misfires every check below. ponytail: fromjson? keeps the parseable lines.
    idxjson=$(jq -Rc 'fromjson? // empty' "$IDX" 2>/dev/null)
    debtjson=$(jq -Rc 'fromjson? // empty' "$DEBT" 2>/dev/null)

    sev=warn    # audit: a pre-2.1 record missing a field is named, not failed (see check_fields)
    # One group per document, across the 3.0 id migration. Pre-3.0 records have no `id` and key on
    # their path, so without the bridge below they form a second group whose last record is the old
    # short one — and a finished migration would keep reporting the very fields it just supplied.
    # The bridge maps a path to the id that later claimed it, by `doc` (the doc stayed put) or by
    # `supersedes` (it moved), so the legacy records land in their successor's group and `last`
    # picks the complete record.
    group_by_doc_id='
      (map(select(.id) | {key: .doc, value: .id})
       + map(select(.id and .supersedes) | {key: .supersedes, value: .id}) | from_entries) as $m
      | group_by(.id // $m[.doc] // .doc)'
    [ -n "$idxjson" ] && while IFS= read -r l; do [ -n "$l" ] && check_index_line "$l"; done \
      < <(jq -s -c "$group_by_doc_id"' | .[] | last' <<<"$idxjson")
    [ -n "$debtjson" ] && while IFS= read -r l; do [ -n "$l" ] && check_debt_line "$l"; done \
      < <(jq -s -c 'group_by(.id)[] | last' <<<"$debtjson")

    check_filed_blocked "$debtjson"

    # 2.0: a doc's last record is its full state — it must still name every file an earlier record had.
    # Only pre-2.0 records (scalar `commit`, or no `commits`) need migrating; a clean 2.0 doc may
    # legitimately drop a reverted file (INDEX-IT.md § files), so don't nag about that.
    while read -r d; do
      [ -n "$d" ] && warn "index: last record of $d drops files earlier records had — pre-2.0 delta ledger? migrate per CHANGELOG 2.0.0"
    done < <(jq -s -r "$group_by_doc_id"' | .[] | select(length>1)
      | select(any(.[]; has("commit") or (has("commits")|not)))
      | select((((map(.files[]?))|unique) - (last|.files // [])) | length>0) | .[0].doc' <<<"$idxjson")

    # orphan docs — on disk, never indexed. globstar: task docs live in tasks/<feature>/ since 3.0,
    # and a non-recursive glob would make every one of them invisible to this check.
    shopt -s globstar nullglob
    for d in .claude/clio/docs/tasks/**/*.md .claude/clio/docs/decisions/**/*.md; do
      [ -e "$d" ] || continue
      [ "${d##*/}" = summary.md ] && continue          # feature-level blurb, never an indexed doc
      jq -e --arg d "$d" 'select(.doc==$d)' <<<"$idxjson" >/dev/null 2>&1 || warn "orphan doc, no index record: $d — /clio:memo was skipped"
    done
    # index records pointing at docs that no longer exist without a supersedes trail
    while read -r doc; do
      [ -z "$doc" ] && continue
      [ -f "$doc" ] && continue
      jq -e --arg d "$doc" 'select(.supersedes==$d)' <<<"$idxjson" >/dev/null 2>&1 \
        && info "renamed doc, superseded: $doc" \
        || fail "index record points at a missing doc and nothing supersedes it: $doc"
    done < <(jq -r '.doc' <<<"$idxjson" 2>/dev/null | sort -u)
    # One id, one row. A re-plan supersedes an unticked row *in place*; appending a second row with
    # the same id instead leaves two, and `Done` then depends on which one a reader hits first.
    for pl in .claude/clio/docs/plans/*.md; do
      [ -e "$pl" ] || continue
      while read -r dup; do
        [ -n "$dup" ] && fail "$pl has task id $dup twice — supersede a row in place, never append a copy"
      done < <(awk -F'|' 'NF>5 && $2 ~ /^ *[0-9]+(\.[0-9]+)* *$/ {gsub(/^ +| +$/,"",$2); print $2}' "$pl" | sort | uniq -d)
    done

    # A pre-4.0 table (Test column) with no table in today's format after it: never re-planned, so its
    # ticked rows were never brought under /clio:test and the gate refuses its unticked ones.
    for pl in .claude/clio/docs/plans/*.md; do
      [ -e "$pl" ] || continue
      grep -qE '^\| *# *\|.*\| *Test' "$pl" && ! grep -qE '^\| *# *\|.*\| *Levels *\|' "$pl" \
        && warn "$pl is a pre-4.0 plan (Test column) — /clio:plan re-plans it into sub-tasks"
    done
    # Test cases: one id, one row — clio-test.sh refuses to run a duplicated id, say so before it does.
    for tf in .claude/clio/docs/tests/*.md; do
      [ -e "$tf" ] || continue
      while read -r dup; do
        [ -n "$dup" ] && fail "$tf has case id $dup twice"
      done < <(awk -F'|' 'NF>=9 {g=$2; gsub(/^[ \t]+|[ \t]+$/,"",g); if(g!="Case" && g !~ /^-+$/) print g}' "$tf" | sort | uniq -d)
    done
    RUNS=.claude/clio/database/runs.jsonl
    if [ -f "$RUNS" ]; then
      n=0; while IFS= read -r l; do n=$((n+1))
        [ -z "$l" ] || jq -e '.case and .fp and (.result|IN("pass","fail"))' >/dev/null 2>&1 <<<"$l" \
          || fail "$RUNS line $n is not a clio-test.sh record — only the script writes this file"
      done < "$RUNS"
    else
      warn "missing $RUNS — /clio:test has nowhere to record evidence"
    fi

    # A plan task's `req` column, against requirements.md — the same rule check_req applies to a
    # ledger record, applied to the other file that carries req numbers.
    # Not checked here: which decided rows have no plan task. `plan` gives a ⚠️/❌ row a placeholder
    # line naming the debt it waits on, so "a plan row exists for an undecided row" is the correct
    # state, not a finding; and "✅ with no plan task" overlaps the ✅-with-no-index-record INFO below.
    if [ -f "$REQ" ] && compgen -G '.claude/clio/docs/plans/*.md' >/dev/null; then
      planreq=$(awk -F'|' 'NF>5 && $2 ~ /^ *[0-9]+(\.[0-9]+)* *$/ {
        n=split($4,a,","); for(i=1;i<=n;i++){gsub(/^ +| +$/,"",a[i]); if(a[i] ~ /^[0-9]/) print a[i]}
      }' .claude/clio/docs/plans/*.md | sort -u)
      while read -r n; do
        [ -z "$n" ] && continue
        printf '%s\n' "$rows" | grep -qx "$n" \
          || fail "a plan task claims req $n, which requirements.md has no row for"
      done <<<"$planreq"
    fi

    # A spec-delta says the spec moved and the code has not followed. /clio:plan turns one into a
    # task carrying its id, so an open delta named in no plan means no plan absorbed it — and that
    # is silent: every later session reads a plan that no longer matches the decision.
    shopt -s nullglob
    if compgen -G '.claude/clio/docs/plans/*.md' >/dev/null; then
      while read -r id; do
        [ -z "$id" ] && continue
        grep -qrF -- "$id" .claude/clio/docs/plans/ \
          || warn "spec-delta $id is in no plan — /clio:plan <area> absorbs it as a task"
      done < <(jq -s -r 'group_by(.id)[] | last
        | select(.kind=="spec-delta" and .status!="done" and .blocked_by==null) | .id' <<<"$debtjson")
    fi

    # Links inside a document's prose. `.doc` and `.specs` are fields and already checked; a path
    # written into a sentence is not, and moving a doc is exactly what breaks those.
    # Markdown only: a ledger is append-only, so its older records name the old path on purpose and
    # rewriting them would be the actual bug. Skip a path holding `<` — a template placeholder.
    while IFS= read -r ref; do
      [ -z "$ref" ] && continue
      case $ref in *'<'*) continue ;; esac
      [ -e "$ref" ] || warn "dead link in a document: $ref — was it renamed? rewrite the reference"
    done < <(grep -rhoE --include='*.md' '\.claude/[A-Za-z0-9._/-]+\.md' .claude/clio/ .claude/rules/ 2>/dev/null | sort -u)

    # requirements.md markers vs the ledgers
    if [ -f "$REQ" ]; then
      while IFS='|' read -r _ num _ _ status _; do
        num=$(echo "$num" | tr -d ' \t'); status=$(echo "$status" | tr -d ' \t')
        case $num in ''|*[!0-9.]*) continue ;; esac
        case $status in
          *⚠*|*❌*)
            jq -s -e --arg n "$num" 'map(select(.req != null))
              | group_by(.id)[] | last | select((.req[]?|tostring) == $n and .status!="done")' \
              >/dev/null 2>&1 <<< "$debtjson" || warn "requirements.md row $num is ⚠️/❌ but no open debt record tracks it" ;;
          *✅*)
            jq -s -e --arg n "$num" 'any(.[]; (.req[]?|tostring) == $n)' >/dev/null 2>&1 <<<"$idxjson" \
              || info "requirements.md row $num is ✅ (decided) with no index record — decided but not built" ;;
        esac
      done < "$REQ"
    fi
    ;;
  *) echo "usage: validate.sh [index|debt|all]"; exit 1 ;;
esac

[ "$fails" -eq 0 ] && echo "OK ($mode)"
exit $((fails > 0 ? 1 : 0))
