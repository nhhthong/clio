"""`clio test red <task-id>... [--base <rev>] [--fresh]` — the cases that must be seen red (every
`regression` case, every non-mutation case of a `critical` task), run on a base commit's code in a
kept, reused git worktree with today's test files — red without anyone breaking code by hand."""
import os
import shutil
import sys
import time

import testcore as tc
from cliolib import common as c
from cliolib import fingerprint as fpm
from cliolib import store
from cliolib import tables


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
                tc.say("FAIL: --base needs a commit")
                return 1
            base, i = args[i + 1], i + 2
        elif args[i] == "--fresh":
            fresh, i = True, i + 1
        else:
            tasks.append(args[i])
            i += 1
    if not tasks:
        tc.say("usage: clio test red <task-id>... [--base <rev>] [--fresh]")
        return 1
    if c.git(["rev-parse", "-q", "--verify", base + "^{commit}"]).returncode != 0:
        tc.say("FAIL: %s is not a commit" % base)
        return 1
    rows = tc.cases()
    prows = store.plan_rows()
    ids = []
    for task in tasks:
        levels = next((r[4] for r in prows if r[1] == task), None)
        if levels is None:
            tc.say("FAIL: task %s is in no %s/*.jsonl record — nothing run" % (task, tc.PLANS))
            return 1
        crit = "critical" in levels
        ids += [r[0] for r in rows if r[1] == task and r[4] not in (tables.DASH, "-")
                and (r[2] == "regression" or (crit and r[2] != "mutation"))]
    if not ids:
        tc.say("nothing needs red in %s: no regression case, no critical task — run-task is enough" % " ".join(tasks))
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
        tc.say("FAIL: another `clio test red` is running (or died: rmdir %s.lock)" % wt)
        return 1
    try:
        c.git(["worktree", "prune"])
        stamped = open(stamp).read().strip() if os.path.isfile(stamp) else ""
        if not fresh and stamped == sha and c.git(["rev-parse", "--git-dir"], cwd=wt).returncode == 0:
            c.git(["checkout", "-q", "--detach", "--force", sha], cwd=wt)
            c.git(["clean", "-fdq"], cwd=wt)   # ignored build output stays
            tc.say("note: reusing the red worktree at %s — only changed files rebuild (--fresh to start over)" % sha[:7])
        else:
            c.git(["worktree", "remove", "--force", wt])
            if wt.endswith("/clio-red") and os.path.lexists(wt):
                shutil.rmtree(wt)
            if c.git(["worktree", "add", "-q", "--detach", wt, sha]).returncode != 0:
                tc.say("FAIL: cannot create a worktree at %s" % base)
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
        tc.link_deps(wt)

        label = c.git_out(["rev-parse", "--short", base])
        # Every failure's output is printed by run/run_batch: read it — a red counts only on an assertion.
        n0 = len(tc.records())
        out = sys.stdout
        sys.stdout = tc.Prefixed(out, "  | ")
        try:
            tc.run_cases(wt, label, ids)
        finally:
            sys.stdout = out
        n = bad = 0
        for cid, r in tc.last_results(ids, n0):
            n += 1
            if r == "pass":
                tc.say("NOT RED: %s passed on %s — it cannot tell that code from yours (change already committed? --base <the commit before it>)" % (cid, label))
                bad += 1
            elif r == "notrun":
                tc.say("NOT RED: %s did not run on %s — the report does not show it (build error?); a red must fail an assertion" % (cid, label))
                bad += 1
            elif r == "never":
                tc.say("NOT RED: %s did not run — its row cannot run (see the FAIL above)" % cid)
                bad += 1
            else:
                tc.say("red: %s failed on %s" % (cid, label))
        tc.say("red on %s: %d/%d cases failed as they must" % (label, n - bad, n))
        tc.say("took %d s" % int(time.monotonic() - t0))
        return 0 if bad == 0 else 1
    finally:
        os.rmdir(wt + ".lock")
