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

debt a spec-blocked '[2]' '"PO owes tax rule"'     >  $D; ok debt "valid spec-blocked"
debt b spec-blocked '[]' null                      >> $D; ko debt "spec-blocked without blocked_by"
debt c typo '[]' null                              >> $D; ko debt "unknown kind"
debt d code-debt '[9]' null                        >> $D; ko debt "req 9 has no requirements row"

# all: pre-2.0 delta ledger and orphan doc both warn, run still passes
idx .claude/docs/tasks/a.md '["a.go"]' '[1]'       >  $I
idx .claude/docs/tasks/a.md '["b.go"]' '[1]'       >> $I
debt a spec-blocked '[2]' '"PO owes tax rule"'     >  $D
touch .claude/docs/tasks/orphan.md
out=$(bash "$V" all) || { echo "$out"; exit 1; }
grep -q 'pre-2.0'    <<<"$out" || { echo "expected pre-2.0 warn"; echo "$out"; exit 1; }
grep -q 'orphan doc' <<<"$out" || { echo "expected orphan warn"; echo "$out"; exit 1; }
echo OK
