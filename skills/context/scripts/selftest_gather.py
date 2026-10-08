#!/usr/bin/env python3
"""selftest_gather.py — `clio q gather`: step 1 of /clio:memo, the case (A–D) computed from git and the ledgers."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from cliolib.testkit import done, git, ok, out, scratch, write  # noqa: E402

scratch()
git("init", "-q")
for d in ("database/plan", "database/test", "docs/specs", "docs/tasks/feat"):
    os.makedirs(".claude/clio/" + d)
write(".claude/clio/docs/specs/requirements.md", "| # | Task | Spec | Status |\n|---|---|---|---|\n| 1 | Orders list | [memory/o.md](memory/o.md) | ✅ |\n")
DOC = ".claude/clio/docs/tasks/feat/1700000001_orders.md"
write(DOC, "# Orders\n")
write("src/a.go", "a\n")
git("add", "src/a.go")
git("commit", "-qm", "base")
base = git("rev-parse", "--short", "HEAD")


def index(*recs):
    write(".claude/clio/database/index.jsonl", "".join(json.dumps(r) + "\n" for r in recs))


def rec(i, doc, tasks, files, commits):
    return {"date": "2026-10-01", "id": i, "type": "task", "doc": doc, "domain": "x", "plan_tasks": tasks, "files": files, "commits": commits,
            "keywords": ["orders"], "req": ["1"], "specs": []}


def task(tid, status="open"):
    return json.dumps({"type": "task", "id": tid, "date": "2026-10-01", "task": "t " + tid, "req": ["1"], "levels": ["unit"], "critical": False, "tier": "full",
                       "needs": [], "touches": [], "na": {}, "status": status, "by": None, "commit": None, "delta": None}) + "\n"


write(".claude/clio/database/plan/a.jsonl", task("1.1", "done") + task("1.2"))
index(rec("1700000001", DOC, ["1.1"], ["src/a.go"], [base]))
g = lambda *a: out("q", "gather", *a)

# nothing changed, nothing unrecorded: stop
r = g()
ok("nothing to record" in r and "unrecorded commits (0)" in r, "nothing new: " + r)

# Case A — a path target: exists → UPDATE; missing → stop and ask
ok("A — path target: EXISTS → UPDATE" in g(DOC), "case A exists: " + g(DOC))
ok("MISSING → stop and ask" in g(".claude/clio/docs/tasks/feat/typo.md"), "case A missing")

# Case B — task target: owned → UPDATE; sub-task of an owned task → the parent's doc; planned, no doc → CREATE; unplanned → stop
ok("B — task 1.1: a doc owns it → UPDATE" in g("1.1") and "1700000001_orders.md" in g("1.1"), "case B owned: " + g("1.1"))
ok("sub-task of 1.1 → UPDATE the parent's doc" in g("1.1.1") and "1700000001_orders.md" in g("1.1.1"), "case B sub-task: " + g("1.1.1"))
ok("no doc → CREATE" in g("1.2"), "case B create: " + g("1.2"))
ok("in no plan → stop and ask" in g("9.9"), "case B unplanned: " + g("9.9"))

# Case C — no target, uncommitted files: the docs that cover them
write("src/a.go", "changed\n")
r = g()
ok("changed (1)" in r and "C — no target: 1 doc(s) already cover changed files" in r and "1700000001_orders.md" in r, "case C: " + r)
write("src/new.go", "n\n")
ok("src/new.go" in g(), "an untracked file is listed")
os.remove("src/new.go")
git("checkout", "--", "src/a.go")

# Case D — committed work that a record names without its hash: backfill; a commit nobody recorded: Case C
write("src/a.go", "second\n")
git("commit", "-qam", "second")
index(rec("1700000001", DOC, ["1.1"], ["src/a.go"], [base]))     # records the first commit only
r = g()
ok("unrecorded commits (1)" in r and "docs: .claude/clio/docs/tasks/feat/1700000001_orders.md" in r and "D — nothing uncommitted and every unrecorded commit names its docs" in r, "case D: " + r)
write("other.txt", "o\n")
git("add", "other.txt")
git("commit", "-qm", "unowned")
r = g()
ok("(nobody recorded it)" in r and "C — nothing uncommitted, but commit(s)" in r, "an unowned commit: " + r)

# the commit of files, the vocabulary
ok("keyword vocabulary (reuse these exact words): orders" in r, "keywords: " + r)

# domains, and the work's own rows and debt found from the changed files' shared word (no target)
write(".claude/clio/docs/specs/requirements.md",
      "Domains — the only values\nnever by directory: `orders` `infra`\n\n| # | Task | Spec | Status |\n|---|---|---|---|\n"
      "| 1 | Orders list | [memory/o.md](memory/o.md) | ✅ |\n| 2 | Own volume, apart from the system | [memory/p.md](memory/p.md) | ⚠️ |\n"
      "| 3 | Player panel | [memory/p.md](memory/p.md) | ✅ |\n")
write(".claude/clio/database/debt.jsonl", json.dumps({"id": "vol-open", "kind": "unverified", "status": "open", "what": ["volume unchecked"], "domain": "orders"}) + "\n")
write("src/volume.go", "v\n")
write("src/volume_keys.go", "k\n")
r = g()
ok("domains (a record's `domain` is one of these; a new one → ask): orders, infra" in r, "domains: " + r)
ok("requirement rows that may be this work's (volume)" in r and "  2      Own volume" in r and "Player panel" not in r, "rows from shared words: " + r)
ok("open debt that mentions volume (1)" in r and "vol-open" in r, "debt from shared words: " + r)

# a word target: the docs whose keywords carry it
r = g("orders")
ok("C — word target: " in r and "1700000001_orders.md" in r, "word target: " + r)
ok("no doc carries the keyword → CREATE" in g("nothingmatches"), "word target, no doc")
done()
