#!/usr/bin/env python3
"""clio_nudge.py — UserPromptSubmit hook. Once per session, tells Claude that work exists which
/clio:memo has not recorded yet. Reminder only: it reads git and index.jsonl and writes neither
ledger. Silence (exit 0, no output) is the normal case — it speaks only when the loop has drifted.
Python 3.9+, standard library only."""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "lib"))
from cliolib.common import unrecorded_commits  # noqa: E402

IDX = ".claude/clio/database/index.jsonl"


def git(*args):
    p = subprocess.run(["git"] + list(args), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                       universal_newlines=True, encoding="utf-8", errors="surrogateescape")
    return p.returncode, p.stdout


def ledger():
    """index.jsonl's records that parse — a malformed line must not make every commit look
    unindexed and nag forever."""
    out = []
    with open(IDX, encoding="utf-8", errors="surrogateescape") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict):
                out.append(r)
    return out


def items(v):
    return v if isinstance(v, list) else list(v.values()) if isinstance(v, dict) else []


def text(v):
    return v if isinstance(v, str) else json.dumps(v)


def main():
    try:
        data = json.loads(sys.stdin.read())
    except ValueError:
        return
    if not isinstance(data, dict):
        return
    sid = data.get("session_id") or "nosid"
    cwd = data.get("cwd") or ""
    if cwd:
        try:
            os.chdir(cwd)
        except OSError:
            pass
    # No Clio here, or the loop never started: /clio:setup already said the loop is manual. Say nothing.
    if not (os.path.isfile(IDX) and os.path.getsize(IDX) > 0):
        return
    if git("rev-parse", "--git-dir")[0] != 0:
        return
    # One nudge per session. TMPDIR is session-scoped enough and keeps the marker out of the user's
    # repo. The session id becomes a path, so strip anything that could walk out of the directory.
    sid = re.sub(r"[^A-Za-z0-9._-]", "", text(sid)) or "nosid"
    mark = os.path.join(os.environ.get("TMPDIR") or "/tmp", "clio-nudge-" + sid)
    if os.path.exists(mark):
        return

    recs = ledger()
    # --porcelain, not `git diff HEAD`: a brand-new file nobody has `git add`ed yet is exactly the
    # work most likely to be missing from the ledger, and `git diff` cannot see it. -z: a path with a
    # space or non-ASCII byte arrives unquoted, so it can match the ledger; a rename is
    # "XY new\0old\0", so the old path is skipped. [3:] drops the two status columns.
    # .claude/ is excluded: /clio:memo writes there, so counting it would nag about memo's own output.
    # A file some index record already lists was recorded while uncommitted — the memo happened, the
    # commit simply hasn't. ponytail: path match only, so further edits to an already-recorded file
    # after its memo go unnoticed until HEAD moves; compare content if that ever matters.
    recorded = {text(f) for r in recs for f in items(r.get("files"))}
    entries = git("status", "--porcelain", "-z")[1].split("\0")
    paths, i = [], 0
    while i < len(entries):
        e = entries[i]
        i += 2 if e[:1] in ("R", "C") else 1
        if e[3:]:
            paths.append(e[3:])
    dirty = sum(1 for p in paths if not p.startswith(".claude/") and p not in recorded)

    # The commits `clio q unrecorded` lists — one definition for both: merges and .claude/-only commits
    # are not work to record, a `chore` record owns the ones the user said belong to no task.
    pending = unrecorded_commits(recs)
    if dirty == 0 and not pending:
        return

    # Cannot record that we nudged → do not nudge: silence beats the same line on every prompt.
    try:
        open(mark, "w").close()
    except OSError:
        return

    msg = "clio: work is not recorded in .claude/clio/database/index.jsonl — "
    if dirty > 0:
        msg += "%d uncommitted change(s) in the working tree" % dirty
    if dirty > 0 and pending:
        msg += "; "
    if pending:
        msg += "commit %s%s appears in no index record (recorded before it was committed? /clio:memo only backfills the hash)" % (
            pending[0][0], " and %d older" % (len(pending) - 1) if len(pending) > 1 else "")
    print(msg + ".")
    print("Tell the user once that /clio:memo is owed for this work, then carry on with their request.")
    print("This notice is not permission to run it. Only the user asking is — they decide the work is done.")


if __name__ == "__main__":
    main()
