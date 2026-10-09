#!/usr/bin/env python3
USAGE = """# clio q — every read of Clio's ledgers, in one place. Read-only.
#   context [target...]                       /clio:context in one call: rows, spec, built docs, debt, rules, plan, what looks wrong
#                                              (target: area · row · task id · debt id · file · word; none = summary)
#   levels [choosing | level...]              LEVELS.md sections: the questions + tier, or what each named level must cover
#   gather [target]                           /clio:memo step 1 in one call: changed, unrecorded, the doc that owns the target
#                                              (Case A–D), its rows and plan tasks, commit, keywords, rules
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
    cased = store.case_tasks()
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
        print("no ingest baseline in this clone (it is clone-local, never pushed) — reconstruct, see skills/ingest/cases/CHANGE.md § 1",
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


def levels(args):
    """Sections of skills/test/LEVELS.md, so nobody reads the whole catalog (13 KB): `choosing` (the questions
    and the tier), or level names (`unit api security`) for what each must cover. No argument lists the names."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "test", "LEVELS.md")
    text = tables.read_lines(path)
    secs, cur = {}, None
    for line in text:
        m = re.match(r"## (.*)$", line)
        if m:
            cur = m.group(1).strip().lower()
            secs[cur] = [line]
        elif cur:
            secs[cur].append(line)
    secs["choosing"] = secs.get("choosing", []) + secs.get("tier", [])
    head = [l for l in text[:text.index(next(l for l in text if l.startswith("## ")))] if l.strip()]
    if not args:
        print("sections: " + " ".join(k for k in secs if k != "tier"))
        return
    for a in args:
        k = a.lower()
        if k not in secs:
            print("no section %r — sections: %s" % (a, " ".join(secs)), file=sys.stderr)
            sys.exit(1)
    if "choosing" not in [a.lower() for a in args]:
        print("(ids `level.n` are the risks a task's cases must cover or excuse; a bullet without an id is a constraint on every case)")
    for a in args:
        print("\n".join(l for l in secs[a.lower()]).rstrip())
        print()


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


def rules_for(files):
    """[(rule file, why)] — the .claude/rules/*.md that bind these files; a rule with no `paths:` loads
    every session and is reported as such."""
    # ponytail: `**` matches like `*` (crossing `/`). Good enough to name candidates; Claude Code's
    # own matcher is what actually loads them.
    out = []
    for rf in sorted(glob.glob(".claude/rules/**/*.md", recursive=True)):
        globs = rule_globs(rf)
        if not globs:
            out.append((rf, "(no paths: — loads every session)"))
            continue
        hit = next(((f, g) for f in files for g in globs if fnmatch.fnmatchcase(f, g)), None)
        if hit:
            out.append((rf, "← %s matches %s" % (hit[0], hit[1])))
    return out


def rules(args):
    if not args:
        print("usage: clio q rules <file>...", file=sys.stderr)
        sys.exit(1)
    for rf, why in rules_for(args):
        print("%s  %s" % (rf, why))


# --- context: hops 1–5 of /clio:context in one call --------------------------------------------------------
NUM = re.compile(r"[0-9]+(\.[0-9]+)*")


def domains():
    """The `Domains:` vocabulary of requirements.md: the only values a ledger record's `domain` may hold."""
    path = SPECS + "/requirements.md"
    if not os.path.isfile(path):
        return []
    lines = tables.read_lines(path)
    for i, line in enumerate(lines):
        if line.lstrip("*_ ").lower().startswith("domains"):
            para = []
            for l in lines[i:]:
                if not l.strip():
                    break
                para.append(l)
            return re.findall(r"`([^`]+)`", " ".join(para)[len(line):] if len(para) > 1 else line)
    return []


_GENERIC = {"internal", "src", "app", "lib", "pkg", "cmd", "test", "tests", "main", "index", "util", "utils", "common", "the", "and"}


def work_words(target, files):
    """Words that stand for this work: the target's, else the stems of the changed files (a path gives `volume`
    for `internal/player/volume.go`), minus the directory names every repo has."""
    src = [target] if target and not NUM.fullmatch(target) else []
    if not src:
        src = [os.path.splitext(f)[0] for f in files if not f.startswith(".claude/")]
    out, seen = [], {}
    for chunk in src:
        for w in {w.lower() for w in re.split(r"[\s/_.-]+", chunk)}:
            if len(w) > 2 and not NUM.fullmatch(w) and w not in _GENERIC:
                seen[w] = seen.get(w, 0) + 1
    # a word the changed files share (`volume` in four file names) is the work's topic; the rest is noise
    shared = [w for w, n in seen.items() if n > 1] if not target else []
    return sorted(shared or seen)


def best_rows(rows, words):
    """The rows the words point at: each word weighs 1 / (rows it appears in), so `volume` outweighs `player`;
    only rows scoring at least half of the best stay."""
    text = [(r, (r[1] + " " + r[2]).lower()) for r in rows]
    weight = {w: 1.0 / max(1, sum(w in t for _, t in text)) for w in words}
    scored = [(sum(weight[w] for w in words if w in t), r) for r, t in text]
    top = max([sc for sc, _ in scored] or [0])
    return [r for sc, r in scored if sc and sc >= top / 2]


def req_table():
    """[(num, task, spec stem, spec path, status)] — the rows of requirements.md — and its keyword table
    {word: spec stem}."""
    path = SPECS + "/requirements.md"
    rows, kw, in_kw = [], {}, False
    if not os.path.isfile(path):
        return rows, kw
    for line in tables.live(tables.read_lines(path)):
        if line.startswith("## "):
            in_kw = "keyword" in line.lower()
            continue
        if not line.lstrip().startswith("|"):
            continue
        cell = tables._cells(line)
        if in_kw:
            m = re.search(r"([A-Za-z0-9_-]+)\.md", tables._f(cell, 3))
            if m:
                for w in re.split(r"[/,]", tables._f(cell, 2)):
                    if w.strip():
                        kw[w.strip().lower()] = m.group(1)
        elif NUM.fullmatch(tables._f(cell, 2)):
            m = re.search(r"\(([^)]+\.md)\)", tables._f(cell, 4))
            sp = m.group(1) if m else ""
            rows.append((tables._f(cell, 2), tables._f(cell, 3), os.path.basename(sp)[:-3], sp, tables._f(cell, 5)))
    return rows, kw


def doc_sections(path, names=("Decisions", "Side Effects", "Follow-up"), cap=8):
    """{section: its non-empty lines, cut to cap} of a task doc — the load-bearing part (HOP2.md). A section
    relabelled `[SUPERSEDED …]` is history: one warning line instead of its body, so nobody reads reverted
    work as the pattern to follow."""
    out, cur = {}, None
    if not os.path.isfile(path):
        return out
    for line in tables.read_lines(path):
        if line.startswith("## "):
            m = re.match(r"## (\[SUPERSEDED[^\]]*\]) (.*?)(?: — REVERTED.*)?$", line)
            if m and m.group(2) in names:
                out[m.group(2)] = ["%s — do not follow, the code is gone" % m.group(1)]
                cur = None
                continue
            m = re.match(r"## (.*)$", line)
            cur = m.group(1) if m and m.group(1) in names else None
            if cur:
                out.setdefault(cur, [])
        elif cur and line.strip():
            out[cur].append(line)
    return {k: (v[:cap] + ["  … %d more line(s) in the doc" % (len(v) - cap)] if len(v) > cap else v) for k, v in out.items()}


def context(args):
    """Everything /clio:context loads for a target, in one report: the requirement rows and their spec
    files, what was built (the last docs' load-bearing sections), what is owed, the rules that bind the
    files, the plan, and what looks wrong. A target is an area, a requirement row, a task id, a debt id, a
    file or a word; several are merged. No target is the overview."""
    if not args:
        summary()
        return
    rows, kw = req_table()
    plan = {r[1]: r for r in store.plan_rows()}
    areas_all = {store.area_of(p) for p in store.files("plan")}
    debt_all = {}
    for r in c.read_valid(DEBT):
        if isinstance(r, dict):
            debt_all[c.tostring(r.get("id"))] = r
    nums, stems, areas, files, words, tasks_t = set(), set(), set(), set(), set(), set()
    for t in args:
        if t in debt_all:
            d = debt_all[t]
            nums |= {c.tostring(x) for x in c.items(d.get("req"))}
            stems |= {os.path.basename(c.tostring(x))[:-3] for x in c.items(d.get("specs"))}
        elif t in plan:
            tasks_t.add(t)
            nums |= {x.strip() for x in plan[t][3].split(",") if NUM.fullmatch(x.strip())}
            areas.add(store.area_of(plan[t][0]))
        elif NUM.fullmatch(t) and any(r[0] == t or r[0].startswith(t + ".") for r in rows):
            nums.add(t)
        elif t in areas_all or any(r[2] == t for r in rows):
            (areas if t in areas_all else stems).add(t)
            if t in areas_all:
                stems.add(t)
        elif "/" in t or os.path.exists(t):
            files.add(t)
        else:
            words.add(t.lower())
            if t.lower() in kw:
                stems.add(kw[t.lower()])
    sel = [r for r in rows if r[0] in nums or any(r[0].startswith(n + ".") for n in nums) or r[2] in stems
           or any(w in (r[1] + " " + r[2]).lower() for w in words)]
    nums |= {r[0] for r in sel}
    print("context: %s" % " ".join(args))

    # hop 1 — the requirement and its spec files
    print("\nrequirement rows (%d)%s:" % (len(sel), "" if len(sel) <= 12 else ", first 12"))
    for num, task, stem, sp, status in sel[:12]:
        print("  %-6s %s → %s\n         %s" % (num, task[:90], sp or "?", status[:230]))
    if not sel:
        print("  none matches — outside the contracted scope, or requirements.md lacks a row (not a reason to stop)")
    for stem in sorted({r[2] for r in sel if r[2]}):
        path = "%s/memory/%s.md" % (SPECS, stem)
        if not os.path.isfile(path):
            continue
        sec, n_dec, opens = "", 0, []
        for line in tables.read_lines(path):
            if line.startswith("## "):
                sec = line
            elif sec.startswith("## Decisions") and re.match(r"-\s", line):
                n_dec += 1
            elif sec.startswith("## Open") and line.startswith("- ") and "None" not in line[:8]:
                opens.append(line)
        print("  spec %s: %d decisions, %d open ⚠️  (read it whole when a decision matters)" % (path, n_dec, len(opens)))
        for o in opens:
            print("     " + o[:300])

    # hop 2 — what was built
    idx = c.read_valid(IDX)
    ptasks = tasks_t | {r[1] for r in plan.values() if set(x.strip() for x in r[3].split(",")) & nums or store.area_of(r[0]) in areas}

    def mine(r):
        return (r.get("type") != "chore" and (
            {c.tostring(x) for x in c.items(r.get("req"))} & nums
            or {os.path.basename(c.tostring(x))[:-3] for x in c.items(r.get("specs"))} & stems
            or r.get("domain") in areas
            or any(any(f == c.tostring(x) or f in c.tostring(x) for x in c.items(r.get("files"))) for f in files)
            or any(any(w in c.tostring(x).lower() for x in c.items(r.get("keywords"))) for w in words)
            or {c.tostring(x) for x in c.items(r.get("plan_tasks"))} & tasks_t))
    built = [r for r in docs(idx) if mine(r)]
    built.sort(key=lambda r: (c.tostring(r.get("date")), c.tostring(r.get("id"))), reverse=True)
    print("\nbuilt (%d doc(s); newest first):" % len(built))
    for r in built[:3]:
        print("  %s  %s  tasks %s" % (c.tostring(r.get("date")), r.get("doc"), ",".join(c.tostring(x) for x in c.items(r.get("plan_tasks"))[:8]) or "–"))
        for name, lines in doc_sections(c.tostring(r.get("doc"))).items():
            print("     [%s]" % name)
            for l in lines:
                print("       " + l[:240])
    for r in built[3:12]:
        print("  %s  %s  tasks %s" % (c.tostring(r.get("date")), r.get("doc"), ",".join(c.tostring(x) for x in c.items(r.get("plan_tasks"))[:6]) or "–"))
    if len(built) > 12:
        print("  … and %d older" % (len(built) - 12))
    for stem in sorted(stems | areas):
        for sm in glob.glob(".claude/clio/docs/tasks/*/summary.md"):
            if os.path.basename(os.path.dirname(sm)) == stem:
                gm = doc_sections(sm, names=("General Memory", "Cross-cutting side effects"))
                for name, lines in gm.items():
                    print("  feature %s [%s]" % (stem, name))
                    for l in lines:
                        print("       " + l[:240])

    # hop 3 — what is owed
    open_debt = []
    for g in c.group_by([r for r in c.read_valid(DEBT) if isinstance(r, dict)], lambda r: r.get("id")):
        d = g[-1]
        if d.get("status") == "done":
            continue
        blob = (c.tostring(d.get("what")) + " " + c.tostring(d.get("id"))).lower()
        if ({c.tostring(x) for x in c.items(d.get("req"))} & nums or d.get("domain") in areas
                or {os.path.basename(c.tostring(x))[:-3] for x in c.items(d.get("specs"))} & stems
                or c.tostring(d.get("id")) in args or any(w in blob for w in words)):
            open_debt.append(d)
    open_debt.sort(key=lambda d: d.get("blocked_by") is not None)
    print("\nowed (%d open; actionable first):" % len(open_debt))
    for d in open_debt:
        bb = d.get("blocked_by")
        print("  %-28s %-12s %-10s %s" % (c.tostring(d.get("id")), d.get("kind"), d.get("status"),
                                          ("BLOCKED by " + c.tostring(bb)[:90]) if bb is not None else "actionable now"))
        print("      " + c.tostring((c.items(d.get("what")) or [""])[0])[:200])

    # hop 4 — the rules that bind the files this work will touch
    touch = set(files)
    for tid in ptasks:
        if tid in plan and plan[tid][6].startswith("[ ]"):
            rec = store.tasks().get(tid, {})
            touch |= {c.tostring(x) for x in c.items(rec.get("touches")) if "/" in c.tostring(x) and not c.tostring(x).endswith("/")}
    for r in built[:3]:
        touch |= {c.tostring(x) for x in c.items(r.get("files"))[:8]}
    rl = rules_for(sorted(touch)) if touch else []
    print("\nrules (%d file(s) considered):" % len(touch))
    for rf, why in rl:
        print("  %s  %s" % (rf, why))
    if not rl:
        print("  none")

    # hop 5 — the plan
    mine_t = sorted((plan[t] for t in ptasks if t in plan), key=lambda r: [int(x) if x.isdigit() else 0 for x in re.split(r"[.]", r[1])])
    opn = [r for r in mine_t if r[6].startswith("[ ]")]
    done_ids = {r[1] for r in plan.values() if r[6].startswith("[x]")}
    cased = store.case_tasks()
    dropped = sum(r[6].startswith(("superseded", "void", "withdrawn")) for r in mine_t)
    print("\nplan: %d task(s), %d done, %d open%s" % (len(mine_t), sum(r[6].startswith("[x]") for r in mine_t), len(opn),
                                                  ", %d superseded/void (history, not work)" % dropped if dropped else ""))
    for r in opn[:10]:
        waits = [n for n in re.split(r"[ ,]+", r[5]) if n[:1].isdigit() and n not in done_ids]
        print("  %-8s %-26s %s%s" % (r[1], r[4][:26], "ready" if not waits else "waits on " + ", ".join(waits),
                                      "" if r[1] in cased else " · no cases yet"))
        print("           " + r[2][:150])

    # what looks wrong — reported, never fixed (/clio:memo and /clio:ingest write the corrections)
    print("\nlooks wrong:")
    bad = []
    for num, task, stem, sp, status in sel:
        if ("⚠" in status or "❌" in status) and not any({c.tostring(x) for x in c.items(d.get("req"))} & {num} for d in open_debt):
            bad.append("row %s is ⚠️/❌ and no open debt record tracks it" % num)
        if "✅" in status and not any(num in {c.tostring(x) for x in c.items(r.get("req"))} for r in idx if isinstance(r, dict)):
            bad.append("row %s is ✅ (decided) and nothing was recorded as built: nothing implements it yet, or a memo is missing" % num)
    ok_rows = {r[0] for r in rows if "✅" in r[4] and "⚠" not in r[4].split(";")[0] and "❌" not in r[4].split(";")[0]}
    for d in open_debt:
        rq = {c.tostring(x) for x in c.items(d.get("req"))}
        if d.get("blocked_by") is not None and rq and rq <= ok_rows and d.get("kind") == "spec-blocked":
            bad.append("debt %s waits on %s but its row(s) %s read ✅ now: unblock or close it" % (d.get("id"), c.tostring(d.get("blocked_by"))[:60], ",".join(sorted(rq))))
    print("\n".join("  - " + b for b in bad) if bad else "  nothing found")
    for cmd, why in suggest(store.plan_rows()):
        print("suggest: %s — %s" % (cmd, why))


def gather(args):
    """Step 1 of /clio:memo in one report: what changed, what is unrecorded, which doc owns the target
    (Case A–D of RESOLVE-AND-GATHER.md, computed), the requirement rows and plan tasks it serves, the
    commit of the files, the keyword vocabulary and the rules that bind the files."""
    import datetime
    idx = c.read_valid(IDX)
    last = [r for r in docs(idx) if r.get("type") != "chore"]
    print("gather: %s" % (" ".join(args) or "(no target)"))
    print("today: %s" % datetime.date.today().strftime("%Y-%m-%d"))
    files, same = work_changes() if c.is_git() else ([], False)
    print("\nchanged (%d)%s:" % (len(files), " — UNCHANGED since the last memo: nothing new to record" if same else ""))
    for f in files[:40]:
        print("  " + f)
    if len(files) > 40:
        print("  … and %d more" % (len(files) - 40))
    pend = c.unrecorded_commits(idx) if c.is_git() else []
    o = parse([])
    print("\nunrecorded commits (%d):" % len(pend))
    docless = []
    for h, fl in pend:
        found = set()
        for f in fl:
            o["f"] = f
            found.update(c.tostring(r.get("doc")) for r in last if built_match(o, r))
        if not found:
            docless.append(h)
        print("  %s  docs: %s" % (h, ",".join(sorted(found)) or "- (nobody recorded it)"))
    target = args[0] if args else ""
    case, cand = "", []
    if target and ("/" in target or target.endswith(".md")):
        case = "A — path target: " + ("EXISTS → UPDATE" if os.path.isfile(target) else "MISSING → stop and ask, do not create it")
    elif target and NUM.fullmatch(target):
        o = parse([])
        o["t"] = target
        cand = [r for r in last if built_match(o, r)]
        parent = target.rsplit(".", 1)[0] if "." in target else ""
        if not cand and parent and NUM.fullmatch(parent):
            o["t"] = parent
            cand = [r for r in last if built_match(o, r)]
            case = "B — task %s: no doc of its own; a sub-task of %s → UPDATE the parent's doc" % (target, parent) if cand else ""
        elif cand:
            case = "B — task %s: a doc owns it → UPDATE" % target
        if not case:
            case = "B — task %s: %s" % (target, "no doc → CREATE" if target in {r[1] for r in store.plan_rows()} else "in no plan → stop and ask, do not invent an id")
    elif target:
        ws = work_words(target, [])
        cand = [r for r in last if any(any(w == c.tostring(k).lower() for k in c.items(r.get("keywords"))) for w in ws)]
        case = ("C — word target: %d doc(s) carry the keyword → ONE, same sub-task → UPDATE, several → ask, none → CREATE" % len(cand)
                if cand else "C — word target: no doc carries the keyword → CREATE")
    elif not target and files and not same:
        for f in files:
            o = parse([])
            o["f"] = f
            for r in last:
                if built_match(o, r) and r not in cand:
                    cand.append(r)
        case = ("C — no target: %d doc(s) already cover changed files → ONE → UPDATE, several → ask, none → CREATE" % len(cand)) if cand else "C — no target and no doc covers the files → CREATE"
    elif not target and not files and pend:
        case = ("D — nothing uncommitted and every unrecorded commit names its docs: backfill them (hash only)" if not docless else
                "C — nothing uncommitted, but commit(s) %s are recorded nowhere: their files go to Case C (or a chore, if the user says no task owns them)" % ", ".join(docless))
    elif not target and not files and not pend:
        case = "nothing to record — stop, unless the user names work outside git"
    print("\ncase: %s" % (case or "—"))
    for r in cand[:8]:
        print("  %s  %s  tasks %s  commits %s" % (r.get("id"), r.get("doc"), ",".join(c.tostring(x) for x in c.items(r.get("plan_tasks"))[:8]) or "–",
                                                 ",".join(c.tostring(x) for x in c.items(r.get("commits"))) or "–"))

    rows, _ = req_table()
    words = work_words(target, files)
    near = best_rows(rows, words)
    print("\nrequirement rows that may be this work's (%s):" % (", ".join(words) or "no word to match"))
    for num, task, stem, sp, status in near[:8]:
        print("  %-6s %s → %s  %s" % (num, task[:70], sp, status[:60]))
    plan_rows = store.plan_rows()
    reqs = {r[0] for r in near} | ({target} if NUM.fullmatch(target or "") else set())
    mine = [r for r in plan_rows if {x.strip() for x in r[3].split(",")} & reqs or r[1] == target]
    print("plan tasks for those rows (%d):" % len(mine))
    for r in mine[:12]:
        print("  %-8s %-22s %-18s %s" % (r[1], r[4][:22], r[6][:18], r[2][:70]))
    if files:
        h = c.git_out(["log", "-1", "--format=%h", "--"] + files) if not c.git(["status", "--porcelain", "--"] + files).stdout.strip() else ""
        print("\ncommit holding these files: %s" % (h or "none (uncommitted, or a repo with no commit): write no hash"))
        rl = rules_for(files)
        print("rules binding them: %s" % ("; ".join("%s %s" % x for x in rl) or "none"))
    if words:
        hits = []
        for g in c.group_by([r for r in c.read_valid(DEBT) if isinstance(r, dict)], lambda r: r.get("id")):
            d = g[-1]
            blob = (c.tostring(d.get("what")) + " " + c.tostring(d.get("id"))).lower()
            if d.get("status") != "done" and any(w in blob for w in words):
                hits.append(d)
        print("\nopen debt that mentions %s (%d):" % (", ".join(words[:6]), len(hits)))
        for d in hits[:6]:
            bb = d.get("blocked_by")
            print("  %-28s %-12s %s" % (c.tostring(d.get("id")), d.get("kind"), ("BLOCKED by " + c.tostring(bb)[:60]) if bb is not None else "actionable now"))
    print("\ndomains (a record's `domain` is one of these; a new one → ask): %s" % (", ".join(domains()) or "none declared"))
    counts = {}
    for r in last:
        for k in c.items(r.get("keywords")):
            counts[c.tostring(k)] = counts.get(c.tostring(k), 0) + 1
    print("\nkeyword vocabulary (reuse these exact words): %s" % ", ".join(k for k, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:30]))
    feats = sorted(glob.glob(".claude/clio/docs/tasks/*/"), key=lambda d: os.path.getmtime(d), reverse=True)
    print("feature directories (newest first): %s" % ", ".join(os.path.basename(d.rstrip("/")) for d in feats))
    for cmd, why in suggest(plan_rows)[:2]:
        print("suggest: %s — %s" % (cmd, why))


def main(argv):
    c.quiet_on_closed_pipe()
    cmd = argv[0] if argv else ""
    if cmd == "levels":                   # the plugin's own catalog: needs no project
        levels(argv[1:])
        return
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
    elif cmd == "context":
        context(args)
    elif cmd == "gather":
        gather(args)
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
