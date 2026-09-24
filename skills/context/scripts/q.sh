#!/usr/bin/env bash
# q.sh — every read of Clio's ledgers, in one place. Read-only.
#   summary                                   plans done/open + next task, debt queue/blocked, last memo
#   built  [--req R --spec S --file F --area A --keyword K --task T --id I]   current state per doc
#   owed   [--req R --spec S --area A --q WORD --id I] [--all]                 open debt, queue first
#   history <id>                              a doc's timeline + what its last run added/removed
#   keywords                                  keyword vocabulary, most used first
#   rules  <file>...                          .claude/rules/*.md whose paths: match the files
#   changed                                   files this work touched: uncommitted + untracked, .claude/ excluded
#   commit <file>...                          the commit holding these files — empty while any is uncommitted
#   unrecorded [N]                            commits since the last one any index record names: hash<TAB>docs|-
#   spec-mark                                 snapshot the spec files (committed or not) as ingest's baseline
#   spec-diff [git-diff args]                 spec files now vs that baseline — hand edits since the last ingest
# Filters are OR'd; none given → everything. `req` compares as a string, so 7.1 and 7.10 stay apart.
set -uo pipefail

root=$PWD
while [ ! -d "$root/.claude/clio" ] && [ "$root" != "/" ]; do root=$(dirname "$root"); done
[ -d "$root/.claude/clio" ] || { echo "no .claude/clio above $PWD — run /clio:setup" >&2; exit 1; }
cd "$root"
IDX=.claude/clio/database/index.jsonl
DEBT=.claude/clio/database/debt.jsonl
PLANS=.claude/clio/docs/plans

# Parseable lines only, and say how many were not — a malformed line must never read as "nothing on record".
valid(){
  [ -f "$1" ] || { echo "missing $1" >&2; return 0; }
  local all good
  all=$(grep -c . "$1"); good=$(jq -Rc 'fromjson? // empty' "$1" | tee /dev/fd/3 | wc -l)
  [ "$all" -eq "$good" ] || echo "WARN: $1 has $((all-good)) malformed line(s) — results are partial, run validate.sh all" >&2
} 3>&1

# One group per document across the 3.0 id migration: a path maps to the id that later claimed it,
# by `doc` (stayed put) or `supersedes` (moved).
G='(map(select(.id)|{key:.doc,value:.id}) + map(select(.supersedes)|{key:.supersedes,value:.id})
    | from_entries) as $m | group_by(.id // $m[.doc] // .doc)'

r="" s="" f="" a="" k="" t="" i="" q="" all=false
parse(){
  while [ $# -gt 0 ]; do
    case $1 in
      --req) r=$2 ;; --spec) s=$2 ;; --file) f=$2 ;; --area) a=$2 ;; --keyword) k=$2 ;;
      --task) t=$2 ;; --id) i=$2 ;; --q) q=$2 ;; --all) all=true; shift; continue ;;
      *) echo "unknown filter: $1" >&2; exit 1 ;;
    esac
    shift 2
  done
  A=(--arg r "$r" --arg s "$s" --arg f "$f" --arg a "$a" --arg k "$k" --arg t "$t" --arg i "$i" --arg q "$q")
}
NONE='($r+$s+$f+$a+$k+$t+$i+$q=="")'
REQ='($r!="" and any(.req[]?; tostring==$r))'
SPEC='($s!="" and any(.specs[]?; contains($s)))'

SPECS=.claude/clio/docs/specs
# The spec files' content as a git tree, committed or not, ignored or not — ingest's baseline is what
# the files said, not what was committed.
spec_tree(){
  local idx; idx=$(mktemp); rm -f "$idx"
  GIT_INDEX_FILE=$idx git add -A -f -- "$SPECS" >/dev/null 2>&1
  GIT_INDEX_FILE=$idx git write-tree; rm -f "$idx"
}

cmd=${1:-summary}; shift || true
case $cmd in
  built)
    parse "$@"
    valid "$IDX" | jq -s -c "${A[@]}" "$G"' | .[] | last | select('"$NONE"' or '"$REQ"' or '"$SPEC"'
      or ($f!="" and any(.files[]?; contains($f)))
      or ($a!="" and .domain==$a)
      or ($k!="" and any(.keywords[]?; contains($k)))
      or ($t!="" and any(.plan_tasks[]?; tostring==$t))
      or ($i!="" and .id==$i))' ;;
  owed)
    parse "$@"
    valid "$DEBT" | jq -s -c --argjson all "$all" "${A[@]}" '[group_by(.id)[] | last
      | select($all or .status!="done")
      | select('"$NONE"' or '"$REQ"' or '"$SPEC"'
        or ($a!="" and .domain==$a)
        or ($i!="" and .id==$i)
        or ($q!="" and (.domain==$q or any(.req[]?; tostring==$q) or any(.specs[]?; contains($q))
                        or any(.what[]?; contains($q)))))]
      | sort_by(.blocked_by != null) | .[]' ;;
  history)
    [ -n "${1:-}" ] || { echo "usage: q.sh history <id>" >&2; exit 1; }
    valid "$IDX" | jq -s -c --arg i "$1" 'map(select(.id==$i or .doc==$i)) | (.[]),
      (if length>1 then {changed:.[-1].date, added:(.[-1].files - .[-2].files), removed:(.[-2].files - .[-1].files)} else empty end)' ;;
  keywords)
    valid "$IDX" | jq -s -r "$G"' | .[] | last | .keywords[]?' | sort | uniq -c | sort -rn | head -30 ;;
  summary)
    shopt -s nullglob
    plans=("$PLANS"/*.md)
    [ ${#plans[@]} -gt 0 ] || echo "no plans — /clio:plan has not been run"
    for p in "${plans[@]}"; do
      # A plan lifted from an old requirements.md may still be bullets; cutting columns out of a
      # bullet prints the whole line, so pick the shape per file.
      n=$(grep -m1 '\[ \]' "$p")
      case $n in '|'*) n=$(cut -d'|' -f2,3,5 <<<"$n") ;; *) n=${n:0:80} ;; esac
      printf '%s: done=%s open=%s next:%s\n' "$(basename "$p" .md)" \
        "$(grep -c '\[x\]' "$p")" "$(grep -c '\[ \]' "$p")" "$(tr -s ' ' <<<"$n")"
    done
    valid "$DEBT" | jq -s -r '[group_by(.id)[] | last | select(.status!="done")]
      | "debt: queue=\(map(select(.blocked_by==null))|length) blocked=\(map(select(.blocked_by!=null))|length)"'
    valid "$IDX" | jq -s -r 'if length==0 then "last memo: none yet" else last | "last memo: \(.date) \(.doc)" end' ;;
  changed)
    git rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repository — take the file list from the session" >&2; exit 0; }
    # -z: paths with spaces arrive unquoted; a rename is "XY new\0old\0", so the old path is skipped.
    git status --porcelain=v1 -z -uall 2>/dev/null | while IFS= read -r -d '' e; do
      st=${e:0:2}; p=${e:3}
      case $st in R*|C*) IFS= read -r -d '' _ ;; esac
      case $p in .claude/*) continue ;; esac
      printf '%s\n' "$p"
    done ;;
  commit)
    # Empty is a valid answer: not a repo, no commit yet, or part of this work still uncommitted.
    [ $# -gt 0 ] || exit 0
    git rev-parse --verify -q HEAD >/dev/null 2>&1 || exit 0
    [ -z "$(git status --porcelain -- "$@" 2>/dev/null)" ] || exit 0
    git log -1 --format=%h -- "$@" 2>/dev/null ;;
  unrecorded)
    git rev-parse --verify -q HEAD >/dev/null 2>&1 || exit 0
    # Recorded hashes may be abbreviated to any length; compare on 7 characters.
    rec=$(valid "$IDX" | jq -r '.commits[]?, (.commit // empty)' | cut -c1-7 | sort -u)
    git log -"${1:-20}" --no-merges --format=%h | while read -r h; do
      grep -qx "${h:0:7}" <<<"$rec" && break          # everything older was recorded, or predates Clio
      files=$(git show --name-only --format= "$h" | grep -v '^\.claude/')
      [ -n "$files" ] || continue                      # a commit of .claude/ only — Clio's own output
      docs=$(while IFS= read -r f; do "$0" built --file "$f"; done <<<"$files" | jq -r .doc | sort -u | paste -sd, -)
      printf '%s\t%s\n' "$h" "${docs:--}"
    done ;;
  spec-mark)
    git rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repository — no baseline to keep" >&2; exit 1; }
    # A commit object under a local ref keeps the tree from `git gc`; refs/clio/* is not pushed by default.
    tree=$(spec_tree)
    c=$(git -c user.name=clio -c user.email=clio@localhost commit-tree "$tree" -m "clio: ingest baseline")
    git update-ref refs/clio/ingest "$c"
    git rev-parse --short "$tree" ;;
  spec-diff)
    base=$(git rev-parse -q --verify 'refs/clio/ingest^{tree}' 2>/dev/null) \
      || { echo "no ingest baseline in this clone — fall back to the Last ingest commit, or reconstruct" >&2; exit 1; }
    git diff "$@" "$base" "$(spec_tree)" ;;
  rules)
    [ $# -gt 0 ] || { echo "usage: q.sh rules <file>..." >&2; exit 1; }
    shopt -s globstar nullglob
    for rf in .claude/rules/**/*.md; do
      # ponytail: only the YAML list form of paths: is read, and `**` matches like `*` (crossing `/`).
      # Good enough to name candidates; Claude Code's own matcher is what actually loads them.
      # paths: as a YAML list, an inline [a, b] list, or a single string.
      globs=$(awk 'NR==1 && $0!="---"{exit} NR>1 && $0=="---"{exit}
                   /^paths:/{v=$0; sub(/^paths:[ \t]*/,"",v)
                     if(v!=""){gsub(/[][ "\047]/,"",v); n=split(v,a,","); for(i=1;i<=n;i++) if(a[i]!="") print a[i]; exit}
                     p=1; next}
                   p && /^[ \t]*-/{sub(/^[ \t]*-[ \t]*/,""); gsub(/["\047]/,""); print; next} p{p=0}' "$rf")
      if [ -z "$globs" ]; then echo "$rf  (no paths: — loads every session)"; continue; fi
      for file in "$@"; do
        while IFS= read -r g; do
          # shellcheck disable=SC2053
          [[ $file == $g ]] && { echo "$rf  ← $file matches $g"; break 2; }
        done <<<"$globs"
      done
    done ;;
  *) sed -n '2,14p' "$0"; exit 1 ;;
esac
