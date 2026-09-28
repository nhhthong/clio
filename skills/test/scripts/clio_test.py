#!/usr/bin/env python3
"""clio test run <case-id> | run-task <task-id>... | red <task-id>... [--base <rev>] [--fresh] | approve <task-id>... | gate <task-id> | coverage <task-id> | history <case-id> | fp
  run       run one case from .claude/clio/docs/tests/*.md `Repeat` times, append the result to runs.jsonl
  run-task  run every case of each task that way — one call proves a whole task
  red       run the cases that must be seen red (regression, critical) on the code at a base commit,
            in a kept worktree with today's tests — red without breaking code by hand
  approve   record the hash of each task's case rows once the user approved them (one batch, one yes);
            the gate holds each table to its own hash
  gate      exit 0 only if every case of a plan task has fresh, complete, passing evidence
  coverage  per case of a task: level and last recorded result (pass/fail/never) — what /clio:plan
            reads to decide whether a ticked task's tests fall short
  history   every recorded run of one case, oldest first
  fp        print the working-tree fingerprint evidence is bound to
The model never writes runs.jsonl itself: a pass exists only because this script saw exit 0.
Python 3.9+, standard library only; every caller reaches it as `clio test` (bin/clio)."""
import datetime
import glob
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "lib"))
from cliolib import common as c  # noqa: E402
from cliolib import fingerprint as fpm  # noqa: E402
from cliolib import junit  # noqa: E402
from cliolib import tables  # noqa: E402

# The catalog this script's own repo ships beside it — not the target repo's — so `level_ids` below
# reads the same ids /clio:test wrote from, however clio test was invoked.
LEVELS_FILE = os.path.join(HERE, "..", "LEVELS.md")
# The only level names a plan or a case may use — LEVELS.md's catalog, lowercase.
LEVELS = "unit integration api contract e2e idempotency concurrency security resilience perf load stress regression smoke mutation"
TESTS = ".claude/clio/docs/tests"
PLANS = ".claude/clio/docs/plans"
# ponytail: fixed floor for concurrency repeats; make it a per-case column if 20 proves wrong somewhere.
CONCURRENCY_MIN_REPEAT = 20
# LEVELS.md's mutation default; override per project with `NN%` on the `Mutation:` line in plans/infra.md.
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
    return sorted(glob.glob(TESTS + "/*.md"))


def plan_files():
    return sorted(glob.glob(PLANS + "/*.md"))


def cases():
    """Every case row of every tests file — see tables.case_rows for the fields."""
    return tables.case_rows(LEVELS, test_files())


def level_ids(level):
    """All `level.n` ids LEVELS.md's catalog names for a level — the risks a named level must cover
    or excuse. A level whose bullets carry no id (regression, smoke, mutation — each has its own gate
    rule already) has none, which is how the gate knows to skip the check entirely for it."""
    try:
        text = open(LEVELS_FILE, encoding="utf-8").read()
    except OSError:
        return []
    return sorted({m[1:-1] for m in re.findall(r"`" + re.escape(level) + r"\.[0-9]+`", text)})


def na_lines(task):
    """The bullet-scoped Not applicable list of one task: (id, line). The excuse check reads the id,
    table_hash the line — one parse for both, so a line that excuses an id is always one the user approved."""
    return [(i, line) for t, i, line in tables.na_rows(test_files()) if t == task]


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


def capped(cmd, cwd, log):
    """`bash -c cmd` in cwd, output to log, capped at CLIO_TIMEOUT seconds (default 600): a deadlocked
    case fails instead of hanging the run. On timeout the whole process group goes — the shell and
    whatever it started (mvn, a JVM) — and the exit is 124, as coreutils' timeout reports it.
    Returns (exit code, timed out)."""
    with open(log, "wb") as lf:
        p = subprocess.Popen(["bash", "-c", cmd], cwd=cwd, stdin=subprocess.DEVNULL, stdout=lf,
                             stderr=subprocess.STDOUT, start_new_session=True)
        try:
            rc = p.wait(timeout=timeout_s())
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
        raise CaseError("FAIL: case %s is in no %s/*.md row" % (cid, TESTS))
    if len(hit) > 1:
        raise CaseError("FAIL: case %s appears twice" % cid)
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
                per[e[0]] = per.get(e[0], 0) + e[3]
            reps = min((v if v > 0 else 1) for v in per.values()) if per else 0   # two packages are not two repetitions
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
    for tpl, join, report in tpls:
        pairs, keep = [], []
        for cid in left:
            tid = junit.batch_id(cmd_of(cid), tpl)
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


def last_results(ids):
    """The last recorded result per case: pass | fail | never — and `notrun` for a batch record whose
    report did not show the test at all (the build failed, the id is wrong): a fail, but not one that
    proves anything about the code."""
    last = {}
    for r in records():
        if "case" in r:
            last[r["case"]] = "notrun" if (c.truthy(r.get("batch")) and r.get("runs") == 0) else r.get("result")
    return [(cid, last.get(cid, "never")) for cid in ids]


# --- commands ---------------------------------------------------------------------------------------

def runnable(rows, task):
    return [r for r in rows if r[1] == task and r[4] not in (tables.DASH, "-")]


def cmd_run_task(tasks):
    """Every runnable case of each task given — all tasks' cases in one run_cases, so a batch template
    starts its runner once for the lot. Every task id is checked before anything runs."""
    rows = cases()
    ids = []
    for task in tasks:
        mine = runnable(rows, task)
        if not mine:
            say("FAIL: task %s has no runnable case in %s/*.md — nothing run" % (task, TESTS))
            return 1
        ids += [r[0] for r in mine]
    t0 = time.monotonic()
    run_cases(None, "", ids)
    res = dict(last_results(ids))
    total = totalbad = 0
    for task in tasks:
        mine = [r[0] for r in rows if r[1] == task and r[0] in res]
        n = len(mine)
        bad = sum(1 for cid in mine if res[cid] != "pass")
        say("task %s: %d/%d cases passed" % (task, n - bad, n))
        total, totalbad = total + n, totalbad + bad
    if len(tasks) != 1:
        say("all: %d/%d cases passed across %d tasks" % (total - totalbad, total, len(tasks)))
    say("took %d s" % int(time.monotonic() - t0))
    return 0 if totalbad == 0 else 1


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


def cmd_red(args):
    """See the cases that must be seen red fail on the code as it was at <rev> (default HEAD — the
    commit before the uncommitted change), without anyone breaking code by hand. A worktree of <rev>
    gets today's test files (and only those) — so the run has the same tfp as the pass and another cfp,
    which is exactly what the gate counts as red. Which cases: every `regression` case, and every
    non-mutation case of a `critical` task; nothing else needs red. Exit 0 only if each failed there."""
    base, fresh, tasks = "HEAD", False, []
    i = 0
    while i < len(args):
        if args[i] == "--base":
            if i + 1 >= len(args) or not args[i + 1]:
                say("FAIL: --base needs a commit")
                return 1
            base, i = args[i + 1], i + 2
        elif args[i] == "--fresh":
            fresh, i = True, i + 1
        else:
            tasks.append(args[i])
            i += 1
    if not tasks:
        say("usage: clio test red <task-id>... [--base <rev>] [--fresh]")
        return 1
    if c.git(["rev-parse", "-q", "--verify", base + "^{commit}"]).returncode != 0:
        say("FAIL: %s is not a commit" % base)
        return 1
    rows = cases()
    prows = tables.plan_rows(plan_files())
    ids = []
    for task in tasks:
        levels = next((r[4] for r in prows if r[1] == task), None)
        if levels is None:
            say("FAIL: task %s is in no %s/*.md row — nothing run" % (task, PLANS))
            return 1
        crit = "critical" in levels
        ids += [r[0] for r in rows if r[1] == task and r[4] not in (tables.DASH, "-") and r[7] == ""
                and (r[2] == "regression" or (crit and r[2] != "mutation"))]
    if not ids:
        say("nothing needs red in %s: no regression case, no critical task — run-task is enough" % " ".join(tasks))
        return 0

    # One worktree, kept between calls under the repo's git dir: a second red on the same base only
    # recompiles what changed instead of building the whole project cold. A new base, or --fresh,
    # starts it over — build output of one base never meets another's sources. It never touches the
    # user's working tree, and one red runs at a time (the lock).
    t0 = time.monotonic()
    gd = os.path.abspath(c.git_out(["rev-parse", "--git-common-dir"]))
    wt, stamp = os.path.join(gd, "clio-red"), os.path.join(gd, "clio-red.base")
    sha = c.git_out(["rev-parse", base + "^{commit}"])
    try:
        os.mkdir(wt + ".lock")
    except OSError:
        say("FAIL: another `clio test red` is running (or died: rmdir %s.lock)" % wt)
        return 1
    try:
        c.git(["worktree", "prune"])
        stamped = open(stamp).read().strip() if os.path.isfile(stamp) else ""
        if not fresh and stamped == sha and c.git(["rev-parse", "--git-dir"], cwd=wt).returncode == 0:
            c.git(["checkout", "-q", "--detach", "--force", sha], cwd=wt)
            c.git(["clean", "-fdq"], cwd=wt)   # ignored build output stays
            say("note: reusing the red worktree at %s — only changed files rebuild (--fresh to start over)" % sha[:7])
        else:
            c.git(["worktree", "remove", "--force", wt])
            if wt.endswith("/clio-red") and os.path.lexists(wt):
                shutil.rmtree(wt)
            if c.git(["worktree", "add", "-q", "--detach", wt, sha]).returncode != 0:
                say("FAIL: cannot create a worktree at %s" % base)
                return 1
            with open(stamp, "w") as f:
                f.write(sha + "\n")
        # Test files: the base's are removed, today's copied in — tracked or not, never ignored ones.
        for p in c.git(["ls-files", "-z"], cwd=wt).stdout.split("\0"):
            if p and fpm.TEST_PATHS.search(p) and os.path.lexists(os.path.join(wt, p)):
                os.remove(os.path.join(wt, p))
        for p in c.git(["ls-files", "-co", "--exclude-standard", "-z", "--", ".", ":(exclude).claude"]).stdout.split("\0"):
            if p and fpm.TEST_PATHS.search(p) and os.path.isfile(p):
                os.makedirs(os.path.dirname(os.path.join(wt, p)) or wt, exist_ok=True)
                shutil.copy2(p, os.path.join(wt, p))
        link_deps(wt)

        label = c.git_out(["rev-parse", "--short", base])
        # Every failure's output is printed by run/run_batch: read it — a red counts only on an assertion.
        out = sys.stdout
        sys.stdout = Prefixed(out, "  | ")
        try:
            run_cases(wt, label, ids)
        finally:
            sys.stdout = out
        n = bad = 0
        for cid, r in last_results(ids):
            n += 1
            if r == "pass":
                say("NOT RED: %s passed on %s — it cannot tell that code from yours (change already committed? --base <the commit before it>)" % (cid, label))
                bad += 1
            elif r == "notrun":
                say("NOT RED: %s did not run on %s — the report does not show it (build error?); a red must fail an assertion" % (cid, label))
                bad += 1
            else:
                say("red: %s failed on %s" % (cid, label))
        say("red on %s: %d/%d cases failed as they must" % (label, n - bad, n))
        say("took %d s" % int(time.monotonic() - t0))
        return 0 if bad == 0 else 1
    finally:
        os.rmdir(wt + ".lock")


def case_part(task):
    return tables.case_lines(task, test_files())


def list_part(task):
    """What else the user approved for a task: its `Not applicable` lines, then the `Red waived`
    lines of its cases."""
    mine = {r[0] for r in cases() if r[1] == task}
    return [line for _, line in na_lines(task)] + [line for cid, line in tables.waiver_rows(test_files()) if cid in mine]


def hash_of(lines):
    return fpm.blob_hash("".join(l + "\n" for l in lines))


def table_hash(task):
    """What the user approved for a task, in two parts — its case rows and its lists — hashed as
    one: an excuse or a waiver added after approve voids it like an edited case would. A task with no
    list line hashes exactly as before 4.2.0."""
    if not test_files():
        return "none"
    return hash_of(case_part(task) + list_part(task))


def cmd_approve(tasks):
    """One yes can cover a batch: each task still gets its own record and hash, so editing one table
    later voids that task's approval only. All ids are checked first — a typo approves nothing."""
    rows = cases()
    for task in tasks:
        if not any(r[1] == task for r in rows):
            say("FAIL: task %s has no case rows to approve — nothing approved" % task)
            return 1
    for task in tasks:
        h = table_hash(task)
        append({"date": today(), "approve": task, "hash": h,
                "cases": hash_of(case_part(task)), "lists": hash_of(list_part(task))})
        say("approved: task %s case table %s" % (task, h))
    return 0


def cmd_gate(task):
    fails = [0]

    def fail(msg):
        say("FAIL: " + msg)
        fails[0] += 1
    cur = fpm.fp(ROOT, RUNS)
    rows = [r for r in cases() if r[1] == task]
    if not rows:
        say("FAIL: task %s has no cases — run /clio:test %s" % (task, task))
        return 1
    recs = records()
    arec = next((r for r in reversed(recs) if r.get("approve") == task), None)
    approved = arec.get("hash") if arec and c.truthy(arec.get("hash")) else ""
    if not approved:
        fail("%s: case table never approved — show it to the user, then `clio test approve %s`" % (task, task))
    elif approved != table_hash(task):
        # Say what moved, when the approval recorded its parts (4.2.0+): a new excuse reads very
        # differently from an edited case, and the user should not have to diff to tell which.
        what = "a case added, removed or edited, or a list line"
        if c.truthy(arec.get("cases")) and c.truthy(arec.get("lists")):
            what = ""
            if arec["cases"] != hash_of(case_part(task)):
                what = "case rows (added, removed or edited)"
            if arec["lists"] != hash_of(list_part(task)):
                what = (what + " and " if what else "") + "`Not applicable` / `Red waived` lines"
            what = what or "the table"
        fail("%s: case table changed since it was approved (%s) — changed: %s; show the change and get the user's yes again"
             % (task, approved, what))

    # The plan's Levels cell: "critical · unit, api" or "unit, api". plan_rows says, per row, whether
    # its table has a Levels column or a pre-4.0 Test command.
    found = next((r for r in tables.plan_rows(plan_files()) if r[1] == task), None)
    if found is None:
        say("FAIL: task %s is in no %s/*.md row — the gate needs the plan's Levels" % (task, PLANS))
        return 1
    kind, done, levels = found[7], found[6], found[4]
    if kind != "row":
        say("FAIL: task %s is a pre-4.0 row (Test column, no Levels) — /clio:plan <area> adds a sub-task that brings it under /clio:test; gate that" % task)
        return 1
    if "superseded" in done:
        say("FAIL: task %s is superseded (%s) — gate the row that replaced it" % (task, done))
        return 1
    critical = "critical" in levels

    def last_run(cid):
        """The last run of THIS code: a `red` run (red_base) ran on the base commit's code in a
        worktree — it feeds the red check, never the "is it passing now" one."""
        return next((r for r in reversed(recs) if r.get("case") == cid and not c.truthy(r.get("red_base"))), None)

    # On a critical task a passing mutation case proves what red would — the tests catch injected
    # faults — so it stands in for red on every case of the task. Found once, before the per-case loop.
    mut_ok = ""
    for r in rows:
        if r[2] == "mutation" and r[7] == "":
            lr = last_run(r[0])
            if lr is not None and lr.get("result") == "pass" and lr.get("fp") == cur and lr.get("cmd") == r[4]:
                mut_ok = r[0]
    waived = {cid for cid, _ in tables.waiver_rows(test_files())}
    # Mutation is required only where the plan names it (the user agreed the task is beyond critical),
    # never implied by `critical`. `Mutation: none` in plans/infra.md is an ADR against it, so a row
    # still naming it is a contradiction to resolve, not a level to waive quietly.
    infra = tables.read_lines(PLANS + "/infra.md") if os.path.isfile(PLANS + "/infra.md") else []
    no_mutation = any(re.match(r"Mutation: *none", l, re.I) for l in infra)
    # The threshold a mutation case's command must show: the project's own `NN%` if it set one, else
    # LEVELS.md's default. Read once so every mutation case in this task is held to the same number.
    mutation_req = MUTATION_MIN_THRESHOLD
    mline = next((l for l in infra if re.match(r"Mutation:", l, re.I)), "")
    m = re.search(r"([0-9]{1,3})%", mline)
    if m:
        mutation_req = int(m.group(1))
    excused = {i for i, _ in na_lines(task)}
    for l in levels.replace("critical", "").replace(",", " ").replace("·", " ").split():
        if l not in LEVELS.split():
            fail("%s: plan level '%s' is not one of: %s" % (task, l, LEVELS))
            continue
        if l == "mutation" and no_mutation:
            fail("%s: plan names 'mutation' but plans/infra.md says `Mutation: none` — re-plan the task without it, or change the ADR" % task)
            continue
        if not any(r[2] == l and r[4] not in NA for r in rows):
            fail("%s: plan requires level '%s', no runnable case covers it" % (task, l))
            continue
        # Bullet coverage: only for a level LEVELS.md gives ids, and only once this task has at least
        # one Covers-tracked row for it — a pre-4.1 case table (no Covers column) is grandfathered.
        req_ids = level_ids(l)
        tracked = [r for r in rows if r[2] == l and r[6] == 1]
        if not req_ids or not tracked:
            continue
        covered = set()
        for r in tracked:
            covered.update(x.strip(" \t") for x in re.split(r"[,·]", r[3]))
        covered -= set(NA)
        for rid in req_ids:
            if rid not in covered and rid not in excused:
                fail("%s: %s has no case covering %s and no `Not applicable` line for it — LEVELS.md § %s" % (task, l, rid, l))

    # One case, one command: a command reused under another case (or level) proves nothing new.
    by_cmd = {}
    for r in rows:
        if r[4] not in NA:
            by_cmd.setdefault(r[4], []).append(r[0])
    for ids in by_cmd.values():
        if len(ids) > 1:
            fail("%s: cases %s run the same command — one case, one command" % (task, ", ".join(ids)))

    for cid, _, level, _, cmd, rep, _, err in rows:
        if err:
            fail("%s: %s" % (cid, err))
            continue
        if cmd in NA:
            continue
        rep = int(rep)
        if level == "concurrency" and rep < CONCURRENCY_MIN_REPEAT:
            fail("%s: concurrency case repeats %d < %d" % (cid, rep, CONCURRENCY_MIN_REPEAT))
        if level == "mutation":
            # The tool's own exit code is trusted (LEVELS.md: it fails below threshold) — but a threshold
            # written as 0, or left out, always exits 0 too. So the command must pass it as a flag whose
            # name says so — Stryker `--thresholds.break N`, PIT `-DmutationThreshold=N`, a wrapper's
            # `--threshold N` / `--min-score N` — and every such flag must be >= the bar: a stray 80
            # elsewhere (a port, `# 80`) does not count, and `--threshold 0 --min-score 80` is refused.
            # A `#` is refused outright: bash -c would treat the rest as a comment the tool never sees.
            nums = [int(re.search(r"[0-9]+$", mm.group(0)).group(0)) for mm in re.finditer(
                r"(thresholds\.break|mutationThreshold|threshold|min[-_]score)[ =:]+[0-9]{1,3}", cmd, re.I)]
            low = min(nums) if nums else -1
            if "#" in cmd:
                fail("%s: mutation command contains `#` — bash -c drops everything after it; pass the threshold as a real flag" % cid)
            elif low < mutation_req:
                fail("%s: mutation command shows no threshold >= %d%% (lowest threshold flag: %s) — pass it as --thresholds.break N / -DmutationThreshold=N / --threshold N / --min-score N; default is %d, override with `NN%%` on the `Mutation:` line in plans/infra.md"
                     % (cid, mutation_req, "none" if low < 0 else low, MUTATION_MIN_THRESHOLD))
        last = last_run(cid)
        if last is None:
            fail(cid + ": never run")
            continue
        if last.get("result") != "pass":
            fail(cid + ": last run failed")
            continue
        if last.get("fp") != cur:
            fail(cid + ": code changed since the last pass — re-run (see `git status --short`; a test output that is not gitignored counts as code)")
        if last.get("cmd") != cmd:
            fail(cid + ": command changed since the last pass — re-run")
        runs_ = last.get("runs")
        if not (isinstance(runs_, (int, float)) and not isinstance(runs_, bool) and runs_ >= rep):
            fail("%s: ran fewer times than Repeat %d" % (cid, rep))
        # Only runs of this command count, in file order (runs.jsonl is append-only).
        #   flaky — it failed on this very code after passing on it: same fp, both results.
        #   red   — it failed before a pass on this code, with the test files as they were at that pass
        #           and the code under test different: the case can tell them apart. A run from before
        #           4.2.0 carries no tfp/cfp and is judged the old way (any other fp).
        # ponytail: a fail at this fp *before* its first pass is forgiven (a DB not yet up); a real flake
        # that happens to fail first slips through — Repeat is what catches those.
        mine = [r for r in recs if r.get("case") == cid and r.get("cmd") == cmd]
        p = [k for k, r in enumerate(mine) if r.get("fp") == cur and r.get("result") == "pass"]
        flaky = bool(p) and any(k > p[0] and r.get("fp") == cur and r.get("result") == "fail" for k, r in enumerate(mine))
        red = False
        if p:
            okr = mine[p[-1]]
            for k, r in enumerate(mine):
                if k >= p[-1] or r.get("result") != "fail":
                    continue
                if c.truthy(r.get("batch")) and r.get("runs") == 0:   # not in the report: it never ran
                    continue
                if c.truthy(r.get("tfp")) and c.truthy(okr.get("tfp")):
                    if r.get("tfp") == okr.get("tfp") and r.get("cfp") != okr.get("cfp"):
                        red = True
                elif r.get("fp") != cur:
                    red = True
        if flaky:
            fail(cid + ": flaky — failed on this code after passing on it; /clio:memo files it as code-debt `flaky:`")
        if not red:
            # A test never seen failing may pass by construction. Regression must prove it reproduced the
            # bug; on a critical task every case must. A mutation case is exempt: its red is a score below
            # threshold. Only these two need red; any other case was checked by its spec-sourced Expected
            # and the approval.
            if level == "regression":
                fail("%s: regression case never failed, with this command and these test files, on code before the fix — `clio test red %s`, then run-task" % (cid, task))
            elif level == "mutation":
                pass
            elif critical:
                if mut_ok:
                    say("NOTE: %s: no red of its own — covered by mutation case %s passing on this code" % (cid, mut_ok))
                elif cid in waived:
                    # A waiver stands only on a tried red — a `red` run of this command, with the test files
                    # of the pass, that PASSED on a base commit: the behaviour was already right there.
                    t = last.get("tfp") if c.truthy(last.get("tfp")) else ""
                    if any(c.truthy(r.get("red_base")) and r.get("result") == "pass" and r.get("tfp") == t for r in mine):
                        say("NOTE: %s: red waived (approved) — passed on a base commit with these tests; the behaviour predates the task" % cid)
                    else:
                        fail("%s: red waived, but no `red` run of it passed on a base commit with these test files — run `clio test red %s --base <commit>` first: a waiver stands only on a tried red" % (cid, task))
                else:
                    fail("%s: never seen red on a critical task — `clio test red %s` (add --base <commit> if the change is committed), then run-task; red not reproducible because the behaviour was always right → a mutation case (/clio:plan), or a `Red waived:` line the user approves after a `red` that passed" % (cid, task))

    if fails[0] == 0:
        say("OK: task %s — every case passed at %s" % (task, cur))
        return 0
    return 1


def cmd_history(cid):
    """Every recorded run of one case, oldest first: date · result passed/runs · fp · red@base ·
    batch · exit · commit — what a person reads when the gate's verdict needs explaining."""
    lines = []
    for r in records():
        if r.get("case") != cid:
            continue
        passed = r.get("passed")
        runs_ = r.get("runs")
        lines.append("  ".join([
            c.tostring(r.get("date")) if r.get("date") is not None else "",
            c.tostring(r.get("result")) if r.get("result") is not None else "",
            "%s/%s" % ("?" if passed is None or passed is False else c.tostring(passed),
                       "?" if runs_ is None or runs_ is False else c.tostring(runs_)),
            c.tostring(r.get("fp")) if r.get("fp") is not None else "",
            "red@" + c.tostring(r["red_base"]) if c.truthy(r.get("red_base")) else "-",
            "batch" if c.truthy(r.get("batch")) else "-",
            "exit " + c.tostring(r.get("exit")),
            c.tostring(r["commit"]) if c.truthy(r.get("commit")) else "-"]))
    say("\n".join(lines) if lines else "no runs recorded for " + cid)
    return 0


def cmd_coverage(task):
    """Per case of a task: level and last result on this code (pass/fail/never) — what /clio:plan reads
    to decide whether a ticked task's tests fall short."""
    mine = runnable(cases(), task)
    if not mine:
        say("no cases")
        return 0
    recs = records()
    for r in mine:
        last = next((x.get("result") for x in reversed(recs)
                     if x.get("case") == r[0] and not c.truthy(x.get("red_base"))), None)
        say("%s\t%s\t%s" % (r[0], r[2], c.tostring(last) if last is not None else "never"))
    return 0


USAGE = ("usage: clio test run <case-id> | run-task <task-id>... | red <task-id>... [--base <rev>] [--fresh]"
         " | approve <task-id>... | gate <task-id> | coverage <task-id> | history <case-id> | fp")


def main(argv):
    global ROOT, RUNS
    ROOT = c.find_root()
    if not ROOT:
        say("FAIL: no .claude/clio above " + os.getcwd())
        return 1
    os.chdir(ROOT)
    if not c.is_git():
        say("FAIL: clio-test needs a git repository — evidence is bound to the working tree")
        return 1
    RUNS = os.path.join(ROOT, ".claude/clio/database/runs.jsonl")   # absolute: `red` runs cases from a worktree
    open(RUNS, "a").close()
    cmd = argv[0] if argv else ""
    arg = argv[1] if len(argv) > 1 else ""
    if cmd == "coverage":
        return cmd_coverage(arg) if arg else (say("usage: clio test coverage <task-id>") or 1)
    if cmd == "history":
        return cmd_history(arg) if arg else (say("usage: clio test history <case-id>") or 1)
    if cmd == "run":
        if not arg:
            say("usage: clio test run <case-id>")
            return 1
        try:
            return 0 if run(arg) else 1
        except CaseError as e:
            say(str(e))
            return 1
    if cmd == "run-task":
        return cmd_run_task(argv[1:]) if arg else (say("usage: clio test run-task <task-id>...") or 1)
    if cmd == "red":
        return cmd_red(argv[1:]) if arg else (say("usage: clio test red <task-id>... [--base <rev>] [--fresh]") or 1)
    if cmd == "approve":
        return cmd_approve(argv[1:]) if arg else (say("usage: clio test approve <task-id>...") or 1)
    if cmd == "gate":
        return cmd_gate(arg) if arg else (say("usage: clio test gate <task-id>") or 1)
    if cmd == "fp":
        say(fpm.fp(ROOT, RUNS))
        return 0
    say(USAGE)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
