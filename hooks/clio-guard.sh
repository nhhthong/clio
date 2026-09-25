#!/usr/bin/env bash
# clio-guard.sh — PreToolUse hook. runs.jsonl is test evidence: only clio-test.sh may append to it.
# Refuses an Edit/Write on it and a Bash command that writes, deletes or reverts it any other way
# (redirect, tee, sed -i, rm, truncate, dd, mv, cp/install onto it, git restore/checkout). Reads —
# cat, jq, grep, a cp *from* it — pass. Acts only in a repo with .claude/clio, so another tool's
# runs.jsonl elsewhere is never touched. Exit 2 blocks the call and hands stderr to Claude.
# ponytail: pattern match on the command text — a script that opens the file itself gets past it.
# It stops the shortcut, not a determined bypass; the gate's fingerprint and approval do the rest.
set -u

input=$(cat)
tool=$(jq -r '.tool_name // empty' <<<"$input" 2>/dev/null) || exit 0
say(){ echo "clio: $1 — runs.jsonl is written only by clio-test.sh run/approve; run the case instead." >&2; exit 2; }

case $tool in
  Write|Edit|MultiEdit)
    path=$(jq -r '.tool_input.file_path // empty' <<<"$input")
    [[ $path == *.claude/clio/database/runs.jsonl ]] && say "$tool on runs.jsonl refused"
    ;;
  Bash)
    cmd=$(jq -r '.tool_input.command // empty' <<<"$input")
    [[ $cmd == *runs.jsonl* ]] || exit 0
    # Clio's runs.jsonl only: named by its path, or a bare name inside a repo that has .claude/clio.
    if [[ $cmd != *clio/database/runs.jsonl* ]]; then
      d=$(jq -r '.cwd // empty' <<<"$input"); d=${d:-$PWD}
      while [ ! -d "$d/.claude/clio" ] && [ "$d" != / ] && [ -n "$d" ]; do d=$(dirname "$d"); done
      [ -d "$d/.claude/clio" ] || exit 0
    fi
    # Split on ; && || | and newlines, then judge each simple command on its own.
    while IFS= read -r part; do
      [[ $part == *runs.jsonl* ]] || continue
      [[ $part == *clio-test.sh* ]] && continue
      read -ra w <<<"$part"
      last=${w[${#w[@]}-1]}
      if grep -qE '>>?[[:space:]]*[^[:space:]]*runs\.jsonl' <<<"$part" \
        || grep -qE '(^|[[:space:]])(tee|truncate|rm|dd)([[:space:]]|$)|sed[[:space:]]+(-[a-zA-Z]*i|--in-place)' <<<"$part" \
        || grep -qE '(^|[[:space:]])mv([[:space:]]|$)' <<<"$part" \
        || { grep -qE '(^|[[:space:]])(cp|install)([[:space:]]|$)' <<<"$part" && [[ $last == *runs.jsonl ]]; } \
        || grep -qE 'git[[:space:]]+(restore|checkout)([[:space:]]|$)' <<<"$part"; then
        say "a command writing, deleting or reverting runs.jsonl refused: $part"
      fi
    done < <(sed -E 's/(\|\||&&|;|\|)/\n/g' <<<"$cmd")
    ;;
esac
exit 0
