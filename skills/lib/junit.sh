# junit.sh — batch templates and the JUnit XML they leave: which cases one runner start can take,
# and what the report says about each. Pure text in, text out; sourced after tables.sh (batches()
# uses its CLIO_NOCOMMENT). Nothing here runs a test or writes evidence — clio-test.sh does.
# selftest: skills/lib/selftest-junit.sh — golden output per runner's report shape.

# --- Batch mode: one runner start for many cases -------------------------------------------------
# A runner that boots something heavy (Maven + JVM + Spring: ~7 s) pays it once per case when every
# case is its own command. A `Batch:` line in .claude/rules/*.md (test/SKILL.md § 1b finds and writes
# it) names the one command that runs many tests and the JUnit XML it leaves behind:
#   Batch: `mvn -q -pl api test -Dtest={tests}` · join: `,` · report: `api/target/surefire-reports/TEST-*.xml`
# A case joins a batch only if its own command IS that template with {tests} = its test id, so the
# batch runs exactly the cases' commands, merged. Each case's result is read from the report; nothing
# is inferred from the batch's exit code alone. A case the report does not show, or shows fewer times
# than its Repeat, falls back to its own command.

# One line per template: template<TAB>join<TAB>report glob.
batches(){
  shopt -s nullglob; local files=(.claude/rules/*.md)
  [ ${#files[@]} -gt 0 ] || return 0
  awk "$CLIO_NOCOMMENT"'/^[-* \t]*Batch:/' "${files[@]}" | sed -E 's/^[-* \t]*Batch:[ \t]*//' \
    | awk -F' · ' '{ t=$1; j=","; r=""
        for(i=2;i<=NF;i++){ if($i ~ /^join:/){j=$i; sub(/^join:[ \t]*/,"",j)} else if($i ~ /^report:/){r=$i; sub(/^report:[ \t]*/,"",r)} }
        gsub(/^`|`[ \t]*$/,"",t); gsub(/^`|`[ \t]*$/,"",j); gsub(/^`|`[ \t]*$/,"",r)
        if (index(t,"{tests}") && r!="") print t "\t" j "\t" r }'
}
# The test id a case command fills a template with; fails when the command is not that template.
batch_id(){
  local cmd=$1 tpl=$2 pre suf id
  pre=${tpl%%\{tests\}*}; suf=${tpl#*\{tests\}}
  [[ $cmd == "$pre"* && $cmd == *"$suf" ]] || return 1
  id=${cmd#"$pre"}; id=${id%"$suf"}
  [[ -n $id && $id != *[[:space:],+*]* ]] || return 1   # one plain test id, not a list or a pattern
  printf '%s\n' "$id"
}
# JUnit XML → class<TAB>test<TAB>status<TAB>rep, one line per <testcase>. class is the full classname
# (two packages' OrderTest stay apart); test drops `(…)` and `[n]`; status 0 pass, 1 failure/error,
# 2 skipped; rep is 1 when the entry is a repetition of the same call — a bare name (go -count) or
# `name()[k]` (JUnit 5 @RepeatedTest) — and 0 for a parameterised one (`name(String)[k]`, `name[k]`):
# ten parameter sets are ten different calls, not ten repeats of one.
junit(){
  awk '
    # attr: an attribute by its exact name — `name=` must not match inside `classname=` (vitest
    # writes classname first)
    function attr(tag, k,   m) {
      if (match(tag, "[ \t]" k "=\"[^\"]*\"")) { m = substr(tag, RSTART, RLENGTH); sub(/^[ \t]*[^=]*="/, "", m); sub(/"$/, "", m); return m }
      return "" }
    function emit() { print c "\t" n "\t" st "\t" rp; open = 0 }
    # scan: children of the open testcase and its close tag, in whatever is left of a line
    function scan(t) {
      if (!open) return
      if (t ~ /<(failure|error)[ \t>\/]/) st = 1
      if (t ~ /<skipped[ \t>\/]/ && st == 0) st = 2
      if (t ~ /<\/testcase>/) emit() }
    {
      line = $0
      # CDATA is captured text (a log line reading `<error …>`), never markup: drop it, across lines too
      if (incd) { if ((i = index(line, "]]>")) == 0) next; line = substr(line, i + 3); incd = 0 }
      while ((i = index(line, "<![CDATA[")) > 0) {
        rest = substr(line, i + 9); j = index(rest, "]]>")
        if (j == 0) { line = substr(line, 1, i - 1); incd = 1; break }
        line = substr(line, 1, i - 1) substr(rest, j + 3) }
      # every testcase on the line, one after another: `<testcase …></testcase>` (gotestsum) and
      # `<testcase …><skipped/></testcase>` share one line
      while (match(line, /<testcase[ \t>][^>]*>/)) {
        scan(substr(line, 1, RSTART - 1))
        tag = substr(line, RSTART, RLENGTH); line = substr(line, RSTART + RLENGTH)
        c = attr(tag, "classname"); n = attr(tag, "name"); r = n; sub(/[\(\[].*/, "", n); r = substr(r, length(n) + 1)
        rp = (r == "" || r ~ /^\(\)\[[0-9]+\]$/) ? 1 : 0; st = 0; open = 1
        if (tag ~ /\/>$/) emit() }
      scan(line)
    }' "$@"
}

# A `Batch:` template guessed from commands that ran alone: their longest common prefix, cut back to
# the last delimiter (space, =, (, ', "), + {tests} + their longest common suffix, cut forward the
# same way. Prints nothing when the commands share no such shape.
suggest_template(){
  awk 'NR==1 { p=$0; s=$0; next }
       { while (index($0, p) != 1) p = substr(p, 1, length(p)-1)
         while (length(s) && substr($0, length($0)-length(s)+1) != s) s = substr(s, 2) }
       END { if (NR < 2) exit
             while (length(p) && substr(p, length(p)) !~ /[ =(\047"]/) p = substr(p, 1, length(p)-1)
             while (length(s) && substr(s, 1, 1) !~ /[ )\047"$]/) s = substr(s, 2)
             if (length(p) > 0) print p "{tests}" s }'
}
