#!/usr/bin/env bash
# selftest.sh — tables.sh against fixtures holding every awkward row the parsers must agree on: an
# indented row, a table inside <!-- -->, a pre-4.0 header, a reordered header, a superseded row,
# an empty cell, a `|` inside a command. Prints OK or each mismatch.
set -u
export LC_ALL=C
. "$(cd "$(dirname "$0")" && pwd)/tables.sh"
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT; cd "$d"
bad=0
eq(){ [ "$1" = "$2" ] || { printf 'FAIL %s\n--- got\n%s\n--- want\n%s\n' "$3" "$1" "$2"; bad=1; }; }

cat > plan.md <<'EOF'
# Plan — orders
| # | Task | req | Test that proves it | Needs | Done |
|---|------|-----|---------------------|-------|------|
| 3.2 | 401 without session | 3 | `go test ./x` | – | superseded 2026-09-24 → 3.2.1 |

<!--
| 9.9 | commented out | 9 | unit | – | – | [ ] |
-->

| # | Task | req | Levels | Needs | Touches | Done |
|---|------|-----|--------|-------|---------|------|
| 3.1 | list | 3 | unit, api | 0.4 | `orders/h.go` | [x] 2026-09-20 |
  | 3.2.1 | 401 without session | 3 | critical · api, security | 3.1 | | [ ] |
| 7.1 | — waits on `ocr-dpi-open` | 7.1 | – | – | – | – |
EOF
cat > reordered.md <<'EOF'
| # | Levels | Task | Done | req | Needs |
|---|---|---|---|---|---|
| 5.1 | unit | moved columns | [ ] | 5 | – |
EOF
eq "$(plan_rows plan.md reordered.md)" "$(printf '%s\n' \
'plan.md	3.2	401 without session	3	–	–	superseded 2026-09-24 → 3.2.1	old' \
'plan.md	3.1	list	3	unit, api	0.4	[x] 2026-09-20	row' \
'plan.md	3.2.1	401 without session	3	critical · api, security	3.1	[ ]	row' \
'plan.md	7.1	— waits on `ocr-dpi-open`	7.1	–	–	–	row' \
'reordered.md	5.1	moved columns	5	unit	–	[ ]	row')" "plan_rows"

cat > req.md <<'EOF'
| # | Task | Spec file(s) | Decision status (NOT build status) |
|---|------|--------------|-------------|
| 1 | login | [memory/a.md](memory/a.md) | ✅ |
 | 7.10 | ocr | [memory/b.md](memory/b.md) | ⚠️ dpi open |
<!-- | 8 | draft | x | ✅ | -->
EOF
eq "$(req_rows req.md)" "$(printf '%s\n' '1	✅' '7.10	⚠️ dpi open')" "req_rows"

cat > tests.md <<'EOF'
| Case | Task | Level | Covers | Behaviour | Expected (source) | Command | Repeat |
|---|---|---|---|---|---|---|---|
| 3.1-u1 | 3.1 | unit | unit.1 | ok | 50 (spec) | `go test -run A$` | 1 |
  | 3.1-a1 | 3.1 | api | api.1 | ok | 200 | `go test -run B$` | 1 |
| 3.1-x1 | 3.1 | unit | unit.1 | pipe | x | `a || b` | 1 |
| 3.1-z1 | 3.1 | smoke | – | n/a | x | – | – |
<!-- | 3.1-c1 | 3.1 | unit | unit.1 | commented | x | `true` | 1 | -->
| 2.1-u1 | 2.1 | unit | old format | x | `true` | 3 |

Not applicable:
- 3.1 · api.2 — read-only route
-   3.1·unit.3   —   spaced oddly
EOF
eq "$(case_rows "unit api smoke" tests.md)" "$(printf '%s\n' \
'3.1-u1	3.1	unit	unit.1	go test -run A$	1	1	' \
'3.1-a1	3.1	api	api.1	go test -run B$	1	1	' \
'3.1-x1	3.1	unit	–	–	–	1	the row splits into 10 cells, not 7 (pre-4.1) or 8 — a `|` in the command? wrap it in a script' \
'3.1-z1	3.1	smoke	–	–	–	1	' \
'2.1-u1	2.1	unit	–	true	3	0	')" "case_rows"
eq "$(case_rows "unit" tests.md | awk -F'\t' '$1=="3.1-a1" {print $8}')" "level api is not one of: unit" "case_rows level check"
eq "$(case_lines 3.1 tests.md | wc -l | tr -d ' ')" "4" "case_lines: the commented row is not approved"
eq "$(case_lines 3.1 tests.md | head -1)" "| 3.1-u1 | 3.1 | unit | unit.1 | ok | 50 (spec) | \`go test -run A\$\` | 1 |" "case_lines normalised"
eq "$(na_rows tests.md | cut -f1,2)" "$(printf '%s\n' '3.1	api.2' '3.1	unit.3')" "na_rows ids"

[ $bad -eq 0 ] && echo OK
exit $bad
