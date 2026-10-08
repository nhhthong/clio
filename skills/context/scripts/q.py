#!/usr/bin/env python3
USAGE = """# clio q — every read of Clio's ledgers, in one place. Read-only.
#   summary                                   plans done/open + next task, debt queue/blocked, last memo, and
#                                              `suggest:` lines — what to do next, from the state alone
#   built  [--req R --spec S --file F --area A --keyword K --task T --id I]   current state per doc
#   owed   [--req R --spec S --area A --q WORD --id I] [--all]                 open debt, queue first
#   history <id>                              a doc's timeline + what its last run added/removed
#   keywords                                  keyword vocabulary, most used first
#   plan   [area...] [--all] [--id T]... [--req R]... [--json]  the plan as a table: open tasks (--all: every status)
#   cases  <task|area>... [--json]           active test cases, then each task's seams, na and waivers
#   spec-grep <regex>                         live spec decisions matching it: bullets already marked Superseded are history, skipped
#   rules  <file>...                          .claude/rules/*.md whose paths: match the files
#   changed                                   files this work touched: uncommitted + untracked, .claude/ excluded;
#                                              says on stderr when the code is the one the last memo recorded
#   commit <file>...                          the commit holding these files — empty while any is uncommitted
#   unrecorded [N]                            commits since the last one any index record names: hash<TAB>docs|-
#   spec-mark [summary...]                    snapshot the spec files (committed or not) as ingest's baseline,
#                                              printed with when + the summary — the only record of it, never
#                                              written into a spec file itself
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
from cliolib import fingerprint as fpm  # noqa: E402
from cliolib import store  # noqa: E402
from cliolib import tables  # noqa: E402

IDX = ".claude/clio/database/index.jsonl"
DEBT = ".claude/clio/database/debt.jsonl"
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
        if opt[FILTERS[a]] != "":     # the second value would silently replace the first: say so
            print("%s given twice — one value per filter (different filters are OR'd)" % a, file=sys.stderr)
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
        if r.get("type") != "chore" and built_match(o, r):
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


def suggest(rows):
    """What to do next, from the state alone — [(command, why)], most urgent first. Nothing here is a
    guess: every line is a fact the ledgers or git show, and the command is the skill that answers it."""
    out = []
    if glob.glob(".claude/clio/docs/plans/*.md") or glob.glob(".claude/clio/docs/tests/*.md"):
        out.append(("/clio:plan", "4.x Markdown plans are still there and nothing reads them: migrate first"))
    idx = c.read_valid(IDX)
    if c.is_git() and idx:      # a project that never memoed has nothing "owed": the drift hook is silent too
        files, same = work_changes()
        pending = c.unrecorded_commits(idx)
        if files and not same:
            out.append(("/clio:memo", "%d file(s) changed since the last memo" % len(files)))
        elif pending:
            out.append(("/clio:memo", "commit %s is in no record (say so if no task owns it)" % pending[0][0]))
    debt = [g[-1] for g in c.group_by([r for r in c.read_valid(DEBT) if isinstance(r, dict)], lambda r: r.get("id"))]
    carried = {c.tostring(r.get("delta")) for _, r in store.current("plan") if r.get("type") == "task" and c.truthy(r.get("delta"))}
    for d in debt:
        if d.get("kind") == "spec-delta" and d.get("status") != "done" and d.get("blocked_by") is None and c.tostring(d.get("id")) not in carried:
            out.append(("/clio:plan %s" % c.tostring(d.get("domain")), "spec-delta %s is open and no task carries it" % c.tostring(d.get("id"))))
            break
    done = {r[1] for r in rows if r[6].startswith("[x]")}
    cased = {r[1] for r in store.case_rows()}
    ready = [r for r in rows if r[6].startswith("[ ]") and all(n in done for n in re.split(r"[ ,]+", r[5]) if n[:1].isdigit())]
    if ready:
        bare = [r for r in ready if r[1] not in cased]
        first = bare[0] if bare else ready[0]
        out.append(("/clio:test %s" % first[1], "%d task(s) ready, %d without cases" % (len(ready), len(bare))))
    waiting = [d for d in debt if d.get("status") != "done" and d.get("blocked_by") is not None and d.get("kind") in ("spec-blocked", "spec-delta")]
    if waiting:
        d = waiting[0]
        out.append(("answer first", "%s (debt %s)%s, then /clio:ingest" % (c.tostring(d.get("blocked_by")), c.tostring(d.get("id")),
                                                                        " and %d more" % (len(waiting) - 1) if len(waiting) > 1 else "")))
    if not out:
        out.append(("describe the next change", "nothing is waiting: a new requirement goes to /clio:ingest, a new task to /clio:plan"))
    return out[:4]


def summary():
    plans = store.files("plan")
    if glob.glob(".claude/clio/docs/plans/*.md"):
        print("4.x plans in .claude/clio/docs/plans/*.md — not read any more: /clio:plan migrates them first")
    if not plans:
        print("no plans — /clio:plan has not been run")
    # Every plan's rows at once: `next` may wait on a task ticked in another area (0.4 in infra).
    rows = store.plan_rows()
    ok = {r[1] for r in rows if r[6].startswith("[x]")}
    for p in plans:
        mine = [r for r in rows if r[0] == p]
        # next = the first open task whose needs are all done; none ready → the first open task, and
        # what it waits on. Superseded and void tasks are neither open nor done.
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
        print("%s: done=%d open=%d next: %s" % (store.area_of(p), d, o, nx))
    debt = [r for r in c.read_valid(DEBT) if isinstance(r, dict)]
    open_ = [g[-1] for g in c.group_by(debt, lambda r: r.get("id")) if g[-1].get("status") != "done"]
    print("debt: queue=%d blocked=%d" % (sum(r.get("blocked_by") is None for r in open_),
                                         sum(r.get("blocked_by") is not None for r in open_)))
    idx = [r for r in c.read_valid(IDX) if isinstance(r, dict) and r.get("type") != "chore"]
    if not idx:
        print("last memo: none yet")
    else:
        print("last memo: %s %s" % (c.tostring(idx[-1].get("date")), c.tostring(idx[-1].get("doc"))))
    for cmd, why in suggest(rows):
        print("suggest: %s — %s" % (cmd, why))


def _cells(*v):
    return "| " + " | ".join(c.tostring(x).replace("|", "\\|") for x in v) + " |"


def _flag_args(args, flags):
    """args → (positional, {flag: [values]}, {switch}) for this file's two table readers."""
    pos, vals, on = [], {}, set()
    i = 0
    while i < len(args):
        a = args[i]
        if a in flags and flags[a] and i + 1 < len(args):
            vals.setdefault(a, []).append(args[i + 1])
            i += 2
            continue
        if a in flags:
            on.add(a)
        else:
            pos.append(a)
        i += 1
    return pos, vals, on


def plan(args):
    """What /clio:plan, /clio:test and /clio:memo read instead of the store files: by default every
    open task, area by area, as one table. A done task is history; --all shows it."""
    pos, vals, on = _flag_args(args, {"--all": False, "--json": False, "--id": True, "--req": True})
    ids = set(vals.get("--id", []))
    reqs = set(vals.get("--req", []))
    picked = []
    for p, r in store.current("plan"):
        if r.get("type") != "task":
            continue
        area = store.area_of(p)
        if pos and area not in pos:
            continue
        if ids and r.get("id") not in ids:
            continue
        if reqs and not reqs & {c.tostring(x) for x in c.items(r.get("req"))}:
            continue
        if not ids and "--all" not in on and r.get("status") != "open":
            continue
        picked.append((area, r))
    if "--json" in on:
        for area, r in picked:
            out(dict({"area": area}, **r))
        return
    if not picked:
        print("no %stasks%s" % ("" if "--all" in on or ids else "open ", " in " + ", ".join(pos) if pos else ""))
        return
    print(_cells("#", "area", "task", "req", "levels", "needs", "touches", "status"))
    print("|---|---|---|---|---|---|---|---|")
    for area, r in picked:
        print(_cells(r.get("id"), area, r.get("task"), ", ".join(c.items(r.get("req"))) or "–", store.levels_cell(r),
                     ", ".join(c.items(r.get("needs"))) or "–", ", ".join(c.items(r.get("touches"))) or "–",
                     store.done_cell(r) + (" · delta " + r["delta"] if c.truthy(r.get("delta")) else "")))
    na = [(r.get("id"), lv, why) for _, r in picked for lv, why in sorted((r.get("na") or {}).items())]
    if na:
        print("\nNot applicable:")
        for tid, lv, why in na:
            print("- %s · %s — %s" % (tid, lv, why))


def cases(args):
    """The approved-or-not case list of tasks (by id) or areas (by name), as the user is shown it."""
    pos, _, on = _flag_args(args, {"--json": False})
    if not pos:
        print("usage: clio q cases <task|area>... [--json]", file=sys.stderr)
        sys.exit(1)
    recs = [(store.area_of(p), r) for p, r in store.current("test")]
    want = [(a, r) for a, r in recs if a in pos or c.tostring(r.get("task") if r.get("type") == "case" else r.get("id")) in pos]
    rows = [r for _, r in want if r.get("type") == "case" and r.get("status") != "removed"]
    metas = [r for _, r in want if r.get("type") == "meta"]
    if "--json" in on:
        for r in rows + metas:
            out(r)
        return
    if not rows and not metas:
        print("no cases for " + " ".join(pos))
        return
    print(_cells("case", "task", "level", "covers", "behaviour", "expected (source)", "command", "repeat"))
    print("|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(_cells(r.get("id"), r.get("task"), r.get("level"), ", ".join(c.items(r.get("covers"))) or "–",
                     r.get("behaviour"), "%s (%s)" % (c.tostring(r.get("expected")), c.tostring(r.get("source"))),
                     "`%s`" % c.tostring(r.get("command")), r.get("repeat")))
    for m in metas:
        if m.get("seams"):
            print("\nSeams %s: %s" % (m.get("id"), ", ".join(c.items(m.get("seams")))))
        for i, why in sorted((m.get("na") or {}).items()):
            print("- not applicable: %s · %s — %s" % (m.get("id"), i, why))
        for cid, why in sorted((m.get("waived") or {}).items()):
            print("- red waived: %s — %s" % (cid, why))


def work_changes():
    """(files, same) — the files git lists as uncommitted or untracked outside .claude/, and whether the
    code is the one the last memo recorded: the last index record's `fp` equals the fingerprint now."""
    # -z: paths with spaces arrive unquoted; a rename is "XY new\0old\0", so the old path is skipped.
    entries = c.git(["status", "--porcelain=v1", "-z", "-uall"]).stdout.split("\0")
    files, i = [], 0
    while i < len(entries):
        e = entries[i]
        i += 1
        if not e:
            continue
        st, p = e[:2], e[3:]
        if st[0] in "RC":
            i += 1
        if not p.startswith(".claude/"):
            files.append(p)
    stored = [c.tostring(r.get("fp")) for r in c.read_valid(IDX) if isinstance(r, dict) and c.truthy(r.get("fp"))]
    same = False
    if files and stored:
        cur = fpm.fp(os.getcwd(), os.path.join(os.getcwd(), ".claude/clio/database/runs.jsonl"))
        same = cur[:12] == stored[-1][:12]
    return files, same


def changed():
    if not c.is_git():
        print("not a git repository — take the file list from the session", file=sys.stderr)
        sys.exit(0)
    files, same = work_changes()
    for p in files:
        print(p)
    # The last index record carries the fingerprint of the code it recorded: the same one now means
    # nothing was touched since that memo, however many files git still lists as uncommitted.
    if same:
        print("unchanged since the last memo (code fingerprint recorded): nothing new to record", file=sys.stderr)


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
    idx = c.read_valid(IDX)
    last = [r for r in docs(idx) if r.get("type") != "chore"]
    o = parse([])
    for h, files in c.unrecorded_commits(idx, args[0] if args else "20"):
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


def spec_mark(args):
    """The baseline lives here, never as a line inside a spec file: anything under docs/specs/ is
    specification, and a bookkeeping line there would be part of its own diff. `summary` (this run's
    ingest report, one line) rides the commit message — the commit's own date is when."""
    if not c.is_git():
        print("not a git repository — no baseline to keep", file=sys.stderr)
        sys.exit(1)
    summary = " ".join(args) if args else "clio: ingest baseline"
    # A commit object under a local ref keeps the tree from `git gc`; refs/clio/* is not pushed by default.
    tree = spec_tree()
    commit_id = c.git_out(["-c", "user.name=clio", "-c", "user.email=clio@localhost",
                           "commit-tree", tree, "-m", summary])
    c.git(["update-ref", "refs/clio/ingest", commit_id])
    when = c.git_out(["log", "-1", "--format=%cd", "--date=format:%Y-%m-%d %H:%M", "refs/clio/ingest"])
    print("Baseline: %s" % c.git_out(["rev-parse", "--short", tree]))
    print("Last ingest: %s — %s" % (when, summary))


def spec_diff(args):
    base = c.git_out(["rev-parse", "-q", "--verify", "refs/clio/ingest^{tree}"])
    if not base:
        print("no ingest baseline in this clone (it is clone-local, never pushed) — reconstruct, see /clio:ingest § 6",
              file=sys.stderr)
        sys.exit(1)
    sys.exit(subprocess.call(["git", "diff"] + args + [base, spec_tree()]))


def spec_grep(args):
    """The decisions still in force that mention a value or a word — what else rests on an old rule. A
    bullet marked `Superseded` is history (and one later `Reinstated` is live again); counting history
    as live is how a change gets weighed against rules that no longer exist."""
    if not args:
        print("usage: clio q spec-grep <regex>", file=sys.stderr)
        sys.exit(1)
    try:
        pat = re.compile(args[0], re.I)
    except re.error as e:
        print("bad regex: %s" % e, file=sys.stderr)
        sys.exit(1)
    live = old = 0
    for f in sorted(glob.glob(SPECS + "/memory/*.md")):
        section = ""
        for n, line in enumerate(tables.read_lines(f), 1):
            if line.startswith("## "):
                section = line
            elif section.startswith("## Decisions") and re.match(r"-\s", line) and pat.search(line):
                if "Superseded" in line and "Reinstated" not in line:
                    old += 1
                else:
                    live += 1
                    print("%s:%d: %s" % (f, n, line[:200]))
    print("# %d live, %d superseded and skipped" % (live, old))


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
        spec_mark(args)
    elif cmd == "spec-diff":
        spec_diff(args)
    elif cmd == "rules":
        rules(args)
    elif cmd == "spec-grep":
        spec_grep(args)
    elif cmd == "plan":
        plan(args)
    elif cmd == "cases":
        cases(args)
    else:
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
