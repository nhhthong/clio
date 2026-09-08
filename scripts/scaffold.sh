#!/usr/bin/env bash
# Scaffold Clio's data files into a project's .claude/ — safe to re-run, never overwrites.
# Called by /clio-setup. Usage: scaffold.sh /path/to/project
set -euo pipefail
for t in bash jq git awk; do command -v "$t" >/dev/null 2>&1 || { echo "FAIL: $t not installed — hooks and validate.sh need it"; exit 1; }; done
sed --version 2>/dev/null | grep -q GNU || echo "WARN: non-GNU sed — the step files use GNU 'sed -i'; on macOS: brew install gnu-sed"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TPL="$ROOT/skills/clio-setup/templates"
PROJ="${1:?usage: scaffold.sh /path/to/project}"
DEST="$PROJ/.claude"

mkdir -p "$DEST"/rules "$DEST"/clio "$DEST"/docs/specs/memory "$DEST"/docs/tasks/sub-tasks "$DEST"/docs/decisions
[ -f "$DEST/CLAUDE.md" ]                   || cp "$TPL/CLAUDE.md"        "$DEST/CLAUDE.md"
[ -f "$DEST/CONTEXT.md" ]                  || cp "$TPL/CONTEXT.md"       "$DEST/CONTEXT.md"
[ -f "$DEST/docs/specs/requirements.md" ]  || cp "$TPL/requirements.md"  "$DEST/docs/specs/requirements.md"
[ -f "$DEST/clio/index.jsonl" ]            || : > "$DEST/clio/index.jsonl"
[ -f "$DEST/clio/debt.jsonl" ]             || : > "$DEST/clio/debt.jsonl"

# stack rules — only for stacks the repo actually has; /clio-setup step 4 verifies each line
stacks=""
[ -f "$PROJ/composer.json" ] && stacks="$stacks php"
[ -f "$PROJ/go.mod" ] && stacks="$stacks go"
ls "$PROJ"/pom.xml "$PROJ"/build.gradle* >/dev/null 2>&1 && stacks="$stacks java"
[ -f "$PROJ/pubspec.yaml" ] && stacks="$stacks dart"
for s in $stacks; do [ -f "$DEST/rules/$s.md" ] || cp "$ROOT/skills/clio-setup/rules/$s.md" "$DEST/rules/"; done

jq -r .version "$ROOT/.claude-plugin/plugin.json" > "$DEST/clio/.version"
echo "Done → $DEST ($(find "$DEST" -type f | wc -l) files, clio $(cat "$DEST/clio/.version"), rules:${stacks:- none})"
