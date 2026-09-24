#!/usr/bin/env bash
# test-nudge.sh — the smallest check that fails if clio-nudge.sh's logic breaks. No args, jq + git only.
set -eu
H=$(cd "$(dirname "$0")" && pwd)/clio-nudge.sh
d=$(mktemp -d); trap 'rm -rf "$d" "$d.marks"' EXIT
export TMPDIR="$d.marks"; mkdir -p "$TMPDIR"   # outside the repo: markers must not show up in git status
SID="$d.marks/sid"                              # fixed path — one case overrides TMPDIR for the hook only
cd "$d"; git init -q .; git config user.email t@t; git config user.name t
mkdir -p .claude/clio/database
IDX=.claude/clio/database/index.jsonl

# The session id lives in a file: every helper below runs in a subshell, so a shell variable
# would not survive to the next call and every case would silently reuse one session.
send(){ printf '{"session_id":"%s","cwd":"%s"}' "$(cat "$SID")" "$d" | bash "$H"; }
run(){ echo "$RANDOM$RANDOM$RANDOM" > "$SID"; send; }   # a fresh session
quiet(){ [ -z "$(run)" ] || { echo "expected silence: $1"; run; exit 1; }; }
loud(){ run | grep -q "$2" || { echo "expected '$2': $1"; run; exit 1; }; }

echo x > a.txt; git add -A; git commit -qm one
quiet "no index.jsonl at all"

idx(){ echo "{\"date\":\"2026-01-01\",\"type\":\"task\",\"doc\":\"d.md\",\"commits\":[$1]}" > $IDX; }

idx ''
loud "HEAD in no index record" "appears in no index record"

idx "\"$(git rev-parse --short=6 HEAD)\""
quiet "HEAD indexed, tree clean"

{ printf '{broken\n'; echo "{\"commits\":[\"$(git rev-parse --short=6 HEAD)\"]}"; } > $IDX
quiet "a malformed ledger line must not fake an unindexed HEAD"

echo y >> a.txt
loud "tracked file dirty" "1 uncommitted change"
git checkout -q -- a.txt

echo new > b.txt                      # never `git add`ed — `git diff HEAD` cannot see this one
loud "untracked new file" "1 uncommitted change"
rm b.txt
mkdir -p .claude/clio/docs/tasks; echo z > .claude/clio/docs/tasks/d.md; git add -A
quiet "only .claude/ changed — that is memo's own output"

echo y >> a.txt
[ -n "$(run)" ] || { echo "expected a nudge before the dedup check"; exit 1; }
[ -z "$(send)" ] || { echo "nudged twice in one session"; exit 1; }

: > $IDX
quiet "empty index.jsonl — loop never started"

idx ''                                                    # would nudge — but the marker cannot be written
TMPDIR="$d.marks/does/not/exist" quiet "marker dir unwritable — silence, not a nag on every prompt"

echo OK
