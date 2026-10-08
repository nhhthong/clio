#!/usr/bin/env python3
"""selftest_add.py — `clio add index|debt`: merge onto the old record, append, validate those lines, and
undo the append on a FAIL, so a ledger never holds a line `clio validate` refuses."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from cliolib.testkit import clio, done, eq, ok, read, scratch, write  # noqa: E402

scratch()
os.makedirs(".claude/clio/database")
os.makedirs(".claude/clio/docs/specs")
os.makedirs(".claude/clio/docs/tasks/f")
write(".claude/clio/docs/specs/requirements.md", "| # | Task | Spec | Status |\\n|---|---|---|---|\\n| 1 | x | m | ✅ |\\n"
      "| 2 | y | [memory/y.md](memory/y.md) | ✅ |\\n".replace("\\n", "\n"))
write(".claude/clio/docs/tasks/f/1700000001_a.md", "x\n")
IDX, DEBT = ".claude/clio/database/index.jsonl", ".claude/clio/database/debt.jsonl"
write(IDX, "")
write(DEBT, "")


def add(kind, *recs, raw=None):
    rc, o, _ = clio("add", kind, input=raw if raw is not None else "".join(json.dumps(r) + "\n" for r in recs))
    return rc, o


def last(path):
    return json.loads(read(path).strip().split("\n")[-1])


# debt: a new record names only its own fields; the rest starts empty and `date` is today
rc, o = add("debt", {"id": "d1", "kind": "code-debt", "domain": "x", "what": ["w"], "req": ["1"]})
ok(rc == 0 and "added: debt d1 (pending)" in o, "new debt: %s %s" % (rc, o))
r = last(DEBT)
eq((r["status"], r["blocked_by"], r["docs"], len(r)), ("pending", None, [], 14), "defaults fill the 14 fields")

# an update names only what changes; nothing else is erased
rc, o = add("debt", {"id": "d1", "status": "done"})
r = last(DEBT)
ok(rc == 0 and r["status"] == "done" and r["what"] == ["w"] and r["req"] == ["1"] and r["kind"] == "code-debt", "update erased fields: %s" % r)

# a bad record is refused AND the file is untouched
before = read(DEBT)
rc, o = add("debt", {"id": "d2", "kind": "nonsense", "domain": "x", "what": ["w"]})
ok(rc != 0 and "nothing written" in o and "FAIL" in o, "bad kind accepted: %s" % o)
eq(read(DEBT), before, "a refused debt record stayed in the file")
rc, o = add("debt", {"id": "d3", "kind": "spec-blocked", "domain": "x", "what": ["w"]})      # filing a spec-blocked needs blocked_by
ok(rc != 0 and "blocked_by" in o, "a spec-blocked filed without a blocker: %s" % o)
eq(read(DEBT), before, "the refused spec-blocked stayed")
rc, o = add("debt", {"kind": "code-debt", "domain": "x", "what": ["w"]})
ok(rc != 0 and "needs an id" in o, "debt without an id: %s" % o)
rc, o = add("debt", raw="{broken\n")
ok(rc != 0 and "not valid JSON" in o, "broken JSON: %s" % o)

# index: a new doc gets its creation id; the doc must exist
rc, o = add("index", {"type": "task", "doc": ".claude/clio/docs/tasks/f/1700000001_a.md", "domain": "x", "keywords": ["k"], "req": ["1"],
                       "files": ["a.go"], "id": "1700000001"})
ok(rc == 0, "new index record: %s" % o)
before = read(IDX)
rc, o = add("index", {"type": "task", "doc": ".claude/clio/docs/tasks/f/missing.md", "domain": "x", "keywords": ["k"], "id": "1700000002"})
ok(rc != 0 and "missing file" in o, "an index record for a missing doc: %s" % o)
eq(read(IDX), before, "the refused index record stayed")

# an index update keeps what it does not name, and replaces a list whole
rc, o = add("index", {"id": "1700000001", "commits": ["abc1234"]})
r = last(IDX)
ok(rc == 0 and r["commits"] == ["abc1234"] and r["files"] == ["a.go"] and r["doc"].endswith("_a.md"), "index update: %s" % r)

# several records, one of them bad: none is written
before = read(DEBT)
rc, o = add("debt", {"id": "d4", "kind": "code-debt", "domain": "x", "what": ["w"]}, {"id": "d5", "kind": "bogus", "domain": "x", "what": ["w"]})
ok(rc != 0, "a batch with a bad record was written")
eq(read(DEBT), before, "the good half of a refused batch stayed")

# a file whose last line has no newline is not glued to
write(DEBT, read(DEBT).rstrip("\n"))
rc, o = add("debt", {"id": "d6", "kind": "code-debt", "domain": "x", "what": ["w"]})
lines = [l for l in read(DEBT).split("\n") if l]
ok(rc == 0 and all(json.loads(l) for l in lines), "glued onto an unterminated line")

# a number stays as written (7.10 is not 7.1)
rc, o = add("debt", raw='{"id":"d7","kind":"code-debt","domain":"x","what":["w"],"req":["1"],"note":7.10}\n')
ok("7.10" in read(DEBT), "a decimal was rewritten")


# no id → the doc's filename prefix; req without specs → the spec file requirements.md maps the row to
write(".claude/clio/docs/tasks/f/1700000009_b.md", "x\n")
write(".claude/clio/docs/specs/memory/y.md", "# y\n")
rc, o = add("index", {"type": "task", "doc": ".claude/clio/docs/tasks/f/1700000009_b.md", "domain": "x", "keywords": ["k"], "req": ["2"], "files": ["b.go"]})
r = last(IDX)
ok(rc == 0 and r["id"] == "1700000009", "id from the doc's filename: %s %s" % (o, r))
ok(r["specs"] == [".claude/clio/docs/specs/memory/y.md"], "specs from req: %s" % r)
rc, o = add("index", {"id": "1700000009", "specs": []})
ok(rc == 0 and last(IDX)["specs"] == [], "specs given explicitly are kept: %s" % last(IDX))
done()
