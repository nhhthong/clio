#!/usr/bin/env bash
# test-guard.sh — the smallest check that fails if clio-guard.sh stops guarding runs.jsonl. jq only.
set -u
H=$(cd "$(dirname "$0")" && pwd)/clio-guard.sh
R=.claude/clio/database/runs.jsonl
bad=0
# CWD: where the call runs — a repo with .claude/clio, or not. Defaults to one that has it.
C=$(mktemp -d); N=$(mktemp -d); trap 'rm -rf "$C" "$N"' EXIT; mkdir -p "$C/.claude/clio/database"
call(){ jq -nc --arg t "$1" --arg k "$2" --arg v "$3" --arg cwd "${CWD:-$C}" \
  '{tool_name:$t, tool_input:{($k):$v}, cwd:$cwd}' | bash "$H" 2>/dev/null; }
deny(){ call "$@"; [ $? -eq 2 ] || { echo "expected deny: $*"; bad=1; }; }
allow(){ call "$@"; [ $? -eq 0 ] || { echo "expected allow: $*"; bad=1; }; }

deny  Write file_path "/repo/$R"
deny  Edit  file_path "/repo/$R"
deny  Bash  command "echo '{\"case\":\"x\",\"result\":\"pass\"}' >> $R"
deny  Bash  command "jq -c . x.json | tee -a $R"
deny  Bash  command "sed -i '\$d' $R"
deny  Bash  command "cd /repo && rm $R"
deny  Bash  command "cp /tmp/fake $R"
allow Bash  command "jq -c 'select(.case==\"3.3-u1\")' $R | tail -1"
allow Bash  command "cat $R; grep pass $R"
allow Bash  command "/p/skills/test/scripts/clio-test.sh run 3.3-u1   # appends to runs.jsonl"
allow Write file_path "/repo/.claude/clio/docs/tests/auth.md"
allow Bash  command "git status"
deny  Bash  command "git restore $R"                       # reverting drops every uncommitted fail
deny  Bash  command "git checkout HEAD -- $R"
deny  Bash  command "mv $R /tmp/old.jsonl"
allow Bash  command "cp $R /tmp/backup.jsonl"              # a copy *from* it is a read
CWD="$C/.claude/clio/database" deny Bash command "echo x >> runs.jsonl"   # bare name, inside Clio
CWD="$N" allow Bash command "python train.py > logs/runs.jsonl"          # another tool, no Clio

[ $bad -eq 0 ] && echo OK
exit $bad
