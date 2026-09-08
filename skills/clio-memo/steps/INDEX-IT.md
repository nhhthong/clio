# Step 4 — Index it: `.claude/clio/index.jsonl`

Append-only JSONL, one line per document written **every run** (UPDATE too — multiple lines per
`doc` is its timeline). Hub-doc entries (see `UPDATE-MODE.md` § Hub + entry split) never get their
own line, only the hub does.

**Reuse keywords first:**
```bash
jq -r --arg d "<doc path>" 'select(.doc==$d) | .keywords[]?' .claude/clio/index.jsonl | sort -u
```

**Append** — the paths in the example are placeholders; use this repo's real ones:
```bash
echo '{"date":"YYYY-MM-DD","type":"task","update":true,"doc":".claude/docs/tasks/2026-07-15_account-two-factor.md","domain":"account","files":["src/orders/order-service.ts"],"commit":"<hash or null>","keywords":["<kw1>","<kw2>"],"specs":[".claude/docs/specs/memory/ui-design.md"],"req":[2]}' >> .claude/clio/index.jsonl
```
- `date` = today. `doc` = unchanged path. `update` = `true` after the first run, omit/false on CREATE.
- `type` = `"task"` or `"adr"`.
- `domain` = one term from the vocabulary listed in `.claude/CLAUDE.md` § Project memory (**by
  domain served, not file location**). New term needed → add it there and say so in the final report.
- `specs` = only what `requirements.md` actually maps `req` to; `req:[]` → name the governing `memory/*.md`
  file or `[]`, never attach a plausible-looking spec.
- `files`/`keywords`/`commit` = this run's delta only, repo-relative, build output excluded (see
  `GATHER-FACTS.md`). Never empty just because a prior record has one — readers union across
  records. Docs-only run with nothing → say so in the final report, don't ship `[]` silently.
- `req`/`specs` = **not** deltas — restate the doc's full current claim every run (readers take the
  *last* value; getting this backwards silently un-tags rows). Resolved in `GATHER-FACTS.md`.
- Renamed/deleted doc → never rewrite old records; append a new-path record with
  `"supersedes":"<old path>"`.
- APPEND ONLY — never rewrite/reorder/clean existing lines, including this doc's own earlier runs.

**Validate every appended line before declaring done:**
```bash
tail -1 .claude/clio/index.jsonl | jq -e '
  (.date and .type and .doc and ((.keywords|length)>0)
   and (.req|type=="array") and (.specs|type=="array")) as $ok
    | if $ok then .doc else "MISSING FIELD" end' | tr -d '"' \
  | { read -r p; [ -f "$p" ] && echo OK || echo "BAD: $p"; }

tail -1 .claude/clio/index.jsonl | jq -r '.specs[]?' | while read -r p; do [ -f "$p" ] || echo "BAD spec: $p"; done

rows=$(awk -F'|' '/^\|/{gsub(/[ \t]/,"",$2);
  if($2 ~ /^[0-9]+(\.[0-9]+)*(–[0-9]+(\.[0-9]+)*)?$/){
    n=split($2,a,"–");
    if(n==1) print a[1];
    else if(a[1] !~ /\./ && a[2] !~ /\./) { for(i=a[1];i<=a[2];i++) print i }
    else { print a[1]; print a[2] }}}' .claude/docs/specs/requirements.md)
tail -1 .claude/clio/index.jsonl | jq -r '.req[]?' | while read -r n; do
  echo "$rows" | grep -qx "$n" || echo "BAD req: $n has no requirements.md row"
done
```
Dotted row numbers (`4.2`) are matched literally; a dotted *range* (`9.1–9.3`) only yields its two
endpoints, so `9.2` reports `BAD req` — widen the row's `#` cell or accept the warning.

`BAD: MISSING FIELD` → required key absent. `BAD: <path>` → points at a file that doesn't exist.
Parse error → malformed JSON. Any bad → `sed -i '$d'` to drop the line, re-append correctly. Also
warn if `files` is empty on a non-docs-only run.

Read-side queries (by file/domain/keyword) live in the `clio-context` skill.

Next: `DEBT-IT.md`.
