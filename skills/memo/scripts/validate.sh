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
IDX=.claude/clio/index.jsonl
DEBT=.claude/clio/debt.jsonl
REQ=.claude/docs/specs/requirements.md
fails=0
fail(){ echo "FAIL: $*"; fails=$((fails+1)); }
warn(){ echo "WARN: $*"; }
info(){ echo "INFO: $*"; }

rows=$([ -f "$REQ" ] && awk -F'|' '/^\|/{gsub(/[ \t]/,"",$2); if($2 ~ /^[0-9]+(\.[0-9]+)*$/) print $2}' "$REQ")

check_req(){   # $1 ledger name, $2 line
  while read -r n; do
    [ -z "$n" ] && continue
    printf '%s\n' "$rows" | grep -qx "$n" || fail "$1 .req $n has no requirements.md row"
  done < <(jq -r '.req[]?' <<<"$2")
}
check_specs(){ # $1 ledger name, $2 line
  while read -r p; do [ -z "$p" ] || [ -f "$p" ] || fail "$1 .specs missing: $p"; done < <(jq -r '.specs[]?' <<<"$2")
}

check_index_line(){
  local line=$1
  jq -e '.date and .doc and ((.keywords|length)>0) and (.type|IN("task","adr"))
         and (.files|type=="array") and (.commits|type=="array")
         and (.req|type=="array") and (.specs|type=="array")' >/dev/null 2>&1 <<<"$line" \
    || { fail "index line missing a required field, bad type, or not valid JSON"; return 1; }
  local doc; doc=$(jq -r .doc <<<"$line")
  [ -f "$doc" ] || fail "index .doc points at a missing file: $doc"
  check_specs index "$line"; check_req index "$line"
}

check_debt_line(){
  local line=$1
  jq -e '.id and (.what|length>0)
         and (.kind|IN("code-debt","unverified","doc-stale","spec-delta","spec-blocked"))
         and (.status|IN("pending","in-process","done"))
         and (.req|type=="array") and (.specs|type=="array") and (.code|type=="array")
         and has("blocked_by")' >/dev/null 2>&1 <<<"$line" \
    || { fail "debt line missing a required field, bad kind/status, or not valid JSON"; return 1; }
  # spec-blocked must name its blocker when filed, but a later line may null it once unblocked
  # (DEBT-IT.md § 1) — so that check is group-aware and lives in `all`, not here.
  check_specs debt "$line"; check_req debt "$line"
}

mode=${1:-all}
case $mode in
  index) [ -s "$IDX" ]  || { echo "FAIL: $IDX is empty"; exit 1; }
    last=$(tail -1 "$IDX")
    if check_index_line "$last"; then
      jq -e '.type=="task" and (.files|length)==0' >/dev/null 2>&1 <<<"$last" && warn "index .files is empty — a task doc with no source files?"
    fi ;;
  debt)  [ -s "$DEBT" ] || { echo "FAIL: $DEBT is empty"; exit 1; }; check_debt_line "$(tail -1 "$DEBT")" ;;
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

    [ -n "$idxjson" ] && while IFS= read -r l; do [ -n "$l" ] && check_index_line "$l"; done \
      < <(jq -s -c 'group_by(.doc)[] | last' <<<"$idxjson")
    [ -n "$debtjson" ] && while IFS= read -r l; do [ -n "$l" ] && check_debt_line "$l"; done \
      < <(jq -s -c 'group_by(.id)[] | last' <<<"$debtjson")

    # a spec-blocked id must name its blocker on the record that FILES it; a later line legitimately
    # nulls blocked_by once the answer lands (DEBT-IT.md § 1), so judge the first record, not the last
    while read -r id; do
      [ -n "$id" ] && fail "debt $id: first spec-blocked record has a null blocked_by"
    done < <(jq -s -r 'group_by(.id)[] | select(.[0].kind=="spec-blocked" and .[0].blocked_by==null) | .[0].id' <<<"$debtjson")

    # 2.0: a doc's last record is its full state — it must still name every file an earlier record had.
    # Only pre-2.0 records (scalar `commit`, or no `commits`) need migrating; a clean 2.0 doc may
    # legitimately drop a reverted file (INDEX-IT.md § files), so don't nag about that.
    while read -r d; do
      [ -n "$d" ] && warn "index: last record of $d drops files earlier records had — pre-2.0 delta ledger? migrate per CHANGELOG 2.0.0"
    done < <(jq -s -r 'group_by(.doc)[] | select(length>1)
      | select(any(.[]; has("commit") or (has("commits")|not)))
      | select((((map(.files[]?))|unique) - (last|.files // [])) | length>0) | .[0].doc' <<<"$idxjson")

    # orphan docs — on disk, never indexed
    for d in .claude/docs/tasks/*.md .claude/docs/decisions/*.md; do
      [ -e "$d" ] || continue
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
    for f in .claude/CONTEXT.md .claude/CLAUDE.md CLAUDE.md; do
      grep -q '<!--' "$f" 2>/dev/null && warn "$f still has HTML comments — it loads every session, delete them"
    done
    # requirements.md markers vs the ledgers
    if [ -f "$REQ" ]; then
      while IFS='|' read -r _ num _ _ status _; do
        num=$(echo "$num" | tr -d ' \t'); status=$(echo "$status" | tr -d ' \t')
        case $num in ''|*[!0-9.]*) continue ;; esac
        case $status in
          *⚠*|*❌*)
            jq -s -e --arg n "$num" 'map(select(.req != null))
              | group_by(.id)[] | last | select((.req[]?|tostring) == $n and .status!="done")' \
              >/dev/null 2>&1 < "$DEBT" || warn "requirements.md row $num is ⚠️/❌ but no open debt record tracks it" ;;
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
