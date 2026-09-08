#!/usr/bin/env bash
# Migrate a project set up with the pre-plugin skeleton (.claude/database/, routes.md, est/folder)
# to Clio's layout. Idempotent. Usage: migrate.sh /path/to/project
set -euo pipefail
D="${1:?usage: migrate.sh /path/to/project}/.claude"
[ -d "$D" ] || { echo "no .claude/ in $1"; exit 1; }

mkdir -p "$D/clio"
for f in index.jsonl debt.jsonl; do
  [ -f "$D/database/$f" ] && [ ! -f "$D/clio/$f" ] && mv "$D/database/$f" "$D/clio/$f"
done
[ -f "$D/docs/specs/routes.md" ] && mv "$D/docs/specs/routes.md" "$D/docs/specs/requirements.md"

for f in "$D"/clio/*.jsonl; do
  [ -s "$f" ] || continue
  jq -c 'if has("est") then .req = .est | del(.est) else . end
         | if has("folder") then .domain = .folder | del(.folder) else . end' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
done

targets=""; for p in "$D/CLAUDE.md" "$D/CONTEXT.md" "$D/docs" "$D/rules"; do [ -e "$p" ] && targets="$targets $p"; done
{ [ -n "$targets" ] && grep -rl -E '\.claude/database/|routes\.md|/feature-done|/spec-update|/spec-ingest|`/debt`|related-context' $targets || true; } \
  | while IFS= read -r f; do
  sed -i -E 's#\.claude/database/#.claude/clio/#g; s/routes\.md/requirements.md/g; s#/feature-done#/clio-memo#g;
             s#/spec-update#/clio-update#g; s#/spec-ingest#/clio-ingest#g; s#`/debt`#`/clio-debt`#g;
             s/related-context/clio-context/g' "$f"
done

echo "migrated → $D/clio, requirements.md, req/domain fields."
echo "Delete by hand (agents are usually denied rm):"
echo "  $D/database  $D/commands-ref  $D/skills/related-context  $D/hooks  $D/.structure-version"
echo "  $D/commands/{debt,feature-done,spec-ingest,spec-update}.md"
echo "Then drop the old skeleton hooks from ~/.claude/settings.json (session-debt, feature-done-reminder) — the plugin ships its own."
