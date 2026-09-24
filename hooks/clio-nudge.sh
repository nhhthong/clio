#!/usr/bin/env bash
# clio-nudge.sh — UserPromptSubmit hook. Once per session, tells Claude that work exists which
# /clio:memo has not recorded yet. Reminder only: it reads git and index.jsonl and writes neither
# ledger. Silence (exit 0, no output) is the normal case — it speaks only when the loop has drifted.
set -u

input=$(cat)
sid=$(jq -r '.session_id // "nosid"' <<<"$input" 2>/dev/null) || exit 0
cwd=$(jq -r '.cwd // empty' <<<"$input" 2>/dev/null)
[ -n "${cwd:-}" ] && cd "$cwd" 2>/dev/null

IDX=.claude/clio/database/index.jsonl
# No Clio here, or the loop never started: /clio:setup already said the loop is manual. Say nothing.
[ -s "$IDX" ] || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

# One nudge per session. /tmp is session-scoped enough and keeps the marker out of the user's repo.
# $sid becomes a path, so strip anything that could walk out of the directory.
sid=$(printf '%s' "$sid" | tr -cd 'A-Za-z0-9._-')
mark="${TMPDIR:-/tmp}/clio-nudge-${sid:-nosid}"
[ -e "$mark" ] && exit 0

# --porcelain, not `git diff HEAD`: a brand-new file nobody has `git add`ed yet is exactly the
# work most likely to be missing from the ledger, and `git diff` cannot see it. `cut -c4-` drops
# porcelain's two status columns and keeps paths with spaces intact.
# .claude/ is excluded: /clio:memo writes there, so counting it would nag about memo's own output.
dirty=$(git status --porcelain 2>/dev/null | cut -c4- | grep -vc '^\.claude/')
[ -n "$dirty" ] || dirty=0

# ponytail: 6-char prefix match against the recorded commits. INDEX-IT.md writes short hashes of
# unpinned length, so compare on the shortest form either side can produce. A 6-char collision
# would cost one missed nudge — use full hashes here only if that ever actually happens.
sha=$(git rev-parse --short=6 HEAD 2>/dev/null || echo "")
indexed=yes
# fromjson?, not a plain filter: jq aborts at the first malformed line and would then report every
# commit as unindexed, nagging forever. validate.sh fixed the same trap in 2.0.1.
if [ -n "$sha" ] && ! jq -R -r 'fromjson? | .commits[]?' "$IDX" 2>/dev/null | grep -qF "$sha"; then
  indexed=no
fi

if [ "$dirty" -eq 0 ] && [ "$indexed" = yes ]; then
  exit 0
fi

# Cannot record that we nudged → do not nudge: silence beats the same line on every prompt.
: 2>/dev/null > "$mark" || exit 0

msg="clio: work is not recorded in .claude/clio/database/index.jsonl — "
if [ "$dirty" -gt 0 ]; then
  msg="${msg}${dirty} uncommitted change(s) in the working tree"
fi
if [ "$dirty" -gt 0 ] && [ "$indexed" = no ]; then
  msg="${msg}; "
fi
if [ "$indexed" = no ]; then
  msg="${msg}HEAD ${sha} appears in no index record (recorded before it was committed? /clio:memo only backfills the hash)"
fi
printf '%s.\n' "$msg"
printf 'Tell the user once that /clio:memo is owed for this work, then carry on with their request.\n'
printf 'This notice is not permission to run it. Only the user asking is — they decide the work is done.\n'
exit 0
