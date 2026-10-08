#!/usr/bin/env python3
"""clio test run <case-id> | run-task <task-id>... | red <task-id>... [--base <rev>] [--fresh] | approve <task-id>... | diff <task-id>... | gate <task-id> | tick <task-id> [--commit h] | withdraw <task-id>... | coverage <task-id> | history <case-id> | migrate [--write] | fp
  run       run one case from .claude/clio/database/test/*.jsonl `repeat` times, append the result to runs.jsonl
  run-task  run every case of each task that way — one call proves a whole task
  red       run the cases that must be seen red (regression, critical) on the code at a base commit,
            in a kept worktree with today's tests — red without breaking code by hand
  approve   record the hash of each task's case rows once the user approved them (one batch, one yes);
            the gate holds each table to its own hash
  gate      exit 0 only if every case of a plan task has fresh, complete, passing evidence
  tick      the gate, then mark the plan task done — the only way a task becomes done
  withdraw  void done tasks whose work never left the working tree (needs the user's yes, like approve)
  diff      what changed in each task's cases since its last approval, one line per kind of edit
  migrate   move a 4.x project's Markdown plans and case tables into the stores (--write to do it)
  coverage  per case of a task: level and last recorded result (pass/fail/never) — what /clio:plan
            reads to decide whether a ticked task's tests fall short
  history   every recorded run of one case, oldest first
  fp        print the working-tree fingerprint evidence is bound to
The model never writes runs.jsonl itself: a pass exists only because this script saw exit 0.
Python 3.9+, standard library only; every caller reaches it as `clio test` (bin/clio).
The engine — case/plan tables, the run ledger, fingerprint-bound execution, the batch merge — is
testcore.py; every subcommand beyond the two one-liners below (`run`, `fp`) is its own module under
cmds/. This file only parses argv and dispatches."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)   # so "testcore" and "cmds" resolve as top-level modules
import testcore as tc  # noqa: E402
from cliolib import common as c  # noqa: E402
from cliolib import fingerprint as fpm  # noqa: E402
from cmds.approve import cmd_approve  # noqa: E402
from cmds.coverage import cmd_coverage  # noqa: E402
from cmds.diff import cmd_diff  # noqa: E402
from cmds.gate import cmd_gate  # noqa: E402
from cmds.history import cmd_history  # noqa: E402
from cmds.migrate import cmd_migrate  # noqa: E402
from cmds.red import cmd_red  # noqa: E402
from cmds.run_task import cmd_run_task  # noqa: E402
from cmds.withdraw import cmd_withdraw  # noqa: E402
from cmds.tick import cmd_tick  # noqa: E402

USAGE = ("usage: clio test run <case-id> | run-task <task-id>... | red <task-id>... [--base <rev>] [--fresh]"
         " | approve <task-id>... | diff <task-id>... | gate <task-id> | tick <task-id> [--commit h] | coverage <task-id> | history <case-id> | migrate [--write] | fp")


def main(argv):
    tc.ROOT = c.find_root()
    if not tc.ROOT:
        tc.say("FAIL: no .claude/clio above " + os.getcwd())
        return 1
    os.chdir(tc.ROOT)
    if not c.is_git():
        tc.say("FAIL: clio-test needs a git repository — evidence is bound to the working tree")
        return 1
    tc.RUNS = os.path.join(tc.ROOT, ".claude/clio/database/runs.jsonl")   # absolute: `red` runs cases from a worktree
    open(tc.RUNS, "a").close()
    cmd = argv[0] if argv else ""
    arg = argv[1] if len(argv) > 1 else ""
    if cmd == "coverage":
        return cmd_coverage(arg) if arg else (tc.say("usage: clio test coverage <task-id>") or 1)
    if cmd == "history":
        return cmd_history(arg) if arg else (tc.say("usage: clio test history <case-id>") or 1)
    if cmd == "run":
        if not arg:
            tc.say("usage: clio test run <case-id>")
            return 1
        try:
            return 0 if tc.run(arg) else 1
        except tc.CaseError as e:
            tc.say(str(e))
            return 1
    if cmd == "run-task":
        return cmd_run_task(argv[1:]) if arg else (tc.say("usage: clio test run-task <task-id>...") or 1)
    if cmd == "red":
        return cmd_red(argv[1:]) if arg else (tc.say("usage: clio test red <task-id>... [--base <rev>] [--fresh]") or 1)
    if cmd == "approve":
        return cmd_approve(argv[1:]) if arg else (tc.say("usage: clio test approve <task-id>...") or 1)
    if cmd == "gate":
        return cmd_gate(arg) if arg else (tc.say("usage: clio test gate <task-id>") or 1)
    if cmd == "diff":
        return cmd_diff(argv[1:]) if arg else (tc.say("usage: clio test diff <task-id>...") or 1)
    if cmd == "withdraw":
        return cmd_withdraw(argv[1:]) if arg else (tc.say("usage: clio test withdraw <task-id>...") or 1)
    if cmd == "tick":
        return cmd_tick(argv[1:]) if arg else (tc.say("usage: clio test tick <task-id> [--commit <hash>]") or 1)
    if cmd == "migrate":
        return cmd_migrate(argv[1:])
    if cmd == "fp":
        tc.say(fpm.fp(tc.ROOT, tc.RUNS))
        return 0
    tc.say(USAGE)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
