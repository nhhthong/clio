#!/usr/bin/env bash
# Prove the plugin still works before it reaches a real project.
# Scaffolds into a temp dir, writes fixture records, runs validate.sh, checks the hooks.
# Usage: tests/selftest.sh
set -uo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
V="$SRC/scripts/validate.sh"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; fail=0
ok(){ echo "  ok   $*"; pass=$((pass+1)); }
no(){ echo "  FAIL $*"; fail=$((fail+1)); }
try(){ if eval "$2" >/dev/null 2>&1; then ok "$1"; else no "$1"; fi; }

echo "0. manifests"
try "plugin.json is valid JSON with a name" "jq -e '.name==\"clio\"' $SRC/.claude-plugin/plugin.json"
try "marketplace.json points at the repo root" "jq -e '.plugins[0].source==\"./\"' $SRC/.claude-plugin/marketplace.json"
try "plugin and marketplace versions agree" "[ \"\$(jq -r .version $SRC/.claude-plugin/plugin.json)\" = \"\$(jq -r '.plugins[0].version' $SRC/.claude-plugin/marketplace.json)\" ]"
try "hooks.json is valid JSON" "jq -e .hooks $SRC/hooks/hooks.json"
for s in setup context memo update ingest debt ask; do
  f="$SRC/skills/clio-$s/SKILL.md"
  grep -q "^name: clio-$s\$" "$f" && ok "skills/clio-$s/SKILL.md name" || no "skills/clio-$s/SKILL.md name"
done
grep -rq --exclude=migrate.sh 'commands-ref\|\.claude/database\|routes\.md\|\best\b\|\bfolder\b' "$SRC/skills" "$SRC/scripts" "$SRC/hooks" \
  && no "old skeleton names still referenced" || ok "no old skeleton names"

echo "1. scaffold.sh"
touch "$T/composer.json" "$T/go.mod"
"$SRC/scripts/scaffold.sh" "$T" >/dev/null || { echo "  FAIL scaffold.sh exited non-zero"; exit 1; }
ok "scaffolded"
for f in CLAUDE.md CONTEXT.md docs/specs/requirements.md clio/index.jsonl clio/debt.jsonl clio/.version; do
  [ -e "$T/.claude/$f" ] && ok "$f" || no "$f missing"
done
for r in php go; do [ -f "$T/.claude/rules/$r.md" ] && ok "rules/$r.md (detected)" || no "rules/$r.md missing"; done
for r in java dart; do [ -f "$T/.claude/rules/$r.md" ] && no "rules/$r.md copied without its stack" || ok "rules/$r.md skipped"; done
grep -q '^@CONTEXT.md' "$T/.claude/CLAUDE.md" && ok "CLAUDE.md imports CONTEXT.md" || no "@CONTEXT.md import missing"
"$SRC/scripts/scaffold.sh" "$T" >/dev/null 2>&1 && ok "re-run is safe" || no "re-run failed"

echo "2. index.jsonl round trip"
cd "$T"
cat > .claude/docs/tasks/2026-01-01_demo-feature.md <<'DOC'
# Demo
Date: 2026-01-01
DOC
echo '{"date":"2026-01-01","type":"task","doc":".claude/docs/tasks/2026-01-01_demo-feature.md","domain":"all","files":["src/x.rs"],"commit":null,"keywords":["demo"],"specs":[],"req":[1]}' \
  >> .claude/clio/index.jsonl
try "validate.sh index accepts a good line" "$V index"
echo '{"date":"2026-01-01","type":"task","doc":".claude/docs/tasks/nope.md","domain":"all","files":[],"commit":null,"keywords":["x"],"specs":[],"req":[1]}' \
  >> .claude/clio/index.jsonl
"$V" index >/dev/null 2>&1 && no "missing doc not caught" || ok "missing doc caught"
sed -i '$d' .claude/clio/index.jsonl
echo '{"date":"2026-01-01","type":"task","doc":".claude/docs/tasks/2026-01-01_demo-feature.md","domain":"all","files":[],"commit":null,"keywords":["x"],"specs":[],"req":[99]}' \
  >> .claude/clio/index.jsonl
"$V" index >/dev/null 2>&1 && no "bogus req not caught" || ok "bogus req caught"
sed -i '$d' .claude/clio/index.jsonl

echo "3. dotted requirements.md row numbers"
printf '| 4.2 | ocr hotkey | [x](x.md) | ✅ |\n' >> .claude/docs/specs/requirements.md
echo '{"date":"2026-01-01","type":"task","doc":".claude/docs/tasks/2026-01-01_demo-feature.md","domain":"all","files":[],"commit":null,"keywords":["ocr"],"specs":[],"req":[4.2]}' \
  >> .claude/clio/index.jsonl
try "req 4.2 resolves against a dotted row" "$V index"

echo "4. debt.jsonl is append-only, last line wins"
echo '{"date":"2026-01-01","id":"demo","kind":"spec-blocked","status":"pending","domain":"all","what":["undecided"],"req":[1],"specs":[],"docs":[],"code":[],"action":"ask","source":null,"blocked_by":"the PO","issue":null}' >> .claude/clio/debt.jsonl
echo '{"date":"2026-01-02","id":"demo","kind":"code-debt","status":"in-process","domain":"all","what":["half done"],"req":[1],"specs":[],"docs":[],"code":["src/x.rs"],"action":"finish","source":null,"blocked_by":null,"issue":null}' >> .claude/clio/debt.jsonl
try "validate.sh debt accepts a good line" "$V debt"
cur=$(jq -s -r 'group_by(.id)[] | last | .status' .claude/clio/debt.jsonl)
[ "$cur" = "in-process" ] && ok "last line per id wins ($cur)" || no "expected in-process, got $cur"
[ "$(wc -l < .claude/clio/debt.jsonl)" -eq 2 ] && ok "history line kept" || no "history line lost"

echo "5. validate.sh all"
"$V" all >"$T/out.txt" 2>&1
grep -q "orphan doc" "$T/out.txt" && no "false orphan on an indexed doc" || ok "no false orphan"
touch .claude/docs/tasks/2026-01-03_unindexed.md
"$V" all >"$T/out2.txt" 2>&1
grep -q "orphan doc" "$T/out2.txt" && ok "orphan doc caught" || no "orphan doc missed"

echo "6. hooks"
try "session-debt is executable" "[ -x $SRC/hooks/session-debt ]"
try "memo-reminder is executable" "[ -x $SRC/hooks/memo-reminder ]"
out=$(echo "{\"cwd\":\"$T\",\"hook_event_name\":\"SessionStart\"}" | "$SRC/hooks/session-debt")
grep -q "demo" <<<"$out" && ok "session-debt lists the actionable item" || no "session-debt output: $out"
out=$(echo '{"cwd":"/nonexistent","hook_event_name":"SessionStart"}' | "$SRC/hooks/session-debt")
[ -z "$out" ] && ok "session-debt silent outside the structure" || no "session-debt spoke up: $out"
echo "{\"cwd\":\"$T\",\"stop_hook_active\":true}" | "$SRC/hooks/memo-reminder" >/dev/null 2>&1
[ $? -eq 0 ] && ok "memo-reminder never blocks twice" || no "loop guard broken"
echo "{\"cwd\":\"$T\",\"stop_hook_active\":false}" | "$SRC/hooks/memo-reminder" >/dev/null 2>&1
[ $? -eq 0 ] && ok "memo-reminder silent without git" || no "fired without git"
git init -q "$T" && git -C "$T" add -A && git -C "$T" -c user.name=t -c user.email=t@t commit -qm init
sleep 1; echo x > "$T/src.rs"
out=$(echo "{\"cwd\":\"$T\",\"stop_hook_active\":false}" | "$SRC/hooks/memo-reminder" 2>/dev/null); rc=$?
[ $rc -eq 2 ] && grep -q "clio-memo" <<<"$out" && ok "memo-reminder blocks on unrecorded change" || no "memo-reminder rc=$rc out=$out"

echo "6b. session-debt orders newest first"
echo '{"date":"2025-12-01","id":"aaa-older","kind":"code-debt","status":"pending","domain":"all","what":["old item"],"req":[],"specs":[],"docs":[],"code":[],"action":"x","source":null,"blocked_by":null,"issue":null}' >> .claude/clio/debt.jsonl
first=$(echo "{\"cwd\":\"$T\",\"hook_event_name\":\"SessionStart\"}" | "$SRC/hooks/session-debt" | sed -n 2p)
grep -q "demo" <<<"$first" && ok "newest actionable listed first" || no "expected demo first, got: $first"

echo "6c. session-debt nudges when CONTEXT.md falls behind"
touch -t 202501010000 .claude/CONTEXT.md
out=$(echo "{\"cwd\":\"$T\",\"hook_event_name\":\"SessionStart\"}" | "$SRC/hooks/session-debt")
grep -q "CONTEXT.md unchanged" <<<"$out" && no "nudged with only 2 runs" || ok "silent under five runs"
for i in 1 2 3; do echo '{"date":"2026-02-01","type":"task","update":true,"doc":".claude/docs/tasks/2026-01-01_demo-feature.md","domain":"all","files":["src/y.rs"],"commit":null,"keywords":["demo"],"specs":[],"req":[1]}' >> .claude/clio/index.jsonl; done
out=$(echo "{\"cwd\":\"$T\",\"hook_event_name\":\"SessionStart\"}" | "$SRC/hooks/session-debt")
grep -q "CONTEXT.md unchanged across 5" <<<"$out" && ok "nudge fires at five runs" || no "nudge missing: $out"
touch .claude/CONTEXT.md
out=$(echo "{\"cwd\":\"$T\",\"hook_event_name\":\"SessionStart\"}" | "$SRC/hooks/session-debt")
grep -q "CONTEXT.md unchanged" <<<"$out" && no "nudge after CONTEXT.md touched" || ok "nudge clears once CONTEXT.md is written"

echo "6d. validate.sh all — every-session budget"
v=$("$V" all 2>&1)
grep -q "HTML comments" <<<"$v" && ok "leftover CONTEXT.md comments flagged" || no "template comments not flagged"
grep -q "budget ~150" <<<"$v" && no "budget warning on a fresh install" || ok "no budget warning on fresh install"
seq 1 160 | sed 's/^/- line /' >> .claude/CONTEXT.md
v=$("$V" all 2>&1)
grep -q "budget ~150" <<<"$v" && ok "budget warning over 150 lines" || no "budget warning missing"

echo "7. migrate.sh"
M=$(mktemp -d); mkdir -p "$M/.claude/database" "$M/.claude/docs/specs"
echo '{"date":"2026-01-01","id":"x","kind":"code-debt","status":"pending","folder":"cart","what":["w"],"est":[3],"specs":[],"docs":[],"code":[],"action":"a","source":null,"blocked_by":null,"issue":null}' > "$M/.claude/database/debt.jsonl"
: > "$M/.claude/database/index.jsonl"
echo '# r' > "$M/.claude/docs/specs/routes.md"
printf 'see .claude/database/debt.jsonl and routes.md, run /feature-done\n' > "$M/.claude/CLAUDE.md"
"$SRC/scripts/migrate.sh" "$M" >/dev/null 2>&1 || no "migrate.sh exited non-zero"
[ -f "$M/.claude/clio/debt.jsonl" ] && ok "ledger moved to clio/" || no "ledger not moved"
[ -f "$M/.claude/docs/specs/requirements.md" ] && ok "routes.md renamed" || no "routes.md not renamed"
jq -e '.req==[3] and .domain=="cart" and (has("est")|not) and (has("folder")|not)' "$M/.claude/clio/debt.jsonl" >/dev/null && ok "est/folder renamed to req/domain" || no "field rename failed"
grep -q '\.claude/clio/debt.jsonl and requirements.md, run /clio-memo' "$M/.claude/CLAUDE.md" && ok "CLAUDE.md references rewritten" || no "CLAUDE.md not rewritten"
rm -rf "$M"

echo
echo "pass $pass  fail $fail"
exit $((fail > 0 ? 1 : 0))
