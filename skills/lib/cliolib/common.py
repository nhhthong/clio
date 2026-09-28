"""What every Clio script needs: the repo root, the JSONL ledgers, git, and JSON the way jq 1.8
reads and writes it — number literals kept as written (7.10 stays 7.10, not 7.1), compact output.
"""
import json
import os
import subprocess
import sys
from decimal import Decimal


def quiet_on_closed_pipe():
    """A read-only script whose reader stopped early (`clio q built | head -1`) ends quietly, as a shell
    pipeline would, instead of printing a BrokenPipeError."""
    import signal
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def find_root(start=None):
    """The nearest directory at or above `start` holding .claude/clio, or None."""
    d = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(d, ".claude", "clio")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def loads(text):
    """JSON with every non-integer number as a Decimal of its literal, so it prints back unchanged."""
    return json.loads(text, parse_float=Decimal)


def truthy(v):
    """jq's truth: everything but null and false (0 and "" are true)."""
    return v is not None and v is not False


def _key(v):
    """jq's sort order: null < false < true < numbers < strings < arrays < objects."""
    if v is None:
        return (0,)
    if v is False:
        return (1,)
    if v is True:
        return (2,)
    if isinstance(v, (int, float, Decimal)):
        return (3, v)
    if isinstance(v, str):
        return (4, v)
    if isinstance(v, list):
        return (5, [_key(x) for x in v])
    return (6, sorted((k, _key(x)) for k, x in v.items()))


def group_by(items, key):
    """jq's group_by: groups ordered by key, each keeping the items' original order."""
    groups = {}
    order = []
    for it in items:
        k = key(it)
        tk = json.dumps(_key(k), default=str)
        if tk not in groups:
            groups[tk] = (k, [])
            order.append(tk)
        groups[tk][1].append(it)
    return [groups[tk][1] for tk in sorted(order, key=lambda t: _key(groups[t][0]))]


def dumps(v):
    """jq -c: compact, keys in their order, non-ASCII as is, numbers as their literal."""
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (int, float)):
        return json.dumps(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return "[" + ",".join(dumps(x) for x in v) + "]"
    return "{" + ",".join(json.dumps(str(k), ensure_ascii=False) + ":" + dumps(x) for k, x in v.items()) + "}"


def tostring(v):
    """jq's tostring: a string as is, anything else as its compact JSON."""
    return v if isinstance(v, str) else dumps(v)


def items(v):
    """jq's `.[]?`: an array's items, an object's values, nothing for anything else."""
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        return list(v.values())
    return []


def contains(v, s):
    return isinstance(v, str) and s in v


def read_valid(path, err=sys.stderr):
    """The records of a JSONL ledger that parse (null and false dropped, as jq's `fromjson? // empty`),
    saying on `err` how many lines did not — a malformed line must never read as "nothing on record".
    A missing file is said too, and reads as no records."""
    if not os.path.isfile(path):
        print("missing " + path, file=err)
        return []
    with open(path, encoding="utf-8", errors="surrogateescape") as f:
        lines = f.read().split("\n")
    total, out = 0, []
    for line in lines:
        if line == "":
            continue
        total += 1
        try:
            v = loads(line)
        except ValueError:
            continue
        if truthy(v):
            out.append(v)
    if total != len(out):
        print("WARN: %s has %d malformed line(s) — results are partial, run clio validate all"
              % (path, total - len(out)), file=err)
    return out


def git(args, cwd=None, env=None, input=None, check=False):
    """git with its output captured as text; returns the CompletedProcess."""
    e = None
    if env:
        e = dict(os.environ)
        e.update(env)
    return subprocess.run(["git"] + list(args), cwd=cwd, env=e, input=input,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, errors="surrogateescape", check=check)


def git_out(args, cwd=None, env=None, input=None):
    """git's stdout, trailing newline dropped; "" when git fails."""
    p = git(args, cwd=cwd, env=env, input=input)
    return p.stdout.rstrip("\n") if p.returncode == 0 else ""


def is_git(cwd=None):
    return git(["rev-parse", "--git-dir"], cwd=cwd).returncode == 0
