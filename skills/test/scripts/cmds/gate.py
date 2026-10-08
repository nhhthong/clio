"""`clio test gate <task-id>` — exit 0 only when every case of a plan task has fresh, complete,
passing evidence: approval hash, LEVELS.md bullet coverage, no shared commands, red/flaky/mutation
checks. It reads runs.jsonl; it runs no test itself.

cmd_gate only gathers what the checks read (a Gate) and calls them in order; each check_* is one
rule and says its own FAIL lines through g.fail. The order is the output's order."""
import re

import testcore as tc
from cliolib import common as c
from cliolib import fingerprint as fpm
from cliolib import store


class Gate:
    """What every check reads, gathered once: the task's case rows, the ledger, the current
    fingerprint, the plan task's levels and the project's mutation settings."""

    def __init__(self, task, rows, recs, cur):
        self.task, self.rows, self.recs, self.cur = task, rows, recs, cur
        self.fails = 0
        self.levels, self.critical = "", False
        self.no_mutation, self.mutation_req = False, tc.MUTATION_MIN_THRESHOLD
        self.mut_ok, self.waived = "", set()

    def fail(self, msg):
        tc.say("FAIL: " + msg)
        self.fails += 1

    def last_run(self, cid):
        """The last run of THIS code: a `red` run (red_base) ran on the base commit's code in a
        worktree — it feeds the red check, never the "is it passing now" one."""
        return next((r for r in reversed(self.recs) if r.get("case") == cid and not c.truthy(r.get("red_base"))), None)


def check_approval(g):
    task = g.task
    arec = next((r for r in reversed(g.recs) if r.get("approve") == task), None)
    approved = arec.get("hash") if arec and c.truthy(arec.get("hash")) else ""
    if not approved:
        g.fail("%s: case table never approved — show it to the user, then `clio test approve %s`" % (task, task))
    elif approved != tc.table_hash(task):
        # Say what moved, when the approval recorded its parts (4.2.0+): a new excuse reads very
        # differently from an edited case, and the user should not have to diff to tell which.
        what = "a case added, removed or edited, or a list line"
        if c.truthy(arec.get("cases")) and c.truthy(arec.get("lists")):
            what = ""
            if arec["cases"] != tc.hash_of(tc.case_part(task)):
                what = "case rows (added, removed or edited)"
            if arec["lists"] != tc.hash_of(tc.list_part(task)):
                what = (what + " and " if what else "") + "`Not applicable` / `Red waived` lines"
            what = what or "the table"
        g.fail("%s: case table changed since it was approved (%s) — changed: %s; show the change and get the user's yes again"
               % (task, approved, what))


def load_plan(g):
    """The plan's levels as one cell: "critical · unit, api" or "unit, api". False (said) when the task
    cannot be gated: in no plan, in two, superseded or void."""
    task = g.task
    found = [r for r in store.plan_rows() if r[1] == task]
    if not found:
        tc.say("FAIL: task %s is in no %s/*.jsonl record — the gate needs the plan's levels" % (task, tc.PLANS))
        return False
    if len(found) > 1:
        tc.say("FAIL: task %s lives in %s — one id, one area; void one of them" % (task, " and ".join(r[0] for r in found)))
        return False
    done, levels = found[0][6], found[0][4]
    if done.startswith(("superseded", "void")):
        tc.say("FAIL: task %s is %s — gate the task that replaced it" % (task, done))
        return False
    g.levels, g.critical = levels, "critical" in levels
    return True


def load_mutation(g):
    """On a critical task a passing mutation case proves what red would — the tests catch injected
    faults — so it stands in for red on every case of the task. Mutation is required only where the
    plan names it (the user agreed the task is beyond critical), never implied by `critical`.
    A `mutation` record with tool "none" is an ADR against it, so a row still naming it is a
    contradiction to resolve, not a level to waive quietly. The threshold a mutation case's command
    must show: the project's own `NN%` if it set one, else LEVELS.md's default — one number for
    every mutation case of the task."""
    for r in g.rows:
        if r[2] == "mutation" and r[7] == "":
            lr = g.last_run(r[0])
            if lr is not None and lr.get("result") == "pass" and lr.get("fp") == g.cur and lr.get("cmd") == r[4]:
                g.mut_ok = r[0]
    g.waived = {cid for cid, _ in store.waiver_rows()}
    m = store.mutation()
    if m is not None:
        g.no_mutation = c.tostring(m.get("tool")).strip().lower() == "none"
        if isinstance(m.get("threshold"), int) and not isinstance(m.get("threshold"), bool):
            g.mutation_req = m["threshold"]


def check_levels(g):
    """Every plan level has a runnable case; every LEVELS.md id of it is covered or excused."""
    task, rows = g.task, g.rows
    excused = {i for i, _ in tc.na_lines(task)}
    for l in g.levels.replace("critical", "").replace(",", " ").replace("·", " ").split():
        if l not in tc.LEVELS.split():
            g.fail("%s: plan level '%s' is not one of: %s" % (task, l, tc.LEVELS))
            continue
        if l == "mutation" and g.no_mutation:
            g.fail("%s: plan names 'mutation' but the project's mutation record says tool none — re-plan the task without it, or change the ADR" % task)
            continue
        if not any(r[2] == l and r[4] not in tc.NA for r in rows):
            g.fail("%s: plan requires level '%s', no runnable case covers it" % (task, l))
            continue
        # Bullet coverage: only for a level LEVELS.md gives ids, and only once this task has at least
        # one Covers-tracked row for it — a pre-4.1 case table (no Covers column) is grandfathered.
        req_ids = tc.level_ids(l)
        tracked = [r for r in rows if r[2] == l and r[6] == 1]
        if not req_ids or not tracked:
            continue
        covered = set()
        for r in tracked:
            covered.update(x.strip(" \t") for x in re.split(r"[,·]", r[3]))
        covered -= set(tc.NA)
        for rid in req_ids:
            if rid not in covered and rid not in excused:
                g.fail("%s: %s has no case covering %s and no `Not applicable` line for it — LEVELS.md § %s" % (task, l, rid, l))


def check_shared_commands(g):
    """One case, one command: a command reused under another case (or level) proves nothing new."""
    by_cmd = {}
    for r in g.rows:
        if r[4] not in tc.NA:
            by_cmd.setdefault(r[4], []).append(r[0])
    for ids in by_cmd.values():
        if len(ids) > 1:
            g.fail("%s: cases %s run the same command — one case, one command" % (g.task, ", ".join(ids)))


def check_row_rules(g, cid, level, cmd, rep):
    """What the row itself must say, whatever the runs: concurrency repeats, a mutation threshold."""
    if level == "concurrency" and rep < tc.CONCURRENCY_MIN_REPEAT:
        g.fail("%s: concurrency case repeats %d < %d" % (cid, rep, tc.CONCURRENCY_MIN_REPEAT))
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
            g.fail("%s: mutation command contains `#` — bash -c drops everything after it; pass the threshold as a real flag" % cid)
        elif low < g.mutation_req:
            g.fail("%s: mutation command shows no threshold >= %d%% (lowest threshold flag: %s) — pass it as --thresholds.break N / -DmutationThreshold=N / --threshold N / --min-score N; default is %d, override with the `threshold` of the plan's `mutation` record"
                   % (cid, g.mutation_req, "none" if low < 0 else low, tc.MUTATION_MIN_THRESHOLD))


def check_last_run(g, cid, cmd, rep):
    """The last run on this code passed, with this command, as many times as Repeat. Returns that
    run, or None (said) when there is none that passed."""
    last = g.last_run(cid)
    if last is None:
        g.fail(cid + ": never run")
        return None
    if last.get("result") != "pass":
        if c.truthy(last.get("batch")) and last.get("runs") == 0 and last.get("exit") == 124:
            g.fail(cid + ": the batch it ran in timed out before this case's own report entry appeared — "
                         "raise CLIO_TIMEOUT or shrink the batch, not this case")
        else:
            g.fail(cid + ": last run failed")
        return None
    if last.get("fp") != g.cur:
        g.fail(cid + ": code changed since the last pass — re-run (see `git status --short`; a test output that is not gitignored counts as code)")
    if last.get("cmd") != cmd:
        g.fail(cid + ": command changed since the last pass — re-run")
    runs_ = last.get("runs")
    if not (isinstance(runs_, (int, float)) and not isinstance(runs_, bool) and runs_ >= rep):
        g.fail("%s: ran fewer times than Repeat %d" % (cid, rep))
    return last


def check_flaky_and_red(g, cid, level, cmd, last):
    """Only runs of this command count, in file order (runs.jsonl is append-only).
      flaky — it failed on this very code after passing on it: same fp, both results.
      red   — it failed before a pass on this code, with the test files as they were at that pass
              and the code under test different: the case can tell them apart. A run from before
              4.2.0 carries no tfp/cfp and is judged the old way (any other fp).
    A batch record the report did not show (timed out, build broke) never ran the case: it is
    neither a flake nor a red.
    ponytail: a fail at this fp *before* its first pass is forgiven (a DB not yet up); a real flake
    that happens to fail first slips through — Repeat is what catches those."""
    cur, task = g.cur, g.task
    mine = [r for r in g.recs if r.get("case") == cid and r.get("cmd") == cmd
            and not (c.truthy(r.get("batch")) and r.get("runs") == 0)]
    p = [k for k, r in enumerate(mine) if r.get("fp") == cur and r.get("result") == "pass"]
    flaky = bool(p) and any(k > p[0] and r.get("fp") == cur and r.get("result") == "fail" for k, r in enumerate(mine))
    red = False
    if p:
        okr = mine[p[-1]]
        for k, r in enumerate(mine):
            if k >= p[-1] or r.get("result") != "fail":
                continue
            if c.truthy(r.get("tfp")) and c.truthy(okr.get("tfp")):
                if r.get("tfp") == okr.get("tfp") and r.get("cfp") != okr.get("cfp"):
                    red = True
            elif r.get("fp") != cur:
                red = True
    if flaky:
        g.fail(cid + ": flaky — failed on this code after passing on it; /clio:memo files it as code-debt `flaky:`")
    if red:
        return
    # A test never seen failing may pass by construction. Regression must prove it reproduced the
    # bug; on a critical task every case must. A mutation case is exempt: its red is a score below
    # threshold. Only these two need red; any other case was checked by its spec-sourced Expected
    # and the approval.
    if level == "regression":
        g.fail("%s: regression case never failed, with this command and these test files, on code before the fix — `clio test red %s`, then run-task" % (cid, task))
    elif level == "mutation" or not g.critical:
        return
    elif g.mut_ok:
        tc.say("NOTE: %s: no red of its own — covered by mutation case %s passing on this code" % (cid, g.mut_ok))
    elif cid in g.waived:
        # A waiver stands only on a tried red — a `red` run of this command, with the test files
        # of the pass, that PASSED on a base commit: the behaviour was already right there.
        t = last.get("tfp") if c.truthy(last.get("tfp")) else ""
        if any(c.truthy(r.get("red_base")) and r.get("result") == "pass" and r.get("tfp") == t for r in mine):
            tc.say("NOTE: %s: red waived (approved) — passed on a base commit with these tests; the behaviour predates the task" % cid)
        else:
            g.fail("%s: red waived, but no `red` run of it passed on a base commit with these test files — run `clio test red %s --base <commit>` first: a waiver stands only on a tried red" % (cid, task))
    else:
        g.fail("%s: never seen red on a critical task — `clio test red %s` (add --base <commit> if the change is committed), then run-task; red not reproducible because the behaviour was always right → a mutation case (/clio:plan), or a `Red waived:` line the user approves after a `red` that passed" % (cid, task))


def check_cases(g):
    for cid, _, level, _, cmd, rep, _, err in g.rows:
        if err:
            g.fail("%s: %s" % (cid, err))
            continue
        if cmd in tc.NA:
            continue
        rep = int(rep)
        check_row_rules(g, cid, level, cmd, rep)
        last = check_last_run(g, cid, cmd, rep)
        if last is not None:
            check_flaky_and_red(g, cid, level, cmd, last)


def cmd_gate(task):
    cur = fpm.fp(tc.ROOT, tc.RUNS)
    # A line the store cannot read may be the newer state of this very task or case: judging the older
    # record behind it could pass what the user changed. Refuse until the line is fixed.
    bad = store.bad_lines()
    if bad:
        for b in bad:
            tc.say("FAIL: %s is not a JSON record — only `clio add` and `clio test` write the stores; fix or remove it" % b)
        return 1
    rows = tc.cases(task)
    if not rows:
        plan = [r for r in store.plan_rows() if r[1] == task]
        if plan and plan[0][6].startswith(("superseded", "void")):    # nothing to prove for a task that was dropped
            tc.say("FAIL: task %s is %s — gate the task that replaced it, if any" % (task, plan[0][6]))
        else:
            tc.say("FAIL: task %s has no cases — run /clio:test %s" % (task, task))
        return 1
    g = Gate(task, rows, tc.records(), cur)
    check_approval(g)
    if not load_plan(g):
        return 1
    load_mutation(g)
    check_levels(g)
    check_shared_commands(g)
    check_cases(g)
    if g.fails == 0:
        tc.say("OK: task %s — every case passed at %s" % (task, cur))
        return 0
    return 1
