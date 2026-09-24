#!/usr/bin/env bash
# selftest.sh — the smallest check that fails if q.sh's queries break. jq only.
set -u
Q=$(cd "$(dirname "$0")" && pwd)/q.sh
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT; cd "$d"
mkdir -p .claude/clio/database .claude/clio/docs/plans .claude/rules/api
I=.claude/clio/database/index.jsonl; D=.claude/clio/database/debt.jsonl
bad=0
eq(){ [ "$1" = "$2" ] || { echo "expected [$2] got [$1] — $3"; bad=1; }; }

# a pre-3.0 record (no id) later claimed by id 100 through `supersedes`, then two runs of id 100
cat > $I <<'EOF'
{"date":"2026-01-01","type":"task","doc":"old/a.md","domain":"x","files":["a.go"],"commits":[],"keywords":["orders"],"req":[5],"specs":[]}
{"date":"2026-02-01","id":"100","type":"task","doc":"t/100_a.md","supersedes":"old/a.md","domain":"x","plan_tasks":["7.1"],"files":["a.go"],"commits":[],"keywords":["orders"],"req":["7.1"],"specs":[]}
{"date":"2026-03-01","id":"100","type":"task","doc":"t/100_a.md","domain":"x","plan_tasks":["7.1"],"files":["a.go","b.go"],"commits":[],"keywords":["orders"],"req":["7.1","7.10"],"specs":[]}
{"date":"2026-03-02","id":"200","type":"task","doc":"t/200_b.md","domain":"y","plan_tasks":["7.10"],"files":["c.go"],"commits":[],"keywords":["billing"],"req":["7.10"],"specs":["m/pay.md"]}
EOF
cat > $D <<'EOF'
{"id":"d1","status":"pending","blocked_by":"PO answer","req":["7.1"],"what":["tax rule"],"domain":"x","specs":[]}
{"id":"d2","status":"pending","blocked_by":null,"req":["7.10"],"what":["rounding"],"domain":"y","specs":[]}
{"id":"d3","status":"pending","blocked_by":null,"req":["7.1"],"what":["old"],"domain":"x","specs":[]}
{"id":"d3","status":"done","blocked_by":null,"req":["7.1"],"what":["old"],"domain":"x","specs":[]}
EOF

eq "$("$Q" built | wc -l | tr -d ' ')" 2 "legacy record bridged into id 100, one line per doc"
eq "$("$Q" built --req 7.1 | jq -r .id)" 100 "7.1 is not 7.10"
eq "$("$Q" built --req 7.10 | jq -r .id | sort | tr '\n' ' ')" "100 200 " "7.10 matches both docs once each"
eq "$("$Q" built --task 7.10 | jq -r .id)" 200 "plan task as a string"
eq "$("$Q" built --file b.go --area x | wc -l | tr -d ' ')" 1 "OR'd filters do not duplicate a doc"
eq "$("$Q" owed | jq -r .id | tr '\n' ' ')" "d2 d1 " "queue first, done excluded"
eq "$("$Q" owed --req 7.1 | jq -r .id)" d1 "owed by row"
eq "$("$Q" owed --all --id d3 | jq -r .status)" done "--all sees closed records"
eq "$("$Q" history 100 | tail -1 | jq -c .added)" '["b.go"]' "history diff"
eq "$("$Q" summary | tail -1)" "last memo: 2026-03-02 t/200_b.md" "summary last memo"

# summary's next task: a table plan gives id · task · levels; a bullet plan must not dump its whole line
printf '| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n| 3.1 | orders list | 3 | unit, api | – | – | [ ] |\n' > .claude/clio/docs/plans/tbl.md
printf -- '- [ ] **1.16** File association registration for JPG/JPEG/PNG/WebP/GIF/TIFF/BMP, on the primary dev OS first, others tracked as follow-ups (req #30).\n' > .claude/clio/docs/plans/blt.md
out=$("$Q" summary)
grep -q '^tbl: done=0 open=1 next: 3.1 | orders list | unit, api' <<<"$out" || { echo "table plan next lost: $out"; bad=1; }
b=$(grep '^blt:' <<<"$out"); [ "${#b}" -le 120 ] || { echo "bullet plan dumped whole: $b"; bad=1; }
# a pre-4.0 row superseded by its replacement counts as neither open nor done
printf '| # | Task | req | Test that proves it | Needs | Done |\n|---|---|---|---|---|---|\n| 3.2 | 401 | 3 | `go test` | – | superseded 2026-09-24 → 3.2.1 |\n\n| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n| 3.2.1 | 401 | 3 | api | – | – | [ ] |\n' > .claude/clio/docs/plans/sup.md
grep -q '^sup: done=0 open=1 next: 3.2.1 ' <<<"$("$Q" summary)" || { echo "superseded row counted or replacement not next: $("$Q" summary | grep sup)"; bad=1; }
rm .claude/clio/docs/plans/tbl.md .claude/clio/docs/plans/blt.md .claude/clio/docs/plans/sup.md

echo 'not json' >> $D
"$Q" owed 2>err >/dev/null; grep -q malformed err || { echo "malformed line not reported"; bad=1; }

printf -- '---\npaths:\n  - "src/api/**/*.ts"\n---\n- rule\n' > .claude/rules/api/ts.md
printf -- '- always\n' > .claude/rules/all.md
eq "$("$Q" rules src/api/v1/x.ts | grep -c 'api/ts.md')" 1 "path-scoped rule matched"
eq "$("$Q" rules README.md | grep -c 'api/ts.md')" 0 "path-scoped rule not matched"
eq "$("$Q" rules README.md | grep -c 'loads every session')" 1 "unscoped rule named"

: > $I; eq "$("$Q" summary 2>/dev/null | tail -1)" "last memo: none yet" "empty index"

# --- git: which files changed, which commit holds them, which commits nobody recorded
eq "$("$Q" commit a.go 2>/dev/null)" "" "not a git repo → empty commit"
rm -f err; git init -q; git config user.email t@t; git config user.name t
eq "$("$Q" commit a.go)" "" "no commit yet → empty"
echo 1 > a.go; echo 1 > 'b c.go'; mkdir -p .claude/x; echo 1 > .claude/x/y
eq "$("$Q" changed | sort | tr '\n' '|')" "a.go|b c.go|" "untracked listed, spaces intact, .claude/ excluded"
git add a.go 'b c.go'; git commit -qm one; h1=$(git log -1 --format=%h)
eq "$("$Q" commit a.go 'b c.go')" "$h1" "clean and committed → its hash"
echo 2 >> a.go
eq "$("$Q" commit a.go 'b c.go')" "" "part of the work uncommitted → empty, not HEAD"
git mv 'b c.go' d.go
eq "$("$Q" changed | sort | tr '\n' '|')" "a.go|d.go|" "rename lists the new path only"
git commit -qam two; h2=$(git log -1 --format=%h)
echo '{"date":"2026-03-03","id":"300","type":"task","doc":"t/300_x.md","domain":"x","plan_tasks":[],"files":["a.go"],"commits":["'"$h1"'"],"keywords":["k"],"req":[],"specs":[]}' >> $I
eq "$("$Q" unrecorded 2>/dev/null)" "$(printf '%s\tt/300_x.md' "$h2")" "unrecorded stops at the recorded commit and names the doc"
git add -A .claude; git commit -qm memo
eq "$("$Q" unrecorded 2>/dev/null | cut -f1)" "$h2" "a .claude/-only commit is skipped"

printf -- '---\npaths: ["lib/**/*.rb", "app/*.rb"]\n---\n- r\n' > .claude/rules/rb.md
eq "$("$Q" rules app/x.rb | grep -c 'rb.md')" 1 "inline paths: list parsed"

[ $bad -eq 0 ] && echo OK
exit $bad
