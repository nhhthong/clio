# tables.sh — the one place that reads Clio's Markdown tables. Sourced, never run:
#   . "<plugin>/skills/lib/tables.sh"
# Every function prints tab-separated rows, so callers never split on `|` themselves. One set of
# rules for all of them: a line inside <!-- … --> is not read, a table row may be indented, cells
# are trimmed, and an empty cell prints as `–` (read collapses empty tab fields).
# selftest: skills/lib/selftest.sh — fixtures and the exact output expected of each function.

# awk prelude: skip lines inside <!-- … --> — a table commented out is not a table.
CLIO_NOCOMMENT='/<!--/ {incom=1} incom { if (/-->/) incom=0; next }'

# Plan tables (.claude/clio/docs/plans/*.md). One line per task row:
#   file  id  task  req  levels  needs  done  kind
# kind is `row` under a header with a Levels column (4.0+), `old` under a pre-4.0 header (Test
# column; levels then prints `–`). Columns are found by header name, so a reordered table still
# reads right; rows before any header use today's positions (Done = the last cell). The header
# resets per file.
plan_rows(){
  [ $# -gt 0 ] || return 0
  awk "$CLIO_NOCOMMENT"'
    FNR==1 {kind="row"; tc=3; rc=4; lc=5; nc=6; dc=0}
    /^[ \t]*\|/ {
      n=split($0,c,"|"); for(i=2;i<n;i++) gsub(/^[ \t]+|[ \t]+$/,"",c[i])
      if (c[2]=="#") {
        kind="old"; tc=3; rc=4; lc=0; nc=0; dc=0
        for(i=3;i<n;i++){
          if(c[i]=="Task") tc=i; if(c[i]=="req") rc=i; if(c[i]=="Levels"){lc=i; kind="row"}
          if(c[i]=="Needs") nc=i; if(c[i]=="Done") dc=i }
        next
      }
      if (c[2] !~ /^[0-9]+(\.[0-9]+)*$/) next
      printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n", FILENAME, c[2], z(c[tc]), z(c[rc]), (lc ? z(c[lc]) : "–"), (nc ? z(c[nc]) : "–"), z(c[dc ? dc : n-1]), kind
    }
    function z(x){ return x=="" ? "–" : x }' "$@"
}

# requirements.md's row table. One line per numbered row:  num  status
# status is the 4th cell (Decision status), markers and all.
req_rows(){
  [ -f "${1:-}" ] || return 0
  awk "$CLIO_NOCOMMENT"'
    /^[ \t]*\|/ {
      n=split($0,c,"|"); for(i=2;i<n;i++) gsub(/^[ \t]+|[ \t]+$/,"",c[i])
      if (c[2] ~ /^[0-9]+(\.[0-9]+)*$/) printf "%s\t%s\n", c[2], (c[5]=="" ? "–" : c[5])
    }' "$1"
}

# Case tables (.claude/clio/docs/tests/*.md). $1 is the allowed level names, space-separated; the
# rest are files. Current: | Case | Task | Level | Covers | Behaviour | Expected (source) | Command | Repeat |
# pre-4.1 (no Covers column, accepted unchanged — its rows just carry no id to enforce):
#   | Case | Task | Level | Behaviour | Expected (source) | Command | Repeat |
# Prints: case  task  level  covers  command  repeat  tracked  error — one line per case row.
# tracked is 1 for a Covers-column row, 0 for a pre-4.1 one. error is empty for a well-formed row; a
# malformed one is still printed, so the case it belongs to fails loudly instead of running a
# truncated command.
case_rows(){
  local lv=$1; shift
  [ $# -gt 0 ] || return 0
  awk -F'|' -v lv=" $lv " "$CLIO_NOCOMMENT"'
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
    function z(x){ return x=="" ? "–" : x }' "$@"
}

# The case rows of one task ($1) exactly as written, whitespace-normalised — what approve hashes.
# Output must not change between versions: a stored approval is a hash of it.
case_lines(){
  local t=$1; shift
  [ $# -gt 0 ] || return 0
  awk -F'|' -v t="$t" "$CLIO_NOCOMMENT"'
    /^[ \t]*\|/ {g=$3; gsub(/^[ \t]+|[ \t]+$/,"",g); if(g==t){gsub(/[ \t]+/," "); print}}' "$@"
}

# `- <task> · <level.n> — <reason>` bullets (a tests doc's Not applicable list). One line each:
#   task  id  line (whitespace-normalised)
# `·` is multi-byte; tr in the C locale turns each of its bytes into a space on its own.
na_rows(){
  [ $# -gt 0 ] || return 0
  local raw
  raw=$(awk "$CLIO_NOCOMMENT"'/^-[ \t]*[^ \t]/ {gsub(/[ \t]+/," "); print}' "$@")
  [ -n "$raw" ] || return 0
  paste <(LC_ALL=C tr '·' ' ' <<<"$raw" | sed -E 's/^-[ \t]*//' | awk '{print $1 "\t" $2}') <(printf '%s\n' "$raw")
}
