#!/usr/bin/env python3
USAGE = """# clio q — every read of Clio's ledgers, in one place. Read-only.
#   summary                                   plans done/open + next task, debt queue/blocked, last memo
#   built  [--req R --spec S --file F --area A --keyword K --task T --id I]   current state per doc
#   owed   [--req R --spec S --area A --q WORD --id I] [--all]                 open debt, queue first
#   history <id>                              a doc's timeline + what its last run added/removed
#   keywords                                  keyword vocabulary, most used first
#   rules  <file>...                          .claude/rules/*.md whose paths: match the files
#   changed                                   files this work touched: uncommitted + untracked, .claude/ excluded
#   commit <file>...                          the commit holding these files — empty while any is uncommitted
#   unrecorded [N]                            commits since the last one any index record names: hash<TAB>docs|-
#   spec-mark                                 snapshot the spec files (committed or not) as ingest's baseline
#   spec-diff [git-diff args]                 spec files now vs that baseline — hand edits since the last ingest
# Filters are OR'd; none given → everything. `req` compares as a string, so 7.1 and 7.10 stay apart."""
import fnmatch
import glob
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from cliolib import common as c  # noqa: E402
from cliolib import tables  # noqa: E402

IDX = ".claude/clio/database/index.jsonl"
DEBT = ".claude/clio/database/debt.jsonl"
PLANS = ".claude/clio/docs/plans"
SPECS = ".claude/clio/docs/specs"
FILTERS = {"--req": "r", "--spec": "s", "--file": "f", "--area": "a", "--keyword": "k",
           "--task": "t", "--id": "i", "--q": "q"}


def out(v):
    print(c.dumps(v))


def parse(args):
    """--flag value pairs into {r, s, f, a, k, t, i, q, all}; an unknown flag ends the run."""
    opt = dict.fromkeys("rsfaktiq", "")
    opt["all"] = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--all":
            opt["all"] = True
            i += 1
            continue
        if a not in FILTERS:
            print("unknown filter: " + a, file=sys.stderr)
            sys.exit(1)
        opt[FILTERS[a]] = args[i + 1] if i + 1 < len(args) else ""
        i += 2
    return opt


def docs(recs):
    """One group per document across the 3.0 id migration: a path maps to the id that later claimed
    it, by `doc` (stayed put) or `supersedes` (moved). Returns each group's last record."""
    m = {}
    for r in recs:
        if c.truthy(r.get("id")):
            m[r.get("doc")] = r.get("id")
    for r in recs:
        if c.truthy(r.get("supersedes")):
            m[r.get("supersedes")] = r.get("id")

    def key(r):
        for v in (r.get("id"), m.get(r.get("doc")), r.get("doc")):
            if c.truthy(v):
                return v
        return r.get("doc")
    return [g[-1] for g in c.group_by([r for r in recs if isinstance(r, dict)], key)]


def none(o):
    return (o["r"] + o["s"] + o["f"] + o["a"] + o["k"] + o["t"] + o["i"] + o["q"]) == ""


def by_req(o, r):
    return o["r"] != "" and any(c.tostring(x) == o["r"] for x in c.items(r.get("req")))


def by_spec(o, r):
    return o["s"] != "" and any(c.contains(x, o["s"]) for x in c.items(r.get("specs")))


def built_match(o, r):
    return (none(o) or by_req(o, r) or by_spec(o, r)
            or (o["f"] != "" and any(c.contains(x, o["f"]) for x in c.items(r.get("files"))))
            or (o["a"] != "" and r.get("domain") == o["a"])
            or (o["k"] != "" and any(c.contains(x, o["k"]) for x in c.items(r.get("keywords"))))
            or (o["t"] != "" and any(c.tostring(x) == o["t"] for x in c.items(r.get("plan_tasks"))))
            or (o["i"] != "" and r.get("id") == o["i"]))


def built(args):
    o = parse(args)
    for r in docs(c.read_valid(IDX)):
        if built_match(o, r):
            out(r)


def owed(args):
    o = parse(args)
    recs = [r for r in c.read_valid(DEBT) if isinstance(r, dict)]
    last = [g[-1] for g in c.group_by(recs, lambda r: r.get("id"))]
    picked = []
    for r in last:
        if not (o["all"] or r.get("status") != "done"):
            continue
        q = o["q"]
        if (none(o) or by_req(o, r) or by_spec(o, r)
                or (o["a"] != "" and r.get("domain") == o["a"])
                or (o["i"] != "" and r.get("id") == o["i"])
                or (q != "" and (r.get("domain") == q
                                 or any(c.tostring(x) == q for x in c.items(r.get("req")))
                                 or any(c.contains(x, q) for x in c.items(r.get("specs")))
                                 or any(c.contains(x, q) for x in c.items(r.get("what")))))):
            picked.append(r)
    for r in sorted(picked, key=lambda r: r.get("blocked_by") is not None):   # queue first, stable
        out(r)


def minus(a, b):
    """jq's array subtraction: a's items, in order, minus every one b holds."""
    b = [c.dumps(x) for x in c.items(b)]
    return [x for x in c.items(a) if c.dumps(x) not in b]


def history(args):
    if not args:
        print("usage: clio q history <id>", file=sys.stderr)
        sys.exit(1)
    rs = [r for r in c.read_valid(IDX) if isinstance(r, dict)
          and (r.get("id") == args[0] or r.get("doc") == args[0])]
    for r in rs:
        out(r)
    if len(rs) > 1:
        out({"changed": rs[-1].get("date"), "added": minus(rs[-1].get("files"), rs[-2].get("files")),
             "removed": minus(rs[-2].get("files"), rs[-1].get("files"))})


def keywords():
    counts = {}
    for r in docs(c.read_valid(IDX)):
        for k in c.items(r.get("keywords")):
            k = c.tostring(k)
            counts[k] = counts.get(k, 0) + 1
    # `uniq -c | sort -rn`: most used first; a tie falls back to the line compared in reverse
    for k, n in sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)[:30]:
        print("%7d %s" % (n, k))


def summary():
    plans = sorted(glob.glob(PLANS + "/*.md"))
    if not plans:
        print("no plans — /clio:plan has not been run")
    # Every plan's rows at once: `next` may wait on a task ticked in another area (0.4 in infra).
    rows = tables.plan_rows(plans)
    ok = {r[1] for r in rows if r[6].startswith("[x]")}
    for p in plans:
        name = os.path.basename(p)[:-3]
        mine = [r for r in rows if r[0] == p]
        if mine:
            # next = the first open row whose Needs are all ticked; none ready → the first open row, and
            # what it waits on. A superseded row is neither open nor done.
            d = o = 0
            ready = first = firstw = ""
            for r in mine:
                if r[6].startswith("[x]"):
                    d += 1
                elif r[6].startswith("[ ]"):
                    o += 1
                    waits = [n for n in re.split(r"[ ,]+", r[5]) if n[:1].isdigit() and n not in ok]
                    line = "%s | %s | %s" % (r[1], r[2], r[4])
                    if not waits and ready == "":
                        ready = line
                    if first == "":
                        first, firstw = line, ", ".join(waits)
            nx = ready if ready else (first + " (waits on " + firstw + ")" if first else "")
            print("%s: done=%d open=%d next: %s" % (name, d, o, nx))
        else:
            # A plan lifted from an old requirements.md may still be bullets: no table to parse, so show
            # the first open bullet, cut short.
            lines = tables.read_lines(p)
            opens = [l for l in lines if "[ ]" in l]
            n = re.sub(r" +", " ", opens[0][:80]) if opens else ""
            print("%s: done=%d open=%d next: %s" % (name, sum("[x]" in l for l in lines), len(opens), n))
    debt = [r for r in c.read_valid(DEBT) if isinstance(r, dict)]
    open_ = [g[-1] for g in c.group_by(debt, lambda r: r.get("id")) if g[-1].get("status") != "done"]
    print("debt: queue=%d blocked=%d" % (sum(r.get("blocked_by") is None for r in open_),
                                         sum(r.get("blocked_by") is not None for r in open_)))
    idx = c.read_valid(IDX)
    if not idx:
        print("last memo: none yet")
    else:
        print("last memo: %s %s" % (c.tostring(idx[-1].get("date")), c.tostring(idx[-1].get("doc"))))


def changed():
    if not c.is_git():
        print("not a git repository — take the file list from the session", file=sys.stderr)
        sys.exit(0)
    # -z: paths with spaces arrive unquoted; a rename is "XY new\0old\0", so the old path is skipped.
    entries = c.git(["status", "--porcelain=v1", "-z", "-uall"]).stdout.split("\0")
    i = 0
    while i < len(entries):
        e = entries[i]
        i += 1
        if not e:
            continue
        st, p = e[:2], e[3:]
        if st[0] in "RC":
            i += 1
        if p.startswith(".claude/"):
            continue
        print(p)


def commit(args):
    # Empty is a valid answer: not a repo, no commit yet, or part of this work still uncommitted.
    if not args or c.git(["rev-parse", "--verify", "-q", "HEAD"]).returncode != 0:
        return
    if c.git(["status", "--porcelain", "--"] + args).stdout.strip():
        return
    h = c.git_out(["log", "-1", "--format=%h", "--"] + args)
    if h:
        print(h)


def unrecorded(args):
    if c.git(["rev-parse", "--verify", "-q", "HEAD"]).returncode != 0:
        return
    idx = c.read_valid(IDX)
    # Recorded hashes may be abbreviated to any length; compare on 7 characters.
    rec = set()
    for r in idx:
        if isinstance(r, dict):
            for h in c.items(r.get("commits")) + ([r["commit"]] if c.truthy(r.get("commit")) else []):
                rec.add(c.tostring(h)[:7])
    o = parse([])
    last = docs(idx)
    for h in c.git_out(["log", "-%s" % (args[0] if args else "20"), "--no-merges", "--format=%h"]).split("\n"):
        if not h:
            continue
        if h[:7] in rec:
            break          # everything older was recorded, or predates Clio
        files = [f for f in c.git_out(["show", "--name-only", "--format=", h]).split("\n")
                 if f and not f.startswith(".claude/")]
        if not files:
            continue       # a commit of .claude/ only — Clio's own output
        found = set()
        for f in files:
            o["f"] = f
            found.update(c.tostring(r.get("doc")) for r in last if built_match(o, r))
        print("%s\t%s" % (h, ",".join(sorted(found)) or "-"))


def spec_tree():
    """The spec files' content as a git tree, committed or not, ignored or not — ingest's baseline is
    what the files said, not what was committed."""
    fd, idx = tempfile.mkstemp()
    os.close(fd)
    os.remove(idx)
    try:
        c.git(["add", "-A", "-f", "--", SPECS], env={"GIT_INDEX_FILE": idx})
        return c.git_out(["write-tree"], env={"GIT_INDEX_FILE": idx})
    finally:
        if os.path.exists(idx):
            os.remove(idx)


def spec_mark():
    if not c.is_git():
        print("not a git repository — no baseline to keep", file=sys.stderr)
        sys.exit(1)
    # A commit object under a local ref keeps the tree from `git gc`; refs/clio/* is not pushed by default.
    tree = spec_tree()
    commit_id = c.git_out(["-c", "user.name=clio", "-c", "user.email=clio@localhost",
                           "commit-tree", tree, "-m", "clio: ingest baseline"])
    c.git(["update-ref", "refs/clio/ingest", commit_id])
    print(c.git_out(["rev-parse", "--short", tree]))


def spec_diff(args):
    base = c.git_out(["rev-parse", "-q", "--verify", "refs/clio/ingest^{tree}"])
    if not base:
        print("no ingest baseline in this clone — fall back to the Last ingest commit, or reconstruct",
              file=sys.stderr)
        sys.exit(1)
    sys.exit(subprocess.call(["git", "diff"] + args + [base, spec_tree()]))


def rule_globs(path):
    """A rules file's `paths:` — a YAML list, an inline [a, b] list, or a single string. Only the
    frontmatter is read; no frontmatter, or no `paths:`, reads as none."""
    lines = tables.read_lines(path)
    if not lines or lines[0] != "---":
        return []
    out_, in_paths = [], False
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith("paths:"):
            v = re.sub(r"^paths:[ \t]*", "", line)
            if v != "":
                return [g for g in re.sub(r"""[\[\] "']""", "", v).split(",") if g != ""]
            in_paths = True
            continue
        if in_paths and re.match(r"[ \t]*-", line):
            out_.append(re.sub(r"""["']""", "", re.sub(r"^[ \t]*-[ \t]*", "", line)))
            continue
        in_paths = False
    return out_


def rules(args):
    if not args:
        print("usage: clio q rules <file>...", file=sys.stderr)
        sys.exit(1)
    # ponytail: `**` matches like `*` (crossing `/`). Good enough to name candidates; Claude Code's
    # own matcher is what actually loads them.
    for rf in sorted(glob.glob(".claude/rules/**/*.md", recursive=True)):
        globs = rule_globs(rf)
        if not globs:
            print(rf + "  (no paths: — loads every session)")
            continue
        hit = next(((f, g) for f in args for g in globs if fnmatch.fnmatchcase(f, g)), None)
        if hit:
            print("%s  ← %s matches %s" % (rf, hit[0], hit[1]))


def main(argv):
    c.quiet_on_closed_pipe()
    root = c.find_root()
    if not root:
        print("no .claude/clio above %s — run /clio:setup" % os.getcwd(), file=sys.stderr)
        sys.exit(1)
    os.chdir(root)
    cmd, args = (argv[0], argv[1:]) if argv else ("summary", [])
    if cmd == "built":
        built(args)
    elif cmd == "owed":
        owed(args)
    elif cmd == "history":
        history(args)
    elif cmd == "keywords":
        keywords()
    elif cmd == "summary":
        summary()
    elif cmd == "changed":
        changed()
    elif cmd == "commit":
        commit(args)
    elif cmd == "unrecorded":
        unrecorded(args)
    elif cmd == "spec-mark":
        spec_mark()
    elif cmd == "spec-diff":
        spec_diff(args)
    elif cmd == "rules":
        rules(args)
    else:
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
