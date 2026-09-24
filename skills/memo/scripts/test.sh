#!/usr/bin/env bash
# test.sh — the smallest check that fails if validate.sh's logic breaks. No args, no deps beyond jq.
set -eu
V=$(cd "$(dirname "$0")" && pwd)/validate.sh
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT; cd "$d"
mkdir -p .claude/clio/database .claude/clio/docs/tasks/feat .claude/clio/docs/specs/memory
printf '| # | Task | Spec | Status |\n|---|---|---|---|\n| 1 | x | m | ✅ |\n| 2 | y | m | ⚠️ open |\n' > .claude/clio/docs/specs/requirements.md
touch .claude/clio/docs/specs/memory/m.md
mkdir -p .claude/clio/docs/plans
printf '| # | Task | req | Levels | Needs | Done |\n|---|---|---|---|---|---|\n| 1.1 | login | 1 | unit | – | [ ] |\n| 1.2 | logout | 1 | unit | 1.1 | [ ] |\n' > .claude/clio/docs/plans/acct.md
A=.claude/clio/docs/tasks/feat/1700000001_alpha.md
B=.claude/clio/docs/tasks/feat/1700000002_beta.md
L=.claude/clio/docs/tasks/legacy.md                       # pre-3.0 flat doc, no id — still readable
touch "$A" "$B" "$L" .claude/clio/docs/tasks/feat/summary.md
I=.claude/clio/database/index.jsonl; D=.claude/clio/database/debt.jsonl
ok(){ bash "$V" "$1" >/dev/null || { echo "expected pass: $2"; exit 1; }; }
ko(){ if bash "$V" "$1" >/dev/null; then echo "expected FAIL: $2"; exit 1; fi; }
# idx <id> <doc> <files> <req> [plan_tasks-json-array]
idx(){ echo "{\"date\":\"2026-01-01\",\"id\":\"$1\",\"type\":\"task\",\"doc\":\"$2\",\"domain\":\"x\",\"plan_tasks\":${5:-[]},\"files\":$3,\"commits\":[],\"keywords\":[\"k\"],\"req\":$4,\"specs\":[]}"; }
# old(): a pre-3.0 record — no id, no plan_tasks. `all` names it, never fails on it.
old(){ echo "{\"date\":\"2026-01-01\",\"type\":\"task\",\"doc\":\"$1\",\"domain\":\"x\",\"files\":$2,\"commits\":[],\"keywords\":[\"k\"],\"req\":$3,\"specs\":[]}"; }
debt(){ echo "{\"date\":\"2026-01-01\",\"id\":\"$1\",\"kind\":\"$2\",\"status\":\"pending\",\"domain\":\"x\",\"what\":[\"w\"],\"req\":$3,\"specs\":[],\"docs\":[],\"code\":[],\"action\":\"\",\"source\":null,\"blocked_by\":$4,\"issue\":null}"; }

idx 1700000001 "$A" '["a.go"]' '["1"]'               >  $I; ok index "valid index line"
idx 1700000001 "$A" '["a.go"]' '["1"]' '["1.1"]'     >> $I; ok index "plan_tasks carries the plan row"
# req is checked against requirements.md; plan_tasks must be checked against the plans the same way,
# or a typo'd id silently sends /clio:memo to tick a task nobody tested
idx 1700000001 "$A" '["a.go"]' '["1"]' '["9.9"]'     >> $I; ko index "plan_tasks 9.9 is in no plan row"
# an array, like req: a doc written before the one-doc-per-subtask split covers a range of them
idx 1700000001 "$A" '["a.go"]' '["1"]' '["1.1","1.2"]' >> $I; ok index "plan_tasks holds several ids"
idx 1700000001 "$A" '["a.go"]' '["9"]'               >> $I; ko index "req 9 has no requirements row"
idx 1700000001 "$A" '["a.go"]' '[1]'               >> $I; ko index "req as a number — 7.1 and 7.10 would collide"
idx 1700000009 .claude/clio/docs/tasks/feat/1700000009_gone.md '[]' '[]' >> $I; ko index "doc missing on disk"
echo '{not json'                                   >> $I; ko index "invalid JSON"
# id IS the filename prefix (INDEX-IT.md) — the binding that keeps one id bound to one doc
idx 1700000003 "$A" '["a.go"]' '["1"]'               >> $I; ko index "id is not the doc's filename prefix"
old "$A" '["a.go"]' '[1]'                          >> $I; ko index "no id — 3.0 write path requires it"
echo '{"date":"2026-01-01","id":"1700000001","type":"task","doc":"'"$A"'","domain":"x","plan_tasks":[],"files":[],"keywords":["k"],"req":[],"specs":[]}' >> $I; ko index "no commits array"
echo '{"date":"2026-01-01","id":"1700000001","type":"task","doc":"'"$A"'","plan_tasks":[],"files":["a.go"],"commits":[],"keywords":["k"],"req":[],"specs":[]}' >> $I; ko index "no domain — INDEX-IT.md says always present"

debt a spec-blocked '["2"]' '"PO owes tax rule"'     >  $D; ok debt "valid spec-blocked"
debt c typo '[]' null                              >> $D; ko debt "unknown kind"
debt d code-debt '["9"]' null                        >> $D; ko debt "req 9 has no requirements row"
echo '{"id":"j","kind":"code-debt","status":"pending","what":["w"],"req":[],"specs":[],"code":[],"blocked_by":null}' >> $D; ko debt "8 of 14 fields — DEBT-IT.md says all 14, always"

# debt mode is group-aware too, not just `all`: the record that FILES a spec-blocked needs its blocker,
# but a later record may null it once the answer lands (DEBT-IT.md § 1).
debt e spec-blocked '["2"]' null                     >  $D; ko debt "spec-blocked filed with null blocked_by"
debt e spec-blocked '["2"]' '"PO owes tax rule"'     >  $D
echo '{"date":"2026-01-01","id":"e","kind":"spec-blocked","status":"pending","domain":"x","what":["w"],"req":["2"],"specs":[],"docs":[],"code":[],"action":"","source":null,"blocked_by":null,"issue":null}' >> $D
ok debt "later record nulls blocked_by once unblocked"

# the FIRST record is what is judged, so a later line supplying the blocker does not launder a
# record that was filed with none — and tail -1 being the good line must not hide it
debt i spec-blocked '["2"]' null                     >  $D
debt i spec-blocked '["2"]' '"PO owes tax rule"'     >> $D
ko debt "filed with null, fixed later — still the wrong filing"

# all: pre-2.0 delta ledger (scalar `commit`, shrinking files) and orphan doc both warn, run still
# passes; a clean doc that drops a reverted file must NOT be nagged as pre-2.0
echo '{"date":"2026-01-01","type":"task","doc":"'"$L"'","domain":"x","files":["a.go"],"commit":"abc","keywords":["k"],"req":[1],"specs":[]}' > $I
old "$L" '["b.go"]' '[1]'                          >> $I
idx 1700000001 "$A" '["c.go","d.go"]' '["1"]'        >> $I
idx 1700000001 "$A" '["c.go"]' '["1"]'               >> $I
debt a spec-blocked '["2"]' '"PO owes tax rule"'     >  $D
echo '{"id":"old","kind":"code-debt","status":"pending","what":["w"],"req":[],"specs":[],"code":[],"blocked_by":null}' >> $D   # pre-2.1 record: audit names it, run still passes
out=$(bash "$V" all) || { echo "$out"; exit 1; }
grep -q 'debt record is missing: date domain docs action source issue' <<<"$out" || { echo "expected missing-fields WARN for old"; echo "$out"; exit 1; }
grep -q 'legacy.md.*pre-2.0' <<<"$out" || { echo "expected pre-2.0 warn for legacy.md"; echo "$out"; exit 1; }
grep -q 'index record is missing: id plan_tasks' <<<"$out" || { echo "pre-3.0 record not named by the audit"; echo "$out"; exit 1; }
if grep -q '1700000001_alpha.md.*pre-2.0' <<<"$out"; then echo "clean doc wrongly nagged as pre-2.0"; echo "$out"; exit 1; fi
# a doc nested under tasks/<feature>/ must be visible to the orphan check — a non-recursive glob
# would make every 3.0 task doc invisible to it
grep -q "orphan doc, no index record: $B" <<<"$out" || { echo "nested orphan not seen"; echo "$out"; exit 1; }
# summary.md is feature-level blurb, never an indexed doc
if grep -q 'orphan doc.*summary.md' <<<"$out"; then echo "summary.md wrongly called an orphan"; echo "$out"; exit 1; fi

# all: a migrated doc — pre-3.0 records still key on the old path, which a migration moved away.
# The record carrying `supersedes` is what resolves them; without it this is a FAIL, with it an INFO.
mkdir -p .claude/clio/docs/tasks/login
M=.claude/clio/docs/tasks/login/1700000005_login.md; touch "$M"
old .claude/clio/docs/tasks/2026-08-01_login.md '["l.go"]' '[1]'  >  $I
echo '{"date":"2026-01-01","id":"1700000005","type":"task","doc":"'"$M"'","domain":"x","plan_tasks":[],"files":["l.go"],"commits":[],"keywords":["k"],"req":[1],"specs":[],"supersedes":".claude/clio/docs/tasks/2026-08-01_login.md"}' >> $I
idx 1700000001 "$A" '["a.go"]' '["1"]'                >> $I
debt a spec-blocked '["2"]' '"PO owes tax rule"'      >  $D
out=$(bash "$V" all) || { echo "a migrated doc must not fail the audit"; echo "$out"; exit 1; }
grep -q 'renamed doc, superseded' <<<"$out" || { echo "supersedes not resolved"; echo "$out"; exit 1; }
# a doc with an id that moved: its earlier line keeps the old path, which is history, not a broken link
echo '{"date":"2026-01-01","id":"1700000005","type":"task","doc":".claude/clio/docs/tasks/1700000005_login.md","domain":"x","plan_tasks":[],"files":["l.go"],"commits":[],"keywords":["k"],"req":["1"],"specs":[]}' | cat - $I > $I.tmp && mv $I.tmp $I
out=$(bash "$V" all); grep -q 'missing doc.*1700000005_login' <<<"$out" && { echo "moved id doc flagged by its history"; echo "$out"; exit 1; }
if grep -q 'points at a missing file' <<<"$out"; then echo "superseded path double-reported as FAIL"; echo "$out"; exit 1; fi
# and the migration must read as finished: the superseded group's pre-3.0 records are history, so
# they must not keep reporting the very fields the successor just supplied — otherwise a migration
# finds work to do on every run and is never idempotent
if grep -q 'index record is missing' <<<"$out"; then echo "finished migration still reported as pending"; echo "$out"; exit 1; fi
rm -rf .claude/clio/docs/tasks/login

# all: a doc that gains an id but KEEPS its path — a spec or rules file the ledger indexes, which
# a migration gives an id without moving. Without bridging doc->id the pre-3.0 records form a second
# group whose last record is the old short one, and the finished migration reports as unfinished.
S=.claude/clio/docs/specs/memory/m.md
echo '{"date":"2026-01-01","type":"task","doc":"'"$S"'","domain":"x","files":["a.go"],"commit":"abc","keywords":["k"],"req":[1],"specs":[]}' > $I
echo '{"date":"2026-01-02","id":"1700000007","type":"task","doc":"'"$S"'","domain":"x","plan_tasks":[],"files":["a.go"],"commits":["abc"],"keywords":["k"],"req":[1],"specs":[]}' >> $I
idx 1700000001 "$A" '["a.go"]' '["1"]'                >> $I
debt a spec-blocked '["2"]' '"PO owes tax rule"'      >  $D
out=$(bash "$V" all) || { echo "a doc given an id in place must not fail"; echo "$out"; exit 1; }
if grep -q 'index record is missing' <<<"$out"; then echo "id-in-place migration still reported as pending"; echo "$out"; exit 1; fi
if grep -q 'pre-2.0' <<<"$out"; then echo "pre-2.0 warn survived a completed migration"; echo "$out"; exit 1; fi
# the filename-prefix rule is for the dirs Clio names; a spec file keeps its own name
if grep -q 'is not the filename prefix' <<<"$out"; then echo "prefix rule wrongly applied to a spec file"; echo "$out"; exit 1; fi

# HOP2's section-reading command must not drop a section. A sed range ends ON the next heading and
# consumes it, so `## Side Effects` straight after `## Decisions` vanished — the one section that
# says what you can break. Run the documented command against a template-shaped doc.
cat > /tmp/clio-sec-$$.md <<'DOC'
# D
## Summary
s
## Decisions
- chose X
## Side Effects
- breaks Z
## Testing Done
- ran it
## Follow-up
- open
## Change Log
- init
DOC
sec=$(awk '/^## /{p = /^## (Decisions|Side Effects|Follow-up)/} p' /tmp/clio-sec-$$.md); rm -f /tmp/clio-sec-$$.md
for want in '- chose X' '- breaks Z' '- open'; do
  grep -qF -- "$want" <<<"$sec" || { echo "HOP2 section read dropped: $want"; echo "$sec"; exit 1; }
done
grep -qF -- '- ran it' <<<"$sec" && { echo "HOP2 section read pulled in Testing Done"; echo "$sec"; exit 1; }
grep -qF -- '- init' <<<"$sec" && { echo "HOP2 section read ran past Follow-up"; echo "$sec"; exit 1; }

# all: a malformed line does not suppress schema checks on the other records (2.0.1)
idx 1700000001 "$A" '["a.go"]' '["1"]'                >  $I
echo '{"date":"2026-01-01","id":"1700000002","type":"nope","doc":"'"$B"'","domain":"x","plan_tasks":[],"files":[],"commits":[],"keywords":["k"],"req":[1],"specs":[]}' >> $I
echo '{broken'                                      >> $I
debt a spec-blocked '["2"]' '"PO owes tax rule"'      >  $D
out=$(bash "$V" all) && { echo "expected FAIL behind a malformed line"; echo "$out"; exit 1; }
grep -q 'not valid JSON'           <<<"$out" || { echo "expected malformed-line FAIL"; echo "$out"; exit 1; }
grep -q 'required field, bad type' <<<"$out" || { echo "bad-type record not checked past malformed line"; echo "$out"; exit 1; }

# all: spec-blocked names its blocker when filed; a later line may null it once unblocked (DEBT-IT § 1)
idx 1700000001 "$A" '["a.go"]' '["1"]'                >  $I
debt f spec-blocked '["2"]' '"PO owes a rule"'        >  $D
echo '{"date":"2026-01-01","id":"f","kind":"spec-blocked","status":"pending","domain":"x","what":["w"],"req":[2],"specs":[],"docs":[],"code":[],"action":"","source":null,"blocked_by":null,"issue":null}' >> $D
debt g spec-blocked '["2"]' null                      >> $D
debt i spec-blocked '["2"]' null                      >> $D
debt i spec-blocked '["2"]' '"PO owes a rule"'        >> $D
out=$(bash "$V" all) && { echo "expected FAIL: spec-blocked g filed with null blocked_by"; echo "$out"; exit 1; }
grep -q 'debt g' <<<"$out" || { echo "g not flagged"; echo "$out"; exit 1; }
grep -q 'debt i' <<<"$out" || { echo "i filed with null, fixed later — not flagged"; echo "$out"; exit 1; }
if grep -q 'debt f' <<<"$out"; then echo "unblocked spec-blocked f wrongly flagged"; echo "$out"; exit 1; fi
# one id, one finding: the rule lives in one place, so `all` must not report it twice
[ "$(grep -c 'debt g' <<<"$out")" = 1 ] || { echo "duplicate FAIL for g"; echo "$out"; exit 1; }

# A path written into a document's prose is not a field, so nothing else checks it — and renaming a
# doc is exactly what leaves one pointing at nothing. Template placeholders holding `<` are not paths.
idx 1700000001 "$A" '["a.go"]' '["1"]'                >  $I
debt a spec-blocked '["2"]' '"PO owes tax rule"'      >  $D
printf 'see `.claude/clio/docs/decisions/1700000099_gone.md` and `.claude/clio/docs/tasks/<feature>/<id>_x.md`\n' >> "$A"
out=$(bash "$V" all) || { echo "a dead link must warn, not fail"; echo "$out"; exit 1; }
grep -q 'dead link in a document: .claude/clio/docs/decisions/1700000099_gone.md' <<<"$out" \
  || { echo "dead link not reported"; echo "$out"; exit 1; }
grep -q 'dead link.*<feature>' <<<"$out" && { echo "template placeholder wrongly reported as a path"; echo "$out"; exit 1; }
: > "$A"

# A spec-delta names a change the code has not followed. /clio:plan absorbs one by writing a task
# that carries its id, so an open, unblocked delta in no plan means the plan still matches the old
# decision — silently, until someone reads it. Blocked or done deltas are not the plan's to absorb.
idx 1700000001 "$A" '["a.go"]' '["1"]' '["1.1"]'      >  $I
debt sd spec-delta '["1"]' null                       >  $D
out=$(bash "$V" all) || { echo "an unabsorbed spec-delta must warn, not fail"; echo "$out"; exit 1; }
grep -q 'spec-delta sd is in no plan' <<<"$out" || { echo "unabsorbed spec-delta not reported"; echo "$out"; exit 1; }
echo '| 9.9 | absorbs sd | 1 | t | - | [ ] |' >> .claude/clio/docs/plans/acct.md
out=$(bash "$V" all); grep -q 'spec-delta sd is in no plan' <<<"$out" && { echo "delta named in a plan still reported"; echo "$out"; exit 1; }
debt sd spec-delta '["1"]' '"PO owes the rule"'       >  $D          # blocked: not the plan's to absorb
out=$(bash "$V" all); grep -q 'is in no plan' <<<"$out" && { echo "blocked delta wrongly reported"; echo "$out"; exit 1; }
sed -i.bak '$d' .claude/clio/docs/plans/acct.md && rm -f .claude/clio/docs/plans/acct.md.bak

# The manifests and the four places the version lives. There is no CI, so this is the only thing
# that catches a release naming two different builds — run it before you tag.
# a pre-4.0 plan (Test column) that was never re-planned is named; once a Levels table follows, it is not
printf '| # | Task | req | Test that proves it | Needs | Done |\n|---|---|---|---|---|---|\n| 1.1 | x | 1 | `go test` | - | [x] 2026-01-01 |\n' > .claude/clio/docs/plans/old.md
bash "$V" all | grep -q 'old.md is a pre-4.0 plan' || { echo "pre-4.0 plan not named"; exit 1; }
printf '\n| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n| 1.1.1 | harden | 1 | unit | 1.1 | - | [ ] |\n' >> .claude/clio/docs/plans/old.md
bash "$V" all | grep -q 'old.md is a pre-4.0 plan' && { echo "re-planned plan still named"; exit 1; }
rm .claude/clio/docs/plans/old.md

cd "$(dirname "$V")/../../.."
jq -e . .claude-plugin/plugin.json .claude-plugin/marketplace.json > /dev/null || { echo "a manifest is not valid JSON"; exit 1; }
# hooks/hooks.json loads by convention. Naming it in plugin.json too makes the loader read it twice
# and refuse both, which silently kills the drift nudge — so the manifest must NOT mention it.
[ -f hooks/hooks.json ] || { echo "hooks/hooks.json is missing"; exit 1; }
jq -e 'has("hooks")' .claude-plugin/plugin.json >/dev/null 2>&1 \
  && { echo "plugin.json declares .hooks; the standard hooks/hooks.json already loads itself"; exit 1; }
v=$(jq -r .version .claude-plugin/plugin.json)
[ "$(jq -r '.plugins[0].version' .claude-plugin/marketplace.json)" = "$v" ] || { echo "marketplace.json disagrees with plugin.json ($v)"; exit 1; }
grep -q "version-$v-blue" README.md      || { echo "README badge is not version $v"; exit 1; }
grep -q "^## $v[^0-9]" CHANGELOG.md      || { echo "CHANGELOG.md has no '## $v' heading"; exit 1; }

echo OK
