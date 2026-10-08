#!/usr/bin/env python3
"""clio add <plan|test> <area> — the one way into .claude/clio/database/{plan,test}/<area>.jsonl.
Reads JSON records from stdin, one per line. A record names only what it sets: it is merged onto the
current record of its (type, id), so `{"type":"task","id":"3.1","status":"void"}` is a whole update.
Every record is checked first; one bad record and nothing is written.
  plan types: task, mutation      test types: case, meta
Python 3.9+, standard library only."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from cliolib import common as c  # noqa: E402
from cliolib import store  # noqa: E402

USAGE = "usage: clio add <plan|test> <area>  <<'EOF'\n{...}\nEOF"


def main(argv):
    if len(argv) != 2 or argv[0] not in ("plan", "test"):
        print(USAGE, file=sys.stderr)
        return 1
    root = c.find_root()
    if not root:
        print("FAIL: no .claude/clio above %s — run /clio:setup" % os.getcwd())
        return 1
    os.chdir(root)
    parts, errs = [], []
    for n, line in enumerate(sys.stdin.read().split("\n"), 1):
        if line.strip() == "":
            continue
        try:
            parts.append(c.loads(line))
        except ValueError as e:
            errs.append("line %d is not valid JSON (%s) — one record per line" % (n, e))
    if not parts and not errs:
        errs.append("no records on stdin")
    if not errs:
        errs, written = store.write(argv[0], argv[1], parts)
    for e in errs:
        print("FAIL: " + e)
    if errs:
        print("nothing written")
        return 1
    for r in written:
        what = r.get("status") or r.get("tool") or ""
        print("added: %s %s%s" % (r["type"], c.tostring(r.get("id", "")), " (%s)" % what if what else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
