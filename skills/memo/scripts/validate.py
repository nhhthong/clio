#!/usr/bin/env python3
"""validate.py [index [N]|debt [N]|all] — run from anywhere inside a project that has .claude/clio/
  index  validate the last N lines appended to index.jsonl (default 1) — N = how many you just appended
  debt   validate the last N lines appended to debt.jsonl (default 1)
  all    repo-wide audit (the "coverage" hop nothing else computes)
Exit 1 if any FAIL. WARN and INFO never fail the run."""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from cliolib import common as c  # noqa: E402
from cliolib import store  # noqa: E402
from cliolib import tables  # noqa: E402

IDX = ".claude/clio/database/index.jsonl"
DEBT = ".claude/clio/database/debt.jsonl"
RUNS = ".claude/clio/database/runs.jsonl"
REQ = ".claude/clio/docs/specs/requirements.md"
PLANS = store.PLAN_DIR
TESTS = store.TEST_DIR
# Every field the schema files say is always present (null / [] allowed, absence is not).
IDX_FIELDS = "date id type doc domain plan_tasks files commits keywords req specs".split()                  # INDEX-IT.md
DEBT_FIELDS = "date id kind status domain what req specs docs code action source blocked_by issue".split()  # DEBT-IT.md, all 14
KINDS = ("code-debt", "unverified", "doc-stale", "spec-delta", "spec-blocked")
STATUSES = ("pending", "in-process", "done")

fails = 0


def fail(msg):
    global fails
    print("FAIL: " + msg)
    fails += 1


def warn(msg):
    print("WARN: " + msg)


def info(msg):
    print("INFO: " + msg)


# ponytail: one global the `all` mode flips to warn. A record written before 2.1 may lack a field;
# the fix is appending a full record under the same key (readers take the last line), so an audit
# names it and moves on, while the write path (`index` / `debt` mode) refuses the line outright.
sev = fail


def length(v):
    """jq's length: null 0, a number its magnitude, a string/array/object its size; a boolean has none."""
    if v is None:
        return 0
    if isinstance(v, bool):
        return None
    if isinstance(v, (str, list, dict)):
        return len(v)
    return abs(v)


def parse(line):
    try:
        return c.loads(line)
    except ValueError:
        return None


# req row numbers and plan task ids, parsed once
rows = []
tasks = []
planrows = []


def check_req_type(ledger, r):
    # `req` holds requirement row numbers as strings: as JSON numbers 7.1 and 7.10 are the same value.
    # Write path refuses a number; `all` names pre-4.0 records, which `clio q` still reads via tostring.
    req = r.get("req") if c.truthy(r.get("req")) else []
    good = isinstance(req, (list, dict)) and all(isinstance(x, str) for x in c.items(req))
    if not good:
        sev(ledger + ' .req holds a number — write row numbers as strings ("7.10", not 7.10)')


def check_fields(ledger, fields, r):
    missing = [f for f in fields if f not in r]
    if missing:
        sev("%s record is missing: %s — append a full record, readers take the last line" % (ledger, " ".join(missing)))


def check_req(ledger, r):
    for n in c.items(r.get("req")):
        n = c.tostring(n)
        if n != "" and n not in rows:
            fail("%s .req %s has no requirements.md row" % (ledger, n))


def check_plan_tasks(ledger, r):
    # an id naming no plan row sends /clio:memo to tick the wrong one
    if not tasks:
        return
    for t in c.items(r.get("plan_tasks")):
        t = c.tostring(t)
        if t != "" and t not in tasks:
            fail("%s .plan_tasks %s is in no %s/*.jsonl task" % (ledger, t, PLANS))


def check_specs(ledger, r):
    for p in c.items(r.get("specs")):
        p = c.tostring(p)
        if p != "" and not os.path.isfile(p):
            fail("%s .specs missing: %s" % (ledger, p))


def index_shape_ok(r):
    if not isinstance(r, dict):
        return False
    kw = length(r.get("keywords"))
    return (c.truthy(r.get("date")) and c.truthy(r.get("doc")) and kw is not None and kw > 0
            and r.get("type") in ("task", "adr")
            and isinstance(r.get("files"), list) and isinstance(r.get("commits"), list)
            and isinstance(r.get("req"), list) and isinstance(r.get("specs"), list)
            and (isinstance(r.get("plan_tasks"), list) or "plan_tasks" not in r))


def check_chore(r):
    """A commit no task owns (CI, tooling), said so once by the user through /clio:memo: id is the hash."""
    ok = (isinstance(r.get("commits"), list) and len(r["commits"]) > 0 and c.truthy(r.get("date"))
          and c.truthy(r.get("id")) and isinstance(r.get("note"), str) and r["note"].strip() != "")
    if not ok:
        fail("index chore record needs date, id, a non-empty commits list and a note saying why no task owns it")
    return ok


def check_index_line(r, idxjson=None):
    """One index record; idxjson (every parseable record) exists only in `all` mode."""
    if isinstance(r, dict) and r.get("type") == "chore":
        return check_chore(r)
    if not index_shape_ok(r):
        fail("index line missing a required field, bad type, or not valid JSON")
        return False
    check_fields("index", IDX_FIELDS, r)
    check_req_type("index", r)
    doc = c.tostring(r.get("doc"))
    # A migrated doc leaves its pre-3.0 records keyed on the old path, which is now gone. `all` mode's
    # own sweep reports those as INFO once it finds the record that supersedes them — so only FAIL
    # here when nothing does. idxjson is None in `index` mode, so the write path stays strict.
    if not os.path.isfile(doc):
        if not any(isinstance(x, dict) and x.get("supersedes") == doc for x in (idxjson or [])):
            fail("index .doc points at a missing file: " + doc)
    # `id` is the doc's creation timestamp AND its filename prefix (INDEX-IT.md). Enforcing the
    # binding is what stops two docs sharing one id: a collision leaves the losing file on disk with
    # no record of its own, which the orphan check below then names. Only for the two directories
    # whose filenames Clio chooses — a ledger may also index a spec or a rules file, and those are
    # named by content.
    rid = c.tostring(r["id"]) if c.truthy(r.get("id")) else ""
    if doc.startswith((".claude/clio/docs/tasks/", ".claude/clio/docs/decisions/")):
        if rid and not doc.rsplit("/", 1)[-1].startswith(rid + "_"):
            fail("index .id %s is not the filename prefix of %s" % (rid, doc))
    check_specs("index", r)
    check_req("index", r)
    check_plan_tasks("index", r)
    return True


def check_debt_line(r):
    ok = (isinstance(r, dict) and c.truthy(r.get("id"))
          and (length(r.get("what")) or 0) > 0
          and r.get("kind") in KINDS and r.get("status") in STATUSES
          and isinstance(r.get("req"), list) and isinstance(r.get("specs"), list)
          and isinstance(r.get("code"), list) and "blocked_by" in r)
    if not ok:
        fail("debt line missing a required field, bad kind/status, or not valid JSON")
        return False
    check_fields("debt", DEBT_FIELDS, r)
    check_req_type("debt", r)
    check_specs("debt", r)
    check_req("debt", r)
    return True


def check_filed_blocked(debt, only=""):
    """The record that FILES a spec-blocked must name its blocker; a later record may legitimately
    null it once the answer lands (DEBT-IT.md § 1). So the rule is judged on each id's FIRST record,
    never its last — one function, called by both modes, so `all` cannot report the same id twice."""
    if not all(isinstance(r, dict) for r in debt):
        return
    for g in c.group_by(debt, lambda r: r.get("id")):
        first = g[0]
        if only != "" and first.get("id") != only:
            continue
        if first.get("kind") == "spec-blocked" and first.get("blocked_by") is None:
            fail("debt %s: the record that files a spec-blocked needs a non-null blocked_by" % c.tostring(first.get("id")))


def last_lines(path, n):
    """The last n lines of a ledger — the records one append just wrote."""
    lines = [l for _, l in numbered(path)]
    return lines[-n:] if n > 0 else []


def numbered(path):
    with open(path, encoding="utf-8", errors="surrogateescape") as f:
        text = f.read()
    lines = text.split("\n")
    if text.endswith("\n"):
        lines.pop()
    return list(enumerate(lines, 1))


def parseable(path):
    """jq -Rc 'fromjson? // empty': the lines that parse, null and false dropped."""
    if not os.path.isfile(path):
        return []
    return [v for _, l in numbered(path) for v in [parse(l)] if c.truthy(v)]


def by_doc_id(recs):
    """One group per document, across the 3.0 id migration. Pre-3.0 records have no `id` and key on
    their path, so without the bridge they form a second group whose last record is the old short one
    — and a finished migration would keep reporting the very fields it just supplied. The bridge maps
    a path to the id that later claimed it, by `doc` (the doc stayed put) or by `supersedes` (it
    moved), so the legacy records land in their successor's group and `last` picks the full record."""
    m = {}
    for r in recs:
        if c.truthy(r.get("id")):
            m[r.get("doc")] = r.get("id")
    for r in recs:
        if c.truthy(r.get("id")) and c.truthy(r.get("supersedes")):
            m[r.get("supersedes")] = r.get("id")

    def key(r):
        for v in (r.get("id"), m.get(r.get("doc")), r.get("doc")):
            if c.truthy(v):
                return v
        return r.get("doc")
    return c.group_by(recs, key)


def audit():
    global sev
    for f in (IDX, DEBT):
        if not os.path.isfile(f):
            fail("missing " + f)
            continue
        for n, l in numbered(f):
            if l == "":
                continue
            if not c.truthy(parse(l)):
                fail("%s line %d is not valid JSON" % (f, n))
    # a malformed line (already FAILed above) must not misfire every check below
    idxjson = [r for r in parseable(IDX) if isinstance(r, dict)]
    debtjson = [r for r in parseable(DEBT) if isinstance(r, dict)]

    sev = warn    # audit: a pre-2.1 record missing a field is named, not failed (see check_fields)
    groups = by_doc_id(idxjson)
    for g in groups:
        check_index_line(g[-1], idxjson)
    for g in c.group_by(debtjson, lambda r: r.get("id")):
        check_debt_line(g[-1])

    check_filed_blocked(debtjson)

    # 2.0: a doc's last record is its full state — it must still name every file an earlier record had.
    # Only pre-2.0 records (scalar `commit`, or no `commits`) need migrating; a clean 2.0 doc may
    # legitimately drop a reverted file (INDEX-IT.md § files), so don't nag about that.
    for g in groups:
        if len(g) > 1 and any("commit" in r or "commits" not in r for r in g):
            earlier = {c.dumps(x) for r in g for x in c.items(r.get("files"))}
            now = {c.dumps(x) for x in c.items(g[-1].get("files") or [])}
            if earlier - now:
                warn("index: last record of %s drops files earlier records had — pre-2.0 delta ledger? migrate per CHANGELOG 2.0.0"
                     % c.tostring(g[0].get("doc")))

    # orphan docs — on disk, never indexed. Recursive: task docs live in tasks/<feature>/ since 3.0,
    # and a non-recursive glob would make every one of them invisible to this check.
    indexed = {r.get("doc") for r in idxjson}
    for d in (sorted(glob.glob(".claude/clio/docs/tasks/**/*.md", recursive=True))
              + sorted(glob.glob(".claude/clio/docs/decisions/**/*.md", recursive=True))):
        if os.path.basename(d) == "summary.md":          # feature-level blurb, never an indexed doc
            continue
        if d not in indexed:
            warn("orphan doc, no index record: %s — /clio:memo was skipped" % d)
    # pre-3.0 records (no id) pointing at docs that no longer exist without a supersedes trail. A record
    # with an id is judged on its group's last line (above): its earlier lines keep the path the doc
    # had then, which is history, not a broken link.
    for doc in sorted({c.tostring(r.get("doc")) for r in idxjson if not c.truthy(r.get("id"))}):
        if doc == "" or os.path.isfile(doc):
            continue
        if any(r.get("supersedes") == doc for r in idxjson):
            info("renamed doc, superseded: " + doc)
        else:
            fail("index record points at a missing doc and nothing supersedes it: " + doc)
    # A 4.x layout nobody migrated: the skills no longer read it, so its plan is invisible until moved.
    old = sorted(glob.glob(".claude/clio/docs/plans/*.md") + glob.glob(".claude/clio/docs/tests/*.md"))
    if old:
        fail("%d Markdown plan/test file(s) in the 4.x layout (%s…) — /clio:plan migrates them (`clio test migrate`)" % (len(old), old[0]))
    # The plan and test stores: every line a record, every current record well-formed, every id in one
    # area only — the gate gathers a task's cases by id, so a second home lends it another's evidence.
    for b in store.bad_lines():
        fail("%s is not a JSON record — only `clio add` and `clio test` write the stores" % b)
    for kind in ("plan", "test"):
        for p, r in store.current(kind):
            for msg in store.problems(kind, r):
                fail("%s %s %s: %s" % (p, c.tostring(r.get("type")), c.tostring(r.get("id", "")), msg))
        for k, ps in sorted(store.conflicts(kind).items()):
            fail("%s lives in %s — one id, one area" % (k, " and ".join(ps)))
    planned = set(tasks)
    for p, r in store.current("test"):
        tid = c.tostring(r.get("task") if r.get("type") == "case" else r.get("id"))
        if r.get("type") in ("case", "meta") and tid not in planned:
            fail("%s %s %s: task %s is in no plan" % (p, r.get("type"), c.tostring(r.get("id")), tid))
    for p, r in store.current("plan"):
        if r.get("type") == "task":
            for x in c.items(r.get("needs")) + ([r.get("by")] if c.truthy(r.get("by")) else []):
                if c.tostring(x) not in planned:
                    # A finished task cannot be edited, so a need that already pointed nowhere in 4.x stays
                    # as history: said, not failed. A task still open is the plan's to fix.
                    (warn if r.get("status") != "open" else fail)(
                        "%s task %s names %s, which no plan holds" % (p, c.tostring(r.get("id")), c.tostring(x)))
    if os.path.isfile(RUNS):
        for n, l in numbered(RUNS):
            if l == "":
                continue
            r = parse(l)
            good = isinstance(r, dict) and (
                (c.truthy(r.get("case")) and c.truthy(r.get("fp")) and r.get("result") in ("pass", "fail"))
                or (c.truthy(r.get("approve")) and c.truthy(r.get("hash"))))
            if not good:
                fail("%s line %d is not a `clio test` record — only the script writes this file" % (RUNS, n))
    else:
        warn("missing %s — /clio:test has nowhere to record evidence" % RUNS)

    # A plan task's `req` column, against requirements.md — the same rule check_req applies to a
    # ledger record, applied to the other file that carries req numbers.
    # Not checked here: which decided rows have no plan task. `plan` gives a ⚠️/❌ row a placeholder
    # line naming the debt it waits on, so "a plan row exists for an undecided row" is the correct
    # state, not a finding; and "✅ with no plan task" overlaps the ✅-with-no-index-record INFO below.
    plans = store.files("plan")
    if os.path.isfile(REQ) and plans:
        planreq = sorted({x.strip(" ") for r in planrows for x in r[3].split(",") if x.strip(" ")[:1].isdigit()})
        for n in planreq:
            if n not in rows:
                fail("a plan task claims req %s, which requirements.md has no row for" % n)

    # A spec-delta says the spec moved and the code has not followed. /clio:plan turns one into a
    # task carrying its id, so an open delta named in no plan means no plan absorbed it — and that
    # is silent: every later session reads a plan that no longer matches the decision.
    if plans:
        texts = []
        for base, _, files in os.walk(PLANS):
            for f in files:
                with open(os.path.join(base, f), encoding="utf-8", errors="surrogateescape") as fh:
                    texts.append(fh.read())
        for g in c.group_by(debtjson, lambda r: r.get("id")):
            r = g[-1]
            if r.get("kind") == "spec-delta" and r.get("status") != "done" and r.get("blocked_by") is None:
                did = c.tostring(r.get("id"))
                if not any(did in t for t in texts):
                    warn("spec-delta %s is in no plan — /clio:plan <area> absorbs it as a task" % did)

    # Links inside a document's prose. `.doc` and `.specs` are fields and already checked; a path
    # written into a sentence is not, and moving a doc is exactly what breaks those.
    # Markdown only: a ledger is append-only, so its older records name the old path on purpose and
    # rewriting them would be the actual bug. Skip a path holding `<` — a template placeholder.
    refs = set()
    for top in (".claude/clio/", ".claude/rules/"):
        for base, _, files in os.walk(top):
            if "/docs/archive" in base:
                continue                  # 4.x Markdown kept by `clio test migrate` for comparison
            for f in files:
                if f.endswith(".md"):
                    with open(os.path.join(base, f), encoding="utf-8", errors="surrogateescape") as fh:
                        refs.update(re.findall(r"\.claude/[A-Za-z0-9._/-]+\.md", fh.read()))
    moved = [r for r in refs if r.startswith((".claude/clio/docs/plans/", ".claude/clio/docs/tests/"))]
    if moved and os.path.isdir(".claude/clio/docs/archive/v4"):
        info("%d document path(s) name the 4.x plans/tests Markdown (e.g. %s) — it moved to docs/archive/v4/; "
             "old docs may keep the reference, they are history" % (len(moved), moved[0]))
    for ref in sorted(refs):
        if ref not in moved and "<" not in ref and not os.path.exists(ref):
            warn("dead link in a document: %s — was it renamed? rewrite the reference" % ref)

    # requirements.md markers vs the ledgers
    if os.path.isfile(REQ):
        with_req = [r for r in debtjson if r.get("req") is not None]
        open_debt = [g[-1] for g in c.group_by(with_req, lambda r: r.get("id"))]
        for num, status in tables.req_rows(REQ):
            if "⚠" in status or "❌" in status:
                if not any(r.get("status") != "done" and any(c.tostring(x) == num for x in c.items(r.get("req")))
                           for r in open_debt):
                    warn("requirements.md row %s is ⚠️/❌ but no open debt record tracks it" % num)
            elif "✅" in status:
                if not any(any(c.tostring(x) == num for x in c.items(r.get("req"))) for r in idxjson):
                    info("requirements.md row %s is ✅ (decided) with no index record — decided but not built" % num)


def main(argv):
    global rows, tasks, planrows
    c.quiet_on_closed_pipe()
    root = c.find_root()
    if not root:
        print("FAIL: no .claude/clio above " + os.getcwd())
        sys.exit(1)
    os.chdir(root)
    rows = [r[0] for r in tables.req_rows(REQ)]
    # The plan tables, parsed once: `tasks` are the ids `plan_tasks` is allowed to name. No plan file at
    # all is normal (Lite mode, an area nobody planned), and then nothing here can be checked.
    planrows = store.plan_rows()
    tasks = [r[1] for r in planrows]

    mode = argv[0] if argv else "all"
    n = 1
    if mode in ("index", "debt") and len(argv) > 1:
        if not argv[1].isdigit() or int(argv[1]) < 1:
            print("usage: clio validate [index [N]|debt [N]|all]")
            sys.exit(1)
        n = int(argv[1])
    if mode == "index":
        if not (os.path.isfile(IDX) and os.path.getsize(IDX) > 0):
            print("FAIL: %s is empty" % IDX)
            sys.exit(1)
        for line in last_lines(IDX, n):
            r = parse(line)
            if check_index_line(r) and r.get("type") == "task" and length(r.get("files")) == 0:
                warn("index .files is empty — a task doc with no source files?")
    elif mode == "debt":
        if not (os.path.isfile(DEBT) and os.path.getsize(DEBT) > 0):
            print("FAIL: %s is empty" % DEBT)
            sys.exit(1)
        for line in last_lines(DEBT, n):
            r = parse(line)
            check_debt_line(r)
            only = c.tostring(r["id"]) if isinstance(r, dict) and c.truthy(r.get("id")) else ""
            check_filed_blocked([x for x in parseable(DEBT)], only)
    elif mode == "all":
        audit()
    else:
        print("usage: clio validate [index [N]|debt [N]|all]")
        sys.exit(1)

    if fails == 0:
        print("OK (%s)" % mode)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
