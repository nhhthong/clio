#!/usr/bin/env python3
"""selftest_doc.py — `clio doc`: the WRITE-DOC rules applied by a script, not remembered by a model."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from cliolib.testkit import clio, done, eq, ok, read, scratch  # noqa: E402

scratch()
os.makedirs(".claude/clio/database")


def doc(**req):
    rc, o, _ = clio("doc", input=json.dumps(req))
    return rc, o


rc, o = doc(feature="ui", name="panel-width", plan_tasks=["3.5.7"], summary="The panel is 47 columns.", files=["internal/ui/p.go — PanelWidth = 47"],
            decisions=["47 is the header width."], testing=["OK: task 3.5.7"], feature_what="The screen.", domain="ui")
ok(rc == 0 and "created" in o, "new doc: %s" % o)
path = re.search(r"doc: (\S+)", o).group(1)
ident = re.search(r"id: (\d+)", o).group(1)
ok(os.path.basename(path) == ident + "_panel-width.md", "the id is the filename prefix: %s" % path)
text = read(path)
for want in ("# Panel Width", "Plan tasks: 3.5.7", "## Summary\nThe panel is 47 columns.", "- `internal/ui/p.go` — PanelWidth = 47", "- 47 is the header width.",
             "## Side Effects\n- none", "- Wait" if False else "## Follow-up\n- none", "## Change Log\n- "):
    ok(want in text, "new doc lacks [%s]:\n%s" % (want, text))
ok(re.search(r"## Testing Done\n- \d{4}-\d{2}-\d{2} — OK: task 3.5.7", text), "testing is dated: " + text)
ok(os.path.isfile(os.path.dirname(path) + "/summary.md") and "## General Memory" in read(os.path.dirname(path) + "/summary.md"), "the feature summary")

# an update only appends: nothing already written is lost, Follow-up is the one replaced section
before = read(path).split("\n")
rc, o = doc(doc=path, plan_tasks=["5.8.1", "3.5.7"], commit="abc1234", files=["internal/ui/p.go — bar follows", "internal/app/s_test.go — 45 cells"],
            decisions=["Superseded: now 40."], side_effects=["Six tests fail."], follow_up=["Try it on a real terminal."], changelog="widened")
ok(rc == 0 and "updated" in o, "update: %s" % o)
after = read(path)
for line in before:
    if line.strip() and not line.startswith(("Updated:", "Commit:", "Plan tasks:", "- none", "- `internal/ui/p.go`")):
        ok(line in after.split("\n"), "an update lost a line: [%s]" % line)
ok("Plan tasks: 3.5.7, 5.8.1" in after and "Commit: abc1234" in after, "header accumulates: " + after)
ok("- `internal/ui/p.go` — PanelWidth = 47; bar follows (" in after and "- `internal/app/s_test.go` — 45 cells" in after, "files merge: " + after)
ok(re.search(r"## Side Effects\n- none\n- \d{4}-\d{2}-\d{2} — Six tests fail\.", after), "side effects are dated and appended: " + after)
ok("## Follow-up\n- Try it on a real terminal." in after and "(commit abc1234)" in after, "follow-up replaced, changelog line")
rc, o = doc(doc=path, commit="abc1234", follow_up=[])
ok("## Follow-up\n- none" in read(path) and read(path).count("abc1234") == after.count("abc1234"), "an empty follow-up says none; the same commit is not added twice")

# a section can be relabelled; the body stays
rc, o = doc(doc=path, relabel=["Summary", "Decisions"])
r = read(path)
ok(re.search(r"## \[SUPERSEDED \d{4}-\d{2}-\d{2}\] Summary — REVERTED, DO NOT RE-IMPLEMENT\nThe panel is 47 columns\.", r), "relabel keeps the body: " + r)
rc, o = doc(doc=path, relabel=["Summary"], decisions=["x"])
ok(read(path).count("[SUPERSEDED") == 2, "relabelling twice stacks labels")

# refusals
ok(doc(doc=".claude/clio/docs/tasks/ui/9_missing.md", changelog="x")[0] != 0, "a missing doc was created")
ok(doc(feature="ui", name="Bad Name")[0] != 0, "a bad name accepted")
ok(doc(feature="ui", name="x", bogus=1)[0] != 0, "an unknown key accepted")
ok(doc(feature="ui", name="panel-width", id=ident)[0] != 0, "an id collision accepted")
rc, o = doc(doc=path, relabel=["Nonexistent"])
ok(rc != 0 and "no section" in o, "relabel of a missing section: " + o)

# an update keeps the Summary, with a note, unless summary_replace
rc, o = doc(doc=path, summary="Another summary.")
ok(rc == 0 and "note: summary kept" in o and "The panel is 47 columns." in read(path), "summary kept: " + o)
rc, o = doc(doc=path, summary="The panel is 50 columns.", summary_replace=True)
ok(rc == 0 and "The panel is 50 columns." in read(path) and "The panel is 47 columns." not in read(path), "summary replaced: " + read(path))

# light: the header, a summary and the change log, nothing else
rc, o = doc(feature="ui", name="mascot-note", plan_tasks=["9.1"], summary="A note moves.", light=True)
lp = re.search(r"doc: (\S+)", o).group(1)
ok(read(lp).count("## ") == 2 and "## Summary" in read(lp) and "## Change Log" in read(lp), "light doc: " + read(lp))
done()
