"""The plan and test stores: .claude/clio/database/plan/<area>.jsonl and test/<area>.jsonl.

Append-only, like the other ledgers: the last record per (type, id) in a file is the current state,
earlier ones are the history. Records are written only through `write()` (`clio add`, `clio test
tick`), which merges a partial record onto the previous one, checks the result and appends all or
nothing — so a stored record is always complete.

Readers return the same tuples the Markdown tables gave (cliolib.tables), so the gate's rules did not
have to change with the format:
    plan_rows()  (file, id, task, req, levels, needs, done, kind)
    case_rows()  (case, task, level, covers, command, repeat, tracked, error)
Python 3.9+, standard library only. selftest: skills/lib/selftest_store.py"""
import datetime
import glob
import os
import re

from . import common as c

HERE = os.path.dirname(os.path.abspath(__file__))
LEVELS_FILE = os.path.join(HERE, "..", "..", "test", "LEVELS.md")
PLAN_DIR = ".claude/clio/database/plan"
TEST_DIR = ".claude/clio/database/test"
DASH = "–"
# The only level names a plan or a case may use — skills/test/LEVELS.md's catalog, lowercase.
LEVELS = ("unit integration api contract e2e idempotency concurrency security resilience perf load "
          "stress regression smoke mutation").split()
STATUSES = ("open", "done", "superseded", "void")
CASE_STATUSES = ("active", "removed")
TASK_ID = re.compile(r"[0-9]+(\.[0-9]+)*")
AREA = re.compile(r"[a-z0-9][a-z0-9_-]*")

# Per type: every field a stored record holds, with the default a new record starts from. None as a
# default means "must be given".
SCHEMA = {
    "plan": {
        "task": {"task": None, "req": [], "levels": None, "critical": False, "tier": "full", "needs": [],
                 "touches": [], "na": {}, "status": "open", "by": None, "commit": None, "delta": None},
        "mutation": {"tool": None, "threshold": None, "adr": None},
    },
    "test": {
        "case": {"task": None, "level": None, "covers": [], "behaviour": None, "expected": None,
                 "source": None, "command": None, "repeat": 1, "status": "active"},
        "meta": {"seams": [], "na": {}, "waived": {}},
    },
}


_LEVELS_TEXT = []


def level_ids(level):
    """The `level.n` ids LEVELS.md lists for a level — the risks a case of it must cover or excuse."""
    if not _LEVELS_TEXT:
        try:
            with open(LEVELS_FILE, encoding="utf-8") as f:
                _LEVELS_TEXT.append(f.read())
        except OSError:
            _LEVELS_TEXT.append("")
    return sorted({m[1:-1] for m in re.findall(r"`" + re.escape(level) + r"\.[0-9]+`", _LEVELS_TEXT[0])})


def today():
    return datetime.date.today().strftime("%Y-%m-%d")


def files(kind):
    return sorted(glob.glob((PLAN_DIR if kind == "plan" else TEST_DIR) + "/*.jsonl"))


def area_of(path):
    return os.path.basename(path)[:-len(".jsonl")]


def path_of(kind, area):
    return os.path.join(PLAN_DIR if kind == "plan" else TEST_DIR, area + ".jsonl")


def key(r):
    return (r.get("type"), c.tostring(r.get("id")) if r.get("type") != "mutation" else "")


_READ = {}      # path → ((mtime_ns, size), result): a file is parsed once per process unless it changed
_ROWS = {}      # the validated case tuples, same idea


def _sig(paths):
    out = []
    for p in paths:
        try:
            st = os.stat(p)
            out.append((p, st.st_mtime_ns, st.st_size))
        except OSError:
            out.append((p, 0, 0))
    return tuple(out)


def read(path):
    """(records, bad line numbers) of one store file; a missing file is empty. The result is shared with
    later calls of this process (a write changes the file's mtime and size, so the next read is fresh):
    callers must not change what they get."""
    try:
        st = os.stat(path)
    except OSError:
        return [], []
    key = (st.st_mtime_ns, st.st_size)
    hit = _READ.get(path)
    if hit is not None and hit[0] == key:
        return hit[1]
    res = _read(path)
    _READ[path] = (key, res)
    return res


def _read(path):
    recs, bad = [], []
    with open(path, encoding="utf-8", errors="surrogateescape") as f:
        for n, line in enumerate(f.read().split("\n"), 1):
            if line.strip() == "":
                continue
            try:
                r = c.loads(line)
            except ValueError:
                bad.append(n)
                continue
            if isinstance(r, dict):
                recs.append(r)
            else:
                bad.append(n)
    return recs, bad


def current(kind):
    """[(file, record)] — the last record per (type, id) of each file, in order of first appearance."""
    out = []
    for p in files(kind):
        recs, _ = read(p)
        last, order = {}, []
        for r in recs:
            k = key(r)
            if k not in last:
                order.append(k)
            last[k] = r
        out += [(p, last[k]) for k in order]
    return out


def bad_lines():
    """['<file> line <n>'] for every line of the stores that is not a JSON object."""
    return ["%s line %d" % (p, n) for kind in ("plan", "test") for p in files(kind) for n in read(p)[1]]


# --- checks ------------------------------------------------------------------------------------------

def _strs(v):
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


def _strmap(v):
    return isinstance(v, dict) and all(isinstance(k, str) and isinstance(x, str) and x.strip() for k, x in v.items())


def problems(kind, r):
    """What is wrong with one complete record, as short phrases; [] when it is well-formed."""
    t = r.get("type")
    if t not in SCHEMA[kind]:
        return ["type must be one of: " + ", ".join(SCHEMA[kind])]
    p = ["missing " + f for f in ["id", "date"] + list(SCHEMA[kind][t]) if f not in r and not (f == "id" and t == "mutation")]
    if p:
        return p
    rid = r.get("id")
    if t == "task":
        if not (isinstance(rid, str) and TASK_ID.fullmatch(rid)):
            p.append("id must be a task id such as \"3.1\"")
        if not (isinstance(r["task"], str) and r["task"].strip()):
            p.append("task must be a non-empty string")
        for f in ("req", "needs", "touches"):
            if not _strs(r[f]):
                p.append(f + " must be a list of strings")
        # A task planned before levels existed (a pre-4.0 Test column) keeps none once it is history.
        if not (_strs(r["levels"]) and all(x in LEVELS for x in r["levels"])
                and (r["levels"] or r["status"] != "open")):
            p.append("levels must be a non-empty list from: " + " ".join(LEVELS))
        if not isinstance(r["critical"], bool):
            p.append("critical must be true or false")
        if r["tier"] not in ("full", "light"):
            p.append("tier must be full or light")
        elif r["tier"] == "light" and (r["critical"] or len(r["levels"]) != 1 or r["levels"][0] in ("regression", "mutation")):
            p.append("a light task is not critical and names one level, not regression or mutation — LEVELS.md § Tier")
        if not (_strmap(r["na"]) and all(k in LEVELS for k in r["na"])):
            p.append("na must map a level name to its reason")
        if r["status"] not in STATUSES:
            p.append("status must be one of: " + ", ".join(STATUSES))
        if r["status"] == "superseded" and not isinstance(r["by"], str):
            p.append("a superseded task names the task that replaced it in by")
        for f in ("by", "commit", "delta"):
            if r[f] is not None and not isinstance(r[f], str):
                p.append(f + " must be a string or null")
    elif t == "mutation":
        if not (isinstance(r["tool"], str) and r["tool"].strip()):
            p.append("tool must name the mutation tester, or be \"none\"")
        th = r["threshold"]
        if th is not None and not (isinstance(th, int) and not isinstance(th, bool) and 0 < th <= 100):
            p.append("threshold must be a whole percentage or null")
    elif t == "case":
        if not (isinstance(rid, str) and rid.strip() and not re.search(r"\s", rid)):
            p.append("id must be a case id without spaces")
        if not (isinstance(r["task"], str) and TASK_ID.fullmatch(r["task"])):
            p.append("task must be a task id")
        if r["level"] not in LEVELS:
            p.append("level must be one of: " + " ".join(LEVELS))
        if not _strs(r["covers"]):
            p.append("covers must be a list of LEVELS.md ids")
        for f in ("behaviour", "expected", "source"):
            if not (isinstance(r[f], str) and r[f].strip()):
                p.append(f + " must be a non-empty string")
        if not (isinstance(r["command"], str) and r["command"].strip() and "\n" not in r["command"]):
            p.append("command must be one non-empty line")
        rep = r["repeat"]
        if not (isinstance(rep, int) and not isinstance(rep, bool) and rep >= 1):
            p.append("repeat must be a whole number >= 1")
        if r["status"] not in CASE_STATUSES:
            p.append("status must be one of: " + ", ".join(CASE_STATUSES))
    elif t == "meta":
        if not (isinstance(rid, str) and TASK_ID.fullmatch(rid)):
            p.append("id must be the task id the meta belongs to")
        if not _strs(r["seams"]):
            p.append("seams must be a list of strings")
        if not _strmap(r["na"]):
            p.append("na must map a LEVELS.md id to its reason")
        if not _strmap(r["waived"]):
            p.append("waived must map a case id to its reason")
    return p


def conflicts(kind):
    """Ids held by more than one area file: {id: [files]}. One id, one home — the gate gathers a
    task's cases by id, so a second home would let one task borrow another's evidence."""
    where = {}
    for p, r in current(kind):
        if r.get("type") in ("task", "case", "meta"):
            where.setdefault(key(r), set()).add(p)
    return {"%s %s" % k: sorted(ps) for k, ps in where.items() if len(ps) > 1}


# --- readers in the tables' shapes --------------------------------------------------------------------

def done_cell(r):
    s = r.get("status")
    if s == "done":
        return "[x] %s%s" % (c.tostring(r.get("date")), " " + r["commit"] if c.truthy(r.get("commit")) else "")
    if s == "superseded":
        return "superseded %s → %s" % (c.tostring(r.get("date")), c.tostring(r.get("by")))
    if s == "void":
        return "void " + c.tostring(r.get("date"))
    return "[ ]"


def levels_cell(r):
    lv = ", ".join(c.tostring(x) for x in c.items(r.get("levels")))
    return ("critical · " + lv if r.get("critical") is True else lv) or DASH


def plan_rows():
    out = []
    for p, r in current("plan"):
        if r.get("type") != "task":
            continue
        out.append((p, c.tostring(r.get("id")), c.tostring(r.get("task")),
                    ", ".join(c.tostring(x) for x in c.items(r.get("req"))) or DASH,
                    levels_cell(r), ", ".join(c.tostring(x) for x in c.items(r.get("needs"))) or DASH,
                    done_cell(r), "row"))
    return out


def tasks():
    """{task id: its current record}, across every area."""
    return {c.tostring(r.get("id")): r for _, r in current("plan") if r.get("type") == "task"}


def mutation():
    """The project's mutation decision — the last `mutation` record of any plan file — or None."""
    m = None
    for _, r in current("plan"):
        if r.get("type") == "mutation":
            m = r
    return m


def _cases():
    return [(p, r) for p, r in current("test") if r.get("type") == "case" and r.get("status") != "removed"]


def case_tasks():
    """The ids of the tasks that have at least one active case — without validating a single case."""
    return {c.tostring(r.get("task")) for _, r in _cases()}


def case_rows(levels=" ".join(LEVELS), task=None):
    """One tuple per active case: (case, task, level, covers, command, repeat, tracked, error). A
    malformed record is still returned, with the reason in error, so its task fails loudly. task: only
    that task's cases, and only those are validated. Memoised until a test file changes."""
    sig = (_sig(files("test")), levels, task)
    hit = _ROWS.get(sig)
    if hit is not None:
        return hit
    allowed = levels.split()
    out = []
    for _, r in _cases():
        if task is not None and c.tostring(r.get("task")) != task:
            continue
        p = problems("test", r)
        err = "; ".join(p)
        if not err and allowed and r["level"] not in allowed:
            err = "level %s is not one of: %s" % (r["level"], levels)
        out.append((c.tostring(r.get("id")), c.tostring(r.get("task")), c.tostring(r.get("level")),
                    ", ".join(c.tostring(x) for x in c.items(r.get("covers"))) or DASH,
                    c.tostring(r.get("command")) if c.truthy(r.get("command")) else DASH,
                    c.tostring(r.get("repeat")), 1 if c.items(r.get("covers")) else 0, err))
    _ROWS[sig] = out
    return out


def _metas():
    return {c.tostring(r.get("id")): r for _, r in current("test") if r.get("type") == "meta"}


def case_lines(task):
    """What approve hashes of a task's cases: each active case record as compact JSON without its
    date, in id order — re-recording an unchanged case does not void an approval, any edit does."""
    recs = sorted((r for _, r in _cases() if c.tostring(r.get("task")) == task), key=lambda r: c.tostring(r.get("id")))
    return [c.dumps({k: v for k, v in r.items() if k != "date"}) for r in recs]


def na_rows():
    """(task, LEVELS.md id, line) for every `na` entry of every task's test meta."""
    out = []
    for task, m in sorted(_metas().items()):
        na = m.get("na") if isinstance(m.get("na"), dict) else {}
        for i in sorted(na):
            out.append((task, i, "- %s · %s — %s" % (task, i, c.tostring(na[i]))))
    return out


def waiver_rows():
    """(case, line) for every `waived` entry: a critical case whose red the user agreed cannot exist."""
    out = []
    for _, m in sorted(_metas().items()):
        w = m.get("waived") if isinstance(m.get("waived"), dict) else {}
        for cid in sorted(w):
            out.append((cid, "- %s — %s" % (cid, c.tostring(w[cid]))))
    return out


# --- the one write path ---------------------------------------------------------------------------------

def _lock(f):
    try:
        import fcntl
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    except (ImportError, OSError):
        pass


def write(kind, area, partials, may_tick=False, legacy=False, check_refs=True, dry=False, withdraw=False):
    """Merge each partial record onto the current one of its (type, id), check the lot, append all or
    nothing. Returns (errors, written records). `done` is reached only through the gate (may_tick, set
    by `clio test tick`), and a done task is final — later work is a new task that names it in needs.
    A case names the LEVELS.md ids it proves in covers; only a migrated pre-4.1 row (legacy) may name
    none, and the gate then holds it to nothing, as it did before. A migration writes one area at a
    time while tasks name each other across areas, so it checks references once all are written
    (check_refs=False here, `clio validate all` after). dry: check everything, write nothing. withdraw:
    a done task may become void, and only that (`clio test withdraw`, for work that never left the
    working tree)."""
    errs = []
    if not AREA.fullmatch(area or ""):
        return ["area must be lowercase letters, digits, - or _ (it names the file): %r" % area], []
    path = path_of(kind, area)
    mine = {key(r): r for p, r in current(kind) if p == path}
    elsewhere = {key(r): p for p, r in current(kind) if p != path and r.get("type") in ("task", "case", "meta")}
    plan = tasks()
    batch, out = {}, []
    for n, part in enumerate(partials, 1):
        where = "record %d" % n
        if not isinstance(part, dict):
            errs.append(where + ": not a JSON object")
            continue
        t = part.get("type")
        if t not in SCHEMA[kind]:
            errs.append("%s: type must be one of: %s" % (where, ", ".join(SCHEMA[kind])))
            continue
        k = key(part)
        where = "%s %s" % (t, k[1]) if k[1] else t
        prev = batch.get(k) or mine.get(k)
        if k in elsewhere:
            errs.append("%s: id already lives in %s — one id, one area; pick a new id" % (where, elsewhere[k]))
            continue
        only_void = withdraw and part.get("status") == "void" and set(part) <= {"type", "id", "status"}
        if prev is not None and prev.get("status") == "done" and not (may_tick or only_void):
            errs.append("%s: is done — a done task is final; plan a new task that names it in needs" % where)
            continue
        if part.get("status") == "done" and not may_tick:
            errs.append("%s: status done is written only by `clio test tick`, after the gate passes" % where)
            continue
        rec = {"type": t}
        if t != "mutation":
            rec["id"] = part.get("id")
        # A migration keeps the date a task was ticked on; everything else is dated now.
        rec["date"] = part["date"] if legacy and isinstance(part.get("date"), str) else today()
        base = prev if prev is not None else SCHEMA[kind][t]
        for f in SCHEMA[kind][t]:
            rec[f] = part[f] if f in part else base.get(f)
        unknown = [f for f in part if f not in rec]
        if unknown:
            errs.append("%s: unknown field(s): %s" % (where, ", ".join(unknown)))
            continue
        p = problems(kind, rec)
        if not p and t == "case":
            ids_ = level_ids(rec["level"])
            wrong = [x for x in rec["covers"] if x not in ids_]
            if wrong:
                p.append("covers %s, which LEVELS.md § %s does not list (%s)" % (", ".join(wrong), rec["level"], ", ".join(ids_) or "no ids"))
            elif ids_ and not rec["covers"] and not legacy:
                p.append("covers must name the LEVELS.md ids it proves: %s" % ", ".join(ids_))
        if not p and t == "meta":
            wrong = [x for x in rec["na"] if not re.fullmatch(r"[a-z0-9]+\.[0-9]+", x) or x not in level_ids(x.split(".")[0])]
            if wrong:
                p.append("na names %s, which LEVELS.md does not list" % ", ".join(wrong))
        if p:
            errs.append("%s: %s" % (where, "; ".join(p)))
            continue
        batch[k] = rec
        out.append(rec)
    # References are checked against the stores plus this batch, so one call may add a task and the
    # task that needs it, or a case and its task.
    ids = set(plan) | {k[1] for k in batch if k[0] == "task"}
    for rec in (out if check_refs else []):
        t, rid = rec["type"], c.tostring(rec.get("id"))
        if t == "task":
            for x in rec["needs"] + ([rec["by"]] if rec["by"] else []):
                if x not in ids:
                    errs.append("task %s: names %s, which no plan holds" % (rid, x))
        elif t in ("case", "meta"):
            tid = rec["task"] if t == "case" else rid
            if tid not in ids:
                errs.append("%s %s: task %s is in no plan — /clio:plan it first" % (t, rid, tid))
    if errs:
        return errs, []
    if dry:
        return [], out
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8", errors="surrogateescape") as f:
        _lock(f)
        f.write("".join(c.dumps(r) + "\n" for r in out))
    return [], out
