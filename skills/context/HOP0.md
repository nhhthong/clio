# Hop 0 — where are we (no target given)

Counts only. Opens no task doc, no spec, no ADR.

```bash
for p in .claude/docs/plans/*.md; do [ -e "$p" ] || continue
  # A plan is normally /clio:plan's table, but one /clio:audit lifted out of requirements.md keeps
  # its original bullets until it is re-planned. Cutting columns out of a bullet prints the whole
  # line, so pick the shape per file.
  n=$(grep -m1 '\[ \]' "$p")
  case $n in '|'*) n=$(cut -d'|' -f2,3,5 <<<"$n") ;; *) n=${n:0:80} ;; esac
  printf '%s: done=%s open=%s next:%s\n' "$(basename "$p" .md)" \
    "$(grep -c '\[x\]' "$p")" "$(grep -c '\[ \]' "$p")" "$(tr -s ' ' <<<"$n")"
done
jq -s -r 'group_by(.id)[] | last | select(.status!="done")
  | if .blocked_by==null then "queue" else "blocked" end' .claude/clio/debt.jsonl | sort | uniq -c
tail -1 .claude/clio/index.jsonl | jq -r '"last memo: \(.date) \(.doc)"'
```

Report, ≤ 10 lines: per area `done/open` + the first open task and its test · debt `queue` vs
`blocked` counts · last memo. No plans → say `/clio:plan` has not been run. A `next:` whose `Needs`
is unticked is not next — say which task it waits on.

Stop here. The user names an area, row, debt `id` or asks a question → hops 1–3 for that target.
