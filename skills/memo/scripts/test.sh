#!/usr/bin/env bash
# test.sh — the smallest check that fails if validate.sh's logic breaks. No args, no deps beyond jq.
set -eu
V=$(cd "$(dirname "$0")" && pwd)/validate.sh
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT; cd "$d"
mkdir -p .claude/clio .claude/docs/tasks .claude/docs/specs/memory
printf '| # | Task | Spec | Status |\n|---|---|---|---|\n| 1 | x | m | ✅ |\n| 2 | y | m | ⚠️ open |\n' > .claude/docs/specs/requirements.md
touch .claude/docs/tasks/a.md .claude/docs/specs/memory/m.md
I=.claude/clio/index.jsonl; D=.claude/clio/debt.jsonl
ok(){ bash "$V" "$1" >/dev/null || { echo "expected pass: $2"; exit 1; }; }
ko(){ if bash "$V" "$1" >/dev/null; then echo "expected FAIL: $2"; exit 1; fi; }
idx(){ echo "{\"date\":\"2026-01-01\",\"type\":\"task\",\"doc\":\"$1\",\"domain\":\"x\",\"files\":$2,\"commits\":[],\"keywords\":[\"k\"],\"req\":$3,\"specs\":[]}"; }
debt(){ echo "{\"date\":\"2026-01-01\",\"id\":\"$1\",\"kind\":\"$2\",\"status\":\"pending\",\"domain\":\"x\",\"what\":[\"w\"],\"req\":$3,\"specs\":[],\"docs\":[],\"code\":[],\"action\":\"\",\"source\":null,\"blocked_by\":$4,\"issue\":null}"; }

idx .claude/docs/tasks/a.md '["a.go"]' '[1]'       >  $I; ok index "valid index line"
idx .claude/docs/tasks/a.md '["a.go"]' '[9]'       >> $I; ko index "req 9 has no requirements row"
idx .claude/docs/tasks/missing.md '[]' '[]'        >> $I; ko index "doc missing on disk"
echo '{not json'                                   >> $I; ko index "invalid JSON"
echo '{"date":"2026-01-01","type":"task","doc":".claude/docs/tasks/a.md","domain":"x","files":[],"keywords":["k"],"req":[],"specs":[]}' >> $I; ko index "no commits array"
echo '{"date":"2026-01-01","type":"task","doc":".claude/docs/tasks/a.md","files":["a.go"],"commits":[],"keywords":["k"],"req":[],"specs":[]}' >> $I; ko index "no domain — INDEX-IT.md says always present"

debt a spec-blocked '[2]' '"PO owes tax rule"'     >  $D; ok debt "valid spec-blocked"
debt c typo '[]' null                              >> $D; ko debt "unknown kind"
debt d code-debt '[9]' null                        >> $D; ko debt "req 9 has no requirements row"
echo '{"id":"j","kind":"code-debt","status":"pending","what":["w"],"req":[],"specs":[],"code":[],"blocked_by":null}' >> $D; ko debt "8 of 14 fields — DEBT-IT.md says all 14, always"

# debt mode is group-aware too, not just `all`: the record that FILES a spec-blocked needs its blocker,
# but a later record may null it once the answer lands (DEBT-IT.md § 1).
debt e spec-blocked '[2]' null                     >  $D; ko debt "spec-blocked filed with null blocked_by"
debt e spec-blocked '[2]' '"PO owes tax rule"'     >  $D
echo '{"date":"2026-01-01","id":"e","kind":"spec-blocked","status":"pending","domain":"x","what":["w"],"req":[2],"specs":[],"docs":[],"code":[],"action":"","source":null,"blocked_by":null,"issue":null}' >> $D
ok debt "later record nulls blocked_by once unblocked"

# the FIRST record is what is judged, so a later line supplying the blocker does not launder a
# record that was filed with none — and tail -1 being the good line must not hide it
debt i spec-blocked '[2]' null                     >  $D
debt i spec-blocked '[2]' '"PO owes tax rule"'     >> $D
ko debt "filed with null, fixed later — still the wrong filing"

# all: pre-2.0 delta ledger (scalar `commit`, shrinking files) and orphan doc both warn, run still
# passes; a clean 2.0 doc that drops a reverted file must NOT be nagged as pre-2.0
echo '{"date":"2026-01-01","type":"task","doc":".claude/docs/tasks/a.md","domain":"x","files":["a.go"],"commit":"abc","keywords":["k"],"req":[1],"specs":[]}' > $I
idx .claude/docs/tasks/a.md '["b.go"]' '[1]'        >> $I
idx .claude/docs/tasks/c.md '["c.go","d.go"]' '[1]' >> $I
idx .claude/docs/tasks/c.md '["c.go"]' '[1]'        >> $I
touch .claude/docs/tasks/c.md
debt a spec-blocked '[2]' '"PO owes tax rule"'      >  $D
touch .claude/docs/tasks/orphan.md
echo '{"id":"old","kind":"code-debt","status":"pending","what":["w"],"req":[],"specs":[],"code":[],"blocked_by":null}' >> $D   # pre-2.1 record: audit names it, run still passes
out=$(bash "$V" all) || { echo "$out"; exit 1; }
grep -q 'debt record is missing: date domain docs action source issue' <<<"$out" || { echo "expected missing-fields WARN for old"; echo "$out"; exit 1; }
grep -q 'a.md.*pre-2.0' <<<"$out" || { echo "expected pre-2.0 warn for a.md"; echo "$out"; exit 1; }
if grep -q 'c.md.*pre-2.0' <<<"$out"; then echo "clean 2.0 c.md wrongly nagged as pre-2.0"; echo "$out"; exit 1; fi
grep -q 'orphan doc'    <<<"$out" || { echo "expected orphan warn"; echo "$out"; exit 1; }

# all: a malformed line does not suppress schema checks on the other records (2.0.1)
idx .claude/docs/tasks/a.md '["a.go"]' '[1]'        >  $I
echo '{"date":"2026-01-01","type":"nope","doc":".claude/docs/tasks/a.md","domain":"x","files":[],"commits":[],"keywords":["k"],"req":[1],"specs":[]}' >> $I
echo '{broken'                                      >> $I
debt a spec-blocked '[2]' '"PO owes tax rule"'      >  $D
out=$(bash "$V" all) && { echo "expected FAIL behind a malformed line"; echo "$out"; exit 1; }
grep -q 'not valid JSON'           <<<"$out" || { echo "expected malformed-line FAIL"; echo "$out"; exit 1; }
grep -q 'required field, bad type' <<<"$out" || { echo "bad-type record not checked past malformed line"; echo "$out"; exit 1; }

# all: spec-blocked names its blocker when filed; a later line may null it once unblocked (DEBT-IT § 1)
idx .claude/docs/tasks/a.md '["a.go"]' '[1]'        >  $I
debt f spec-blocked '[2]' '"PO owes a rule"'        >  $D
echo '{"date":"2026-01-01","id":"f","kind":"spec-blocked","status":"pending","domain":"x","what":["w"],"req":[2],"specs":[],"docs":[],"code":[],"action":"","source":null,"blocked_by":null,"issue":null}' >> $D
debt g spec-blocked '[2]' null                      >> $D
debt i spec-blocked '[2]' null                      >> $D
debt i spec-blocked '[2]' '"PO owes a rule"'        >> $D
out=$(bash "$V" all) && { echo "expected FAIL: spec-blocked g filed with null blocked_by"; echo "$out"; exit 1; }
grep -q 'debt g' <<<"$out" || { echo "g not flagged"; echo "$out"; exit 1; }
grep -q 'debt i' <<<"$out" || { echo "i filed with null, fixed later — not flagged"; echo "$out"; exit 1; }
if grep -q 'debt f' <<<"$out"; then echo "unblocked spec-blocked f wrongly flagged"; echo "$out"; exit 1; fi
# one id, one finding: the rule lives in one place, so `all` must not report it twice
[ "$(grep -c 'debt g' <<<"$out")" = 1 ] || { echo "duplicate FAIL for g"; echo "$out"; exit 1; }
echo OK
