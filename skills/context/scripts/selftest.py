#!/usr/bin/env python3
"""selftest.py — the smallest check that fails if `clio q`'s queries break."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from cliolib.testkit import clio, done, eq, git, lines, ok, out, read, scratch, write  # noqa: E402


def q(*a):
    return out("q", *a)


def field(s, k):
    return [str(json.loads(l)[k]) for l in lines(s)]


scratch()
I = ".claude/clio/database/index.jsonl"
D = ".claude/clio/database/debt.jsonl"
P = ".claude/clio/docs/plans/"
os.makedirs(".claude/clio/docs/plans")
os.makedirs(".claude/rules/api")

# a pre-3.0 record (no id) later claimed by id 100 through `supersedes`, then two runs of id 100
write(I, """{"date":"2026-01-01","type":"task","doc":"old/a.md","domain":"x","files":["a.go"],"commits":[],"keywords":["orders"],"req":[5],"specs":[]}
{"date":"2026-02-01","id":"100","type":"task","doc":"t/100_a.md","supersedes":"old/a.md","domain":"x","plan_tasks":["7.1"],"files":["a.go"],"commits":[],"keywords":["orders"],"req":["7.1"],"specs":[]}
{"date":"2026-03-01","id":"100","type":"task","doc":"t/100_a.md","domain":"x","plan_tasks":["7.1"],"files":["a.go","b.go"],"commits":[],"keywords":["orders"],"req":["7.1","7.10"],"specs":[]}
{"date":"2026-03-02","id":"200","type":"task","doc":"t/200_b.md","domain":"y","plan_tasks":["7.10"],"files":["c.go"],"commits":[],"keywords":["billing"],"req":["7.10"],"specs":["m/pay.md"]}
""")
write(D, """{"id":"d1","status":"pending","blocked_by":"PO answer","req":["7.1"],"what":["tax rule"],"domain":"x","specs":[]}
{"id":"d2","status":"pending","blocked_by":null,"req":["7.10"],"what":["rounding"],"domain":"y","specs":[]}
{"id":"d3","status":"pending","blocked_by":null,"req":["7.1"],"what":["old"],"domain":"x","specs":[]}
{"id":"d3","status":"done","blocked_by":null,"req":["7.1"],"what":["old"],"domain":"x","specs":[]}
""")

eq(len(lines(q("built"))), 2, "legacy record bridged into id 100, one line per doc")
eq(field(q("built", "--req", "7.1"), "id"), ["100"], "7.1 is not 7.10")
eq(sorted(field(q("built", "--req", "7.10"), "id")), ["100", "200"], "7.10 matches both docs once each")
eq(field(q("built", "--task", "7.10"), "id"), ["200"], "plan task as a string")
eq(len(lines(q("built", "--file", "b.go", "--area", "x"))), 1, "OR'd filters do not duplicate a doc")
eq(field(q("owed"), "id"), ["d2", "d1"], "queue first, done excluded")
eq(field(q("owed", "--req", "7.1"), "id"), ["d1"], "owed by row")
eq(field(q("owed", "--all", "--id", "d3"), "status"), ["done"], "--all sees closed records")
eq(json.loads(lines(q("history", "100"))[-1])["added"], ["b.go"], "history diff")
eq(q("summary").split("\n")[-1], "last memo: 2026-03-02 t/200_b.md", "summary last memo")

# summary's next task: a table plan gives id · task · levels; a bullet plan must not dump its whole line
HEAD = "| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n"
write(P + "tbl.md", HEAD + "| 3.1 | orders list | 3 | unit, api | – | – | [ ] |\n")
write(P + "blt.md", "- [ ] **1.16** File association registration for JPG/JPEG/PNG/WebP/GIF/TIFF/BMP, on the primary "
      "dev OS first, others tracked as follow-ups (req #30).\n")
s = q("summary")
ok(re.search(r"(?m)^tbl: done=0 open=1 next: 3\.1 \| orders list \| unit, api", s), "table plan next lost: " + s)
b = next((l for l in s.split("\n") if l.startswith("blt:")), "")
ok(len(b) <= 120, "bullet plan dumped whole: " + b)
# a pre-4.0 row superseded by its replacement counts as neither open nor done
write(P + "sup.md", "| # | Task | req | Test that proves it | Needs | Done |\n|---|---|---|---|---|---|\n"
      "| 3.2 | 401 | 3 | `go test` | – | superseded 2026-09-24 → 3.2.1 |\n\n" + HEAD + "| 3.2.1 | 401 | 3 | api | – | – | [ ] |\n")
s = q("summary")
ok(re.search(r"(?m)^sup: done=0 open=1 next: 3\.2\.1 ", s), "superseded row counted or replacement not next: " + s)
# next skips a row whose Needs are not ticked yet — across plans (0.4 lives in infra) — and says so
# when nothing is ready
write(P + "inf.md", HEAD + "| 0.4 | smoke suite | 0 | smoke | – | – | [ ] |\n")
write(P + "nd.md", HEAD + "| 4.1 | create | 4 | unit | 0.4 | – | [ ] |\n| 4.2 | list | 4 | api | 0.4, 4.1 | – | [ ] |\n")
s = q("summary")
ok(re.search(r"(?m)^nd: done=0 open=2 next: 4\.1 \| create \| unit \(waits on 0\.4\)", s), "unmet Needs not reported: " + s)
write(P + "inf.md", HEAD + "| 0.4 | smoke suite | 0 | smoke | – | – | [x] 2026-09-01 |\n")
s = q("summary")
ok(re.search(r"(?m)^nd: done=0 open=2 next: 4\.1 \| create \| unit$", s), "ready row not next: " + s)
for f in ("tbl", "blt", "sup", "inf", "nd"):
    os.remove(P + f + ".md")

write(D, "not json\n", "a")
ok("malformed" in clio("q", "owed")[2], "malformed line not reported")

write(".claude/rules/api/ts.md", '---\npaths:\n  - "src/api/**/*.ts"\n---\n- rule\n')
write(".claude/rules/all.md", "- always\n")
eq(q("rules", "src/api/v1/x.ts").count("api/ts.md"), 1, "path-scoped rule matched")
eq(q("rules", "README.md").count("api/ts.md"), 0, "path-scoped rule not matched")
eq(q("rules", "README.md").count("loads every session"), 1, "unscoped rule named")

write(I, "")
eq(q("summary").split("\n")[-1], "last memo: none yet", "empty index")

# --- git: which files changed, which commit holds them, which commits nobody recorded
eq(q("commit", "a.go"), "", "not a git repo → empty commit")
git("init", "-q")
git("config", "user.email", "t@t")   # the scratch repo only — spec-mark commits a snapshot
git("config", "user.name", "t")
eq(q("commit", "a.go"), "", "no commit yet → empty")
write("a.go", "1\n")
write("b c.go", "1\n")
write(".claude/x/y", "1\n")
eq(sorted(lines(q("changed"))), ["a.go", "b c.go"], "untracked listed, spaces intact, .claude/ excluded")
git("add", "a.go", "b c.go")
git("commit", "-qm", "one")
h1 = git("log", "-1", "--format=%h")
eq(q("commit", "a.go", "b c.go"), h1, "clean and committed → its hash")
write("a.go", "2\n", "a")
eq(q("commit", "a.go", "b c.go"), "", "part of the work uncommitted → empty, not HEAD")
git("mv", "b c.go", "d.go")
eq(sorted(lines(q("changed"))), ["a.go", "d.go"], "rename lists the new path only")
git("commit", "-qam", "two")
h2 = git("log", "-1", "--format=%h")
write(I, '{"date":"2026-03-03","id":"300","type":"task","doc":"t/300_x.md","domain":"x","plan_tasks":[],"files":["a.go"],'
      '"commits":["%s"],"keywords":["k"],"req":[],"specs":[]}\n' % h1, "a")
eq(q("unrecorded"), "%s\tt/300_x.md" % h2, "unrecorded stops at the recorded commit and names the doc")
git("add", "-A", ".claude")
git("commit", "-qm", "memo")
eq([l.split("\t")[0] for l in lines(q("unrecorded"))], [h2], "a .claude/-only commit is skipped")

# ingest baseline: a snapshot of the spec files, committed or not; the diff sees hand edits and new files
ok(clio("q", "spec-diff")[0] != 0, "spec-diff without a baseline must fail")
S = ".claude/clio/docs/specs/memory/"
write(S + "a.md", "limit: 5\n")
q("spec-mark")
eq(lines(q("spec-diff", "--stat")), [], "no edit since the mark")
write(S + "a.md", "limit: 10\n")
write(S + "b.md", "new\n")
eq(lines(q("spec-diff", "--name-only")), [S + "a.md", S + "b.md"], "uncommitted edit and untracked new spec both seen")
ok(re.search(r"(?m)^\+limit: 10", q("spec-diff")), "spec-diff lost the content")
q("spec-mark")
eq(lines(q("spec-diff", "--stat")), [], "re-mark moves the baseline")

# The baseline's own bookkeeping must never live inside a spec file — requirements.md sits in the
# same tree spec-diff hashes, so a line rewritten there on every mark would make it look "edited"
# on every single sweep, forever, with nothing actually changed.
R = ".claude/clio/docs/specs/requirements.md"
write(R, "# Requirements\n\n| # | Task | Spec file(s) | Decision status (NOT build status) |\n"
      "|---|---|---|---|\n| 1 | x | m | ✅ |\n")
q("spec-mark", "first ingest")
eq(lines(q("spec-diff", "--stat")), [], "requirements.md just marked shows no diff")
q("spec-mark", "re-marked, nothing changed")
eq(lines(q("spec-diff", "--stat")), [], "marking again with no spec edit still shows nothing changed")
write(R, read(R) + "| 2 | y | m | ⚠️ |\n")
eq(lines(q("spec-diff", "--name-only")), [R], "a real edit to requirements.md itself is still seen")
q("spec-mark", "picked up the new row")
eq(lines(q("spec-diff", "--stat")), [], "baseline moved again")

write(".claude/rules/rb.md", '---\npaths: ["lib/**/*.rb", "app/*.rb"]\n---\n- r\n')
eq(q("rules", "app/x.rb").count("rb.md"), 1, "inline paths: list parsed")

done()
