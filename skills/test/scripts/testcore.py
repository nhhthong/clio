"""testcore — the engine every `clio test` subcommand shares: case/plan tables, the run ledger,
fingerprint-bound execution, and the batch merge. Each cmds/*.py subcommand calls into this; nothing
here parses argv or prints usage — that is clio_test.py's job alone.
Python 3.9+, standard library only."""
import datetime
import glob
import os
import signal
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "lib"))
from cliolib import common as c  # noqa: E402
from cliolib import fingerprint as fpm  # noqa: E402
from cliolib import junit  # noqa: E402
from cliolib import store  # noqa: E402
from cliolib import tables  # noqa: E402

# The only level names a plan or a case may use — LEVELS.md's catalog, lowercase.
LEVELS = " ".join(store.LEVELS)
TESTS = store.TEST_DIR
PLANS = store.PLAN_DIR
# ponytail: fixed floor for concurrency repeats; make it a per-case column if 20 proves wrong somewhere.
CONCURRENCY_MIN_REPEAT = 20
# LEVELS.md's mutation default; override per project with the `threshold` of the plan's `mutation` record.
MUTATION_MIN_THRESHOLD = 80
NA = ("", tables.DASH, "-")

ROOT = RUNS = None


class CaseError(Exception):
    """A case that cannot run at all (no row, two rows, malformed): said, counted as not passed."""


QUIET = False


def say(s=""):
    """Print a line. A reader that stops early (`red … | grep -q …`) closes the pipe: the run goes on
    silently — its records still get written, the lock and the worktree still get cleaned up."""
    global QUIET
    if QUIET:
        return
    try:
        sys.stdout.write(s + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        QUIET = True
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), 1)   # nothing left for the exit-time flush to fail on
        except OSError:
            pass


# --- the tables and the ledger ----------------------------------------------------------------------

def test_files():
    return store.files("test")


def plan_files():
    return store.files("plan")


def cases():
    """Every active case of every test store file — see store.case_rows for the fields."""
    return store.case_rows(LEVELS)


def level_ids(level):
    """All `level.n` ids LEVELS.md's catalog names for a level — the risks a named level must cover
    or excuse. A level whose bullets carry no id (regression, smoke, mutation — each has its own gate
    rule already) has none, which is how the gate knows to skip the check entirely for it."""
    return store.level_ids(level)


def na_lines(task):
    """The bullet-scoped Not applicable list of one task: (id, line). The excuse check reads the id,
    table_hash the line — one parse for both, so a line that excuses an id is always one the user approved."""
    return [(i, line) for t, i, line in store.na_rows() if t == task]


def records():
    """runs.jsonl's records, in order; a line that does not parse is skipped."""
    out = []
    with open(RUNS, encoding="utf-8", errors="surrogateescape") as f:
        for line in f:
            try:
                r = c.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict):
                out.append(r)
    return out


def append(rec):
    with open(RUNS, "a", encoding="utf-8", errors="surrogateescape") as f:
        f.write(c.dumps(rec) + "\n")


def today():
    return datetime.date.today().strftime("%Y-%m-%d")


def short_head(cwd):
    return c.git_out(["rev-parse", "--short", "HEAD"], cwd=cwd) or None


# --- running a command ------------------------------------------------------------------------------

def timeout_s():
    try:
        return max(1, int(os.environ.get("CLIO_TIMEOUT", "600")))
    except ValueError:
        return 600


def ran_nothing(text):
    """True when a command that exited 0 says it ran no test at all: a case whose test was renamed or
    deleted would otherwise "pass". Only output that says so for every package, binary or file counts —
    `go test ./... -run X` prints [no tests to run] for the packages without X and is fine if one ran.
    Go, cargo, pytest and unittest; a runner not listed here is the case's own command to make strict."""
    lines = text.splitlines()
    go_ok = [l for l in lines if l.startswith("ok ") or l.startswith("ok\t")]
    if go_ok and all("[no tests to run]" in l for l in go_ok):
        return True
    cargo = [l.strip() for l in lines if l.strip().startswith("running ") and l.strip().endswith(" tests")]
    if cargo and all(l == "running 0 tests" for l in cargo):
        return True
    return any(l.startswith(("collected 0 items", "no tests ran", "Ran 0 tests")) or " no tests ran in " in l for l in lines)


def heartbeat_s():
    """How often a long command says it is still running — a hang reads as one long before the cap."""
    try:
        return max(1, int(os.environ.get("CLIO_HEARTBEAT", "60")))
    except ValueError:
        return 60


def capped(cmd, cwd, log):
    """`bash -c cmd` in cwd, output to log, capped at CLIO_TIMEOUT seconds (default 600): a deadlocked
    case fails instead of hanging the run. On timeout the whole process group goes — the shell and
    whatever it started (mvn, a JVM) — and the exit is 124, as coreutils' timeout reports it. Every
    CLIO_HEARTBEAT seconds (default 60) it says it is still running and how long the cap leaves.
    Returns (exit code, timed out)."""
    cap = timeout_s()
    with open(log, "wb") as lf:
        p = subprocess.Popen(["bash", "-c", cmd], cwd=cwd, stdin=subprocess.DEVNULL, stdout=lf,
                             stderr=subprocess.STDOUT, start_new_session=True)
        waited, rc = 0, None
        try:
            while rc is None:
                step = min(heartbeat_s(), cap - waited)
                if step <= 0:
                    raise subprocess.TimeoutExpired(cmd, cap)
                try:
                    rc = p.wait(timeout=step)
                except subprocess.TimeoutExpired:
                    waited += step
                    if waited < cap:
                        say("… still running after %d s (cap %d s, CLIO_TIMEOUT): %s" % (waited, cap, cmd[:100]))
        except subprocess.TimeoutExpired:
            for sig, grace in ((signal.SIGTERM, 5), (signal.SIGKILL, None)):
                try:
                    os.killpg(p.pid, sig)
                except ProcessLookupError:
                    break
                try:
                    p.wait(timeout=grace)
                    break
                except subprocess.TimeoutExpired:
                    continue
            p.wait()
            return 124, True
    return (128 - rc if rc < 0 else rc), False


def tail(log, n=30):
    with open(log, "rb") as f:
        text = f.read().decode("utf-8", "replace")
    lines = text.splitlines()
    for line in lines[-n:]:
        say(line)


def row_of(cid, rows):
    hit = [r for r in rows if r[0] == cid]
    if not hit:
        raise CaseError("FAIL: case %s is in no %s/*.jsonl record" % (cid, TESTS))
    if len(hit) > 1:
        raise CaseError("FAIL: case %s lives in two area files — one id, one area" % cid)
    r = hit[0]
    if r[7]:
        raise CaseError("FAIL: case %s: %s" % (cid, r[7]))
    if r[4] in NA:
        raise CaseError("FAIL: case %s has no command (N/A row?)" % cid)
    return r


def run(cid, wd=None, base=""):
    """One case, Repeat times. The row is read here, in the repo; with wd (the worktree `red` built)
    the fingerprint is taken and the command executed there, and the record notes the base commit."""
    _, task, level, _, cmd, rep, _, _ = row_of(cid, cases())
    rep = int(rep)
    cwd = wd or ROOT
    tree = fpm.fp_tree(cwd, RUNS)
    tfp, cfp = fpm.split_fp(cwd, tree)
    before = fpm.untracked(cwd)
    fd, log = tempfile.mkstemp()
    os.close(fd)
    try:
        passed, code = 0, 0
        for i in range(1, rep + 1):
            code, timed_out = capped(cmd, cwd, log)
            if timed_out:
                with open(log, "a") as lf:
                    lf.write("timed out after %ds (run %d of %d)\n" % (timeout_s(), i, rep))
            elif code == 0:
                with open(log, encoding="utf-8", errors="replace") as lf:
                    vacuous = ran_nothing(lf.read())
                if vacuous:    # exit 0 without a test is not a pass
                    code = 1
                    with open(log, "a") as lf:
                        lf.write("the command ran no test (the test was renamed or deleted?) — a case that runs nothing proves nothing\n")
            if code != 0:
                break
            passed += 1
        # A worktree's leftovers vanish with it — only the repo's own runs name artifacts.
        created = [] if wd else sorted(fpm.untracked(cwd) - before)
        result = "pass" if passed == rep else "fail"
        rec = {"date": today(), "case": cid, "task": task, "level": level, "cmd": cmd,
               "commit": short_head(cwd), "fp": tree[:12], "tfp": tfp, "cfp": cfp, "result": result,
               "runs": passed + (1 if code != 0 else 0), "passed": passed, "exit": code, "artifacts": created}
        if base:
            rec["red_base"] = base
        append(rec)
        say("%s: %s (%s) %d/%d — exit %d%s" % (result, cid, level, passed, rep, code, " — on " + base if base else ""))
        if created:
            say("note: the run created %s — recorded as test artifacts, excluded from the fingerprint; gitignore them"
                % c.dumps(created))
        if result != "pass":
            say("--- last output")
            tail(log)
        return result == "pass"
    finally:
        os.remove(log)


def report_files(cwd, pattern):
    return {p: os.stat(p).st_mtime_ns for p in glob.glob(os.path.join(cwd, pattern))}


def run_batch(wd, base, tpl, join, report, pairs, rows):
    """Several cases in one runner start: the template with every test id joined in. One runs.jsonl
    line per case, like run() writes, read from the JUnit XML the runner left — with the batch command
    beside the case's own. A report is the run's if it appeared or changed during it."""
    full = tpl.replace("{tests}", join.join(tid for _, tid in pairs))
    cwd = wd or ROOT
    tree = fpm.fp_tree(cwd, RUNS)
    tfp, cfp = fpm.split_fp(cwd, tree)
    before = report_files(cwd, report)
    fd, log = tempfile.mkstemp()
    os.close(fd)
    ok = True
    try:
        code, timed_out = capped(full, cwd, log)
        if timed_out:
            with open(log, "a") as lf:
                lf.write("timed out after %ds (whole batch)\n" % timeout_s())
        xmls = sorted(p for p, m in report_files(cwd, report).items() if before.get(p) != m)
        entries = junit.junit(xmls)
        fall, shown = [], False
        for cid, tid in pairs:
            _, task, level, _, cmd, rep, _, _ = next(r for r in rows if r[0] == cid)
            rep = int(rep)
            # A test id matches a classname in full or by its trailing `.Simple` part — `OrderTest#x`
            # matches every package's OrderTest (as `-Dtest=OrderTest#x` runs them all), `com.a.OrderTest#x`
            # only that one. cnt: entries seen; bad: failed or skipped; reps: repetitions of one call —
            # the fewest any matched class shows, a parameterised test's sets counting once — which is
            # what `Repeat` asks for.
            if "#" in tid:
                k, m = tid.split("#", 1)
            else:
                k = m = None

            def cls(klass, want):
                return klass == want or klass.endswith("." + want)

            def hit(e):
                if k is not None:
                    return e[1] == m and cls(e[0], k)
                return e[1] == tid or cls(e[0], tid)
            hits = [e for e in entries if hit(e)]
            cnt = len(hits)
            bad = sum(1 for e in hits if e[2] != 0)
            per = {}
            for e in hits:
                per[e[:2]] = per.get(e[:2], 0) + e[3]
            # per call (class, method): two packages are not two repetitions, and neither are two
            # methods of one class matched by a class-wide id
            reps = min((v if v > 0 else 1) for v in per.values()) if per else 0
            if cnt > 0 and bad == 0 and reps < rep:
                fall.append(cid)
                continue
            result = "pass" if cnt > 0 and bad == 0 else "fail"
            passed = reps if bad == 0 else 0
            rec = {"date": today(), "case": cid, "task": task, "level": level, "cmd": cmd, "batch": full,
                   "commit": short_head(cwd), "fp": tree[:12], "tfp": tfp, "cfp": cfp, "result": result,
                   "runs": reps, "passed": passed, "exit": code, "artifacts": []}
            if base:
                rec["red_base"] = base
            append(rec)
            say("%s: %s (%s) %d/%d — batch%s%s" % (result, cid, level, passed, reps,
                                                  " — on " + base if base else "", "" if cnt else " — not in the report"))
            if result == "fail":
                ok = False
                if not shown:
                    say("--- last output")
                    tail(log)
                    shown = True
    finally:
        os.remove(log)
    for fb in fall:
        say("note: %s's report shows fewer repetitions than its Repeat (parameter sets are not repeats) — running it on its own" % fb)
        ok = guarded(fb, wd, base) and ok
    return ok


def guarded(cid, wd=None, base=""):
    """run(), with a case that cannot run said and counted as not passed instead of ending the call."""
    try:
        return run(cid, wd, base)
    except CaseError as e:
        say(str(e))
        return False


def run_cases(wd, base, ids):
    """Every case through a matching `Batch:` template when one fits, the rest one command each."""
    rows = cases()
    tpls = junit.batches()
    left = list(ids)
    ok = True

    def cmd_of(cid):
        return next((r[4] for r in rows if r[0] == cid), "")
    broken = {r[0] for r in rows if r[7]}
    for tpl, join, report in tpls:
        pairs, keep = [], []
        for cid in left:
            tid = None if cid in broken else junit.batch_id(cmd_of(cid), tpl)
            (pairs.append((cid, tid)) if tid is not None else keep.append(cid))
        left = keep
        if pairs:
            ok = run_batch(wd, base, tpl, join, report, pairs, rows) and ok
    # Say so when two or more cases are about to pay a runner start each: that is where the time goes,
    # and the cause is usually one flag between a template and the rows (`-q`), which nothing else shows.
    if len(left) >= 2:
        cmds = [cmd_of(cid) for cid in left]
        guess = junit.suggest_template(cmds)
        if tpls:
            say("note: %d cases run one runner start each — their commands match no `Batch:` template word for word." % len(left))
            say("      template: " + tpls[0][0])
            say("      a case:   " + cmds[0])
        else:
            say("note: %d cases run one runner start each — no `Batch:` line in .claude/rules (/clio:test § 1b)." % len(left))
        if guess:
            say("      their own commands fit: Batch: `%s` · join: … · report: …" % guess)
    for cid in left:
        ok = guarded(cid, wd, base) and ok
    return ok


def last_results(ids, since=0):
    """The last recorded result per case: pass | fail | never — and `notrun` for a batch record whose
    report did not show the test at all (the build failed, the id is wrong): a fail, but not one that
    proves anything about the code. since: skip the first records — the ones written before this call,
    so a case that could not run reads `never`, not its last result from an earlier call."""
    last = {}
    for r in records()[since:]:
        if "case" in r:
            last[r["case"]] = "notrun" if (c.truthy(r.get("batch")) and r.get("runs") == 0) else r.get("result")
    return [(cid, last.get(cid, "never")) for cid in ids]


def runnable(rows, task):
    return [r for r in rows if r[1] == task and r[4] not in (tables.DASH, "-")]


class Prefixed:
    """A stdout whose every line starts with a prefix — how `red` sets its per-case output apart."""

    def __init__(self, inner, prefix):
        self.inner, self.prefix, self.at_start = inner, prefix, True

    def write(self, s):
        for chunk in s.splitlines(True):
            if self.at_start:
                self.inner.write(self.prefix)
            self.inner.write(chunk)
            self.at_start = chunk.endswith("\n")

    def flush(self):
        self.inner.flush()


def link_deps(wt):
    """Dependency dirs a checkout lacks because they are ignored — at the root or nested
    (frontend/node_modules), up to four levels down — are linked in, not copied."""
    names = {"node_modules", "vendor", ".venv", "venv"}
    for base, dirs, _ in os.walk("."):
        depth = 0 if base == "." else base.count(os.sep)
        keep = []
        for d in sorted(dirs):
            rel = os.path.normpath(os.path.join(base, d))
            if d in (".git", "clio-red"):
                continue
            if d in names:
                target = os.path.join(wt, rel)
                if c.git(["check-ignore", "-q", rel]).returncode == 0 and not os.path.lexists(target):
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    os.symlink(os.path.join(ROOT, rel), target)
                continue
            if depth + 1 < 4:
                keep.append(d)
        dirs[:] = keep


def case_part(task):
    return store.case_lines(task)


def list_part(task):
    """What else the user approved for a task: its `Not applicable` lines, then the `Red waived`
    lines of its cases."""
    mine = {r[0] for r in cases() if r[1] == task}
    return [line for _, line in na_lines(task)] + [line for cid, line in store.waiver_rows() if cid in mine]


def hash_of(lines):
    return fpm.blob_hash("".join(l + "\n" for l in lines))


def table_hash(task):
    """What the user approved for a task, in two parts — its case rows and its lists — hashed as
    one: an excuse or a waiver added after approve voids it like an edited case would."""
    if not test_files():
        return "none"
    return hash_of(case_part(task) + list_part(task))
