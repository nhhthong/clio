#!/usr/bin/env bash
# .claude/clio/validate.sh [index|debt|all]
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

routes_rows(){
  [ -f "$REQ" ] || return 0
  awk -F'|' '/^\|/{gsub(/[ \t]/,"",$2);
    if($2 ~ /^[0-9]+(\.[0-9]+)*(–[0-9]+(\.[0-9]+)*)?$/){
      n=split($2,a,"–");
      if(n==1) print a[1];
      else if(a[1] !~ /\./ && a[2] !~ /\./) { for(i=a[1];i<=a[2];i++) print i }
      else { print a[1]; print a[2] }}}' "$REQ"
}

check_index_line(){
  local line=$1
  jq -e '.date and .type and .doc and ((.keywords|length)>0)
         and (.req|type=="array") and (.specs|type=="array")' >/dev/null 2>&1 <<<"$line" \
    || { fail "index line missing a required field or not valid JSON"; return; }
  local doc; doc=$(jq -r .doc <<<"$line")
  [ -f "$doc" ] || fail "index .doc points at a missing file: $doc"
  while read -r p; do [ -z "$p" ] || [ -f "$p" ] || fail "index .specs missing: $p"; done \
    < <(jq -r '.specs[]?' <<<"$line")
  local rows; rows=$(routes_rows)
  while read -r n; do
    [ -z "$n" ] && continue
    printf '%s\n' "$rows" | grep -qx "$n" || fail "index .req $n has no requirements.md row"
  done < <(jq -r '.req[]?' <<<"$line")
  [ "$(jq -r '(.files|length) // 0' <<<"$line")" -eq 0 ] && warn "index .files is empty — docs-only run?"
  return 0
}

check_debt_line(){
  local line=$1
  jq -e '.id and .kind and .status and (.what|length>0)
         and (.req|type=="array") and (.specs|type=="array") and (.code|type=="array")
         and has("blocked_by")' >/dev/null 2>&1 <<<"$line" \
    || { fail "debt line missing a required field or not valid JSON"; return; }
  while read -r p; do [ -z "$p" ] || [ -f "$p" ] || fail "debt .specs missing: $p"; done \
    < <(jq -r '.specs[]?' <<<"$line")
  return 0
}

mode=${1:-all}
case $mode in
  index) [ -s "$IDX" ]  || { echo "FAIL: $IDX is empty"; exit 1; }; check_index_line "$(tail -1 "$IDX")" ;;
  debt)  [ -s "$DEBT" ] || { echo "FAIL: $DEBT is empty"; exit 1; }; check_debt_line "$(tail -1 "$DEBT")" ;;
  all)
    for f in "$IDX" "$DEBT"; do
      [ -f "$f" ] || { fail "missing $f"; continue; }
      n=0; while IFS= read -r l; do n=$((n+1))
        [ -z "$l" ] && continue
        jq -e . >/dev/null 2>&1 <<<"$l" || fail "$f line $n is not valid JSON"
      done < "$f"
    done
    [ -s "$IDX" ] && while IFS= read -r l; do [ -n "$l" ] && check_index_line "$l"; done \
      < <(jq -s -c 'group_by(.doc)[] | last' "$IDX" 2>/dev/null)
    [ -s "$DEBT" ] && while IFS= read -r l; do [ -n "$l" ] && check_debt_line "$l"; done \
      < <(jq -s -c 'group_by(.id)[] | last' "$DEBT" 2>/dev/null)

    # orphan docs — on disk, never indexed
    for d in .claude/docs/tasks/*.md .claude/docs/decisions/*.md; do
      [ -e "$d" ] || continue
      grep -qF "\"doc\":\"$d\"" "$IDX" 2>/dev/null || warn "orphan doc, no index record: $d — /clio:memo was skipped"
    done
    # index records pointing at docs that no longer exist without a supersedes trail
    while read -r doc; do
      [ -z "$doc" ] && continue
      [ -f "$doc" ] && continue
      grep -qF "\"supersedes\":\"$doc\"" "$IDX" 2>/dev/null \
        && info "renamed doc, superseded: $doc" \
        || fail "index record points at a missing doc and nothing supersedes it: $doc"
    done < <(jq -r '.doc' "$IDX" 2>/dev/null | sort -u)
    # every-session line budget: CLAUDE.md + CONTEXT.md after HTML-comment strip
    budget=0
    for f in .claude/CLAUDE.md .claude/CONTEXT.md; do
      [ -f "$f" ] || continue
      if command -v perl >/dev/null 2>&1; then n=$(perl -0pe 's/<!--.*?-->//gs' "$f" | grep -c . || true)
      else n=$(grep -c . "$f" || true); fi
      budget=$((budget + n))
    done
    [ "$budget" -gt 150 ] && warn "CLAUDE.md + CONTEXT.md load every session: $budget non-blank lines, budget ~150 — move path-specific parts into .claude/rules/ with paths: frontmatter"
    grep -q '<!--' .claude/CONTEXT.md 2>/dev/null && warn "CONTEXT.md still has HTML comments — they are imported into context, delete them"
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
            grep -q "\"req\":\[[^]]*$num" "$IDX" 2>/dev/null \
              || info "requirements.md row $num is ✅ (decided) with no index record — decided but not built" ;;
        esac
      done < "$REQ"
    fi
    ;;
  *) echo "usage: validate.sh [index|debt|all]"; exit 1 ;;
esac

[ "$fails" -eq 0 ] && echo "OK ($mode)"
exit $((fails > 0 ? 1 : 0))
