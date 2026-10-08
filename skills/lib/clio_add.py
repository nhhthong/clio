#!/usr/bin/env python3
"""clio add <plan|test> <area> | index | debt — the way into Clio's ledgers.
Reads JSON records from stdin, one per line. A record names only what it sets: it is merged onto the
current record with the same key, so `{"type":"task","id":"3.1","status":"void"}` or
`{"id":"seekbar-unverified","status":"done"}` is a whole update — no field is erased by leaving it out.
  plan types: task, mutation      test types: case, meta
  index, debt: keyed by `id`; a new record names what is its own (kind, domain, what… — the optional
  fields start empty), `date` defaults to today, an index record without an `id` takes its doc's filename prefix (the creation id),
  and a record with `req` but no `specs` gets the spec files requirements.md maps those rows to. Lists are
  replaced whole, so an update of `files` or `commits` gives the full new list.
Every record is checked first; one bad record and nothing is written. For index and debt the line is
appended, `clio validate` runs on exactly those lines, and a FAIL truncates the file back — the write and
its check are one command, not a heredoc, a validate and a `sed` to undo.
Python 3.9+, standard library only."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from cliolib import common as c  # noqa: E402
from cliolib import store  # noqa: E402

USAGE = "usage: clio add <plan|test> <area>  or  clio add <index|debt>   <<'EOF'\n{...}\nEOF"


LEDGER = {"index": ".claude/clio/database/index.jsonl", "debt": ".claude/clio/database/debt.jsonl"}
# What a NEW record starts from, so it names only what is its own. An update starts from the old record.
DEFAULTS = {
    "debt": {"status": "pending", "req": [], "specs": [], "docs": [], "code": [], "action": "", "source": None,
             "blocked_by": None, "issue": None},
    "index": {"plan_tasks": [], "files": [], "commits": [], "req": [], "specs": []},
}


REQ = ".claude/clio/docs/specs/requirements.md"


def row_specs():
    """{row number: spec path} from the requirements table, the path as the ledgers write it."""
    out = {}
    try:
        lines = open(REQ, encoding="utf-8").read().split("\n")
    except OSError:
        return out
    for line in lines:
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
        m = re.search(r"\((memory/[^)]+\.md)\)", line)
        if line.lstrip().startswith("|") and m and cells and re.fullmatch(r"[0-9]+(\.[0-9]+)*", cells[0]):
            out[cells[0]] = ".claude/clio/docs/specs/" + m.group(1)
    return out


def validate(kind, n):
    """`clio validate <kind> <n>` in this process (a second interpreter costs more than the check): (ok, output)."""
    import contextlib
    import io
    import runpy
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "memo", "scripts", "validate.py")
    buf, code = io.StringIO(), 0
    cwd = os.getcwd()
    with contextlib.redirect_stdout(buf):
        try:
            runpy.run_path(path, run_name="clio_validate")["main"]([kind, str(n)])
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
    os.chdir(cwd)
    return code == 0, buf.getvalue()


def add_ledger(kind, parts):
    """Merge, append and validate the records of index.jsonl or debt.jsonl; roll back on a FAIL."""
    import datetime
    import time
    path = LEDGER[kind]
    prev = {}
    for r in c.read_valid(path):
        if isinstance(r, dict) and c.truthy(r.get("id")):
            prev[c.tostring(r["id"])] = r
    out, errs, specs_of = [], [], None
    for n, part in enumerate(parts, 1):
        if not isinstance(part, dict):
            errs.append("record %d: not a JSON object" % n)
            continue
        part = dict(part)
        if not c.truthy(part.get("id")):
            if kind == "index":
                m = re.match(r"(\d+)_", os.path.basename(c.tostring(part.get("doc") or "")))
                part["id"] = m.group(1) if m else str(int(time.time()))     # the doc's creation id
            else:
                errs.append("record %d: a debt record needs an id" % n)
                continue
        rid = c.tostring(part["id"])
        base = prev.get(rid) or dict(DEFAULTS[kind])
        rec = dict(base)
        rec.update(part)
        if "specs" not in part and not c.items(rec.get("specs")) and c.items(rec.get("req")):
            if specs_of is None:
                specs_of = row_specs()
            rec["specs"] = sorted({specs_of[x] for x in (c.tostring(r) for r in c.items(rec["req"])) if x in specs_of and os.path.isfile(specs_of[x])})
        if "date" not in part:
            rec["date"] = datetime.date.today().strftime("%Y-%m-%d")
        if "id" in rec:
            rec["id"] = rid
        prev[rid] = rec
        out.append(rec)
    if errs:
        return errs, []
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a+", encoding="utf-8", errors="surrogateescape") as f:
        store._lock(f)
        f.seek(0, 2)
        before = f.tell()
        if before:
            f.seek(before - 1)
            if f.read(1) != "\n":                       # never glue a record onto an unterminated line
                f.write("\n")
                before += 1
        f.write("".join(c.dumps(r) + "\n" for r in out))
        f.flush()
        ok, text = validate(kind, len(out))
        if not ok:
            f.truncate(before)
            return [l[len("FAIL: "):] if l.startswith("FAIL: ") else l for l in text.splitlines()
                    if l.startswith("FAIL") or l.startswith("usage")] or [text.strip()], []
    return [], out


def main(argv):
    ledger = len(argv) == 1 and argv[0] in LEDGER
    if not (ledger or (len(argv) == 2 and argv[0] in ("plan", "test"))):
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
        errs, written = add_ledger(argv[0], parts) if ledger else store.write(argv[0], argv[1], parts)
    for e in errs:
        print("FAIL: " + e)
    if errs:
        print("nothing written")
        return 1
    for r in written:
        what = r.get("status") or r.get("tool") or r.get("kind") or ""
        print("added: %s %s%s" % (r.get("type") or argv[0], c.tostring(r.get("id", "")), " (%s)" % what if what else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
