#!/usr/bin/env python3
"""clio doc — create or update a sub-task doc under .claude/clio/docs/tasks/<feature>/ from one JSON object on
stdin, applying the rules of /clio:memo's WRITE-DOC step so the model does not: a doc is only ever appended to
(Follow-up is the one section that is replaced), Updated is today, Commit and Plan tasks accumulate, the Change
Log gets its line, a section can be relabelled [SUPERSEDED …]. One call replaces the Read of the whole doc and
the Edit of each section. Python 3.9+, standard library only.

  new doc:       {"feature":"ui","name":"panel-width","plan_tasks":["3.5.7"],"summary":"…","files":["path — reason"],
                  "decisions":["…"],"side_effects":["…"],"testing":["OK: task 3.5.7 …"],"related":["…"],
                  "follow_up":["…"],"changelog":"initial","commit":"abc1234","id":"<ts, default now>","light":false}
  existing doc:  {"doc":".claude/clio/docs/tasks/ui/1789430400_panel-width.md", …the same keys, all optional…}
  also:          "summary_replace":true  →  an existing doc's Summary is replaced (otherwise it is kept, with a note)
                 "relabel":["Summary","Decisions"]  →  ## [SUPERSEDED date] Summary — REVERTED, DO NOT RE-IMPLEMENT
                 "feature_what":"…"  →  creates the feature's summary.md when it has none (with "domain", "plan", "spec")
Prints `doc: <path>` and `id: <id>` — the id and path the index record needs."""
import datetime
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from cliolib import common as c  # noqa: E402

TASKS = ".claude/clio/docs/tasks"
ORDER = ["Summary", "Files Changed", "Decisions", "Side Effects", "Testing Done", "Related", "Follow-up", "Change Log"]
KEYS = {"doc", "feature", "name", "id", "plan_tasks", "commit", "summary", "files", "decisions", "side_effects", "testing", "related",
        "follow_up", "changelog", "relabel", "light", "feature_what", "domain", "plan", "spec", "summary_replace"}
SECTION_KEY = {"Files Changed": "files", "Decisions": "decisions", "Side Effects": "side_effects", "Testing Done": "testing", "Related": "related"}
DATED = ("Side Effects", "Testing Done", "Related")      # appended to an existing doc with the date in front
LABEL = re.compile(r"^## (?:\[SUPERSEDED [^\]]*\] )?(.*?)(?: — REVERTED, DO NOT RE-IMPLEMENT)?$")


def today():
    return datetime.date.today().strftime("%Y-%m-%d")


def parse(text):
    """(header lines, [[name, heading line, body lines]]) — unknown sections are kept in place."""
    header, secs = [], []
    for line in text.split("\n"):
        if line.startswith("## "):
            m = LABEL.match(line)
            secs.append([m.group(1) if m else line[3:], line, []])
        elif secs:
            secs[-1][2].append(line)
        else:
            header.append(line)
    for s in secs:
        while s[2] and s[2][-1].strip() == "":
            s[2].pop()
    return header, secs


def render(header, secs):
    out = list(header)
    while out and out[-1].strip() == "":
        out.pop()
    for _, heading, body in secs:
        out += ["", heading] + [b for b in body]
    return "\n".join(out) + "\n"


def bullet(t):
    t = t.strip()
    return t if t.startswith("- ") else "- " + t


def find(secs, name):
    return next((s for s in secs if s[0] == name), None)


def section(secs, name):
    """The section, created in its place in ORDER when the doc has none."""
    s = find(secs, name)
    if s is None:
        s = [name, "## " + name, []]
        later = [i for i, x in enumerate(secs) if x[0] in ORDER and ORDER.index(x[0]) > ORDER.index(name)]
        secs.insert(later[0] if later else len(secs), s)
    return s


def files_bullet(item):
    """'path — reason' or ['path','reason'] → (path, reason)."""
    if isinstance(item, (list, tuple)):
        return item[0], item[1] if len(item) > 1 else ""
    m = re.match(r"`?([^`—]+?)`?\s+—\s+(.*)$", item.strip())
    return (m.group(1).strip(), m.group(2).strip()) if m else (item.strip().strip("`"), "")


def merge_files(sec, items, new):
    body = sec[2]
    for item in items:
        path, why = files_bullet(item)
        hit = next((i for i, l in enumerate(body) if "`%s`" % path in l.split(" — ")[0]), None)
        if hit is None:
            body.append("- `%s`%s" % (path, " — " + why if why else ""))
        elif why and why not in body[hit]:
            body[hit] = body[hit].rstrip() + "; %s (%s)" % (why, today())


def apply(header, secs, req, new):
    t = today()
    # the header: Updated is today, Commit and Plan tasks accumulate
    def setline(prefix, fn):
        for i, l in enumerate(header):
            if l.startswith(prefix):
                header[i] = prefix + fn(l[len(prefix):].strip())
                return
        header.append(prefix + fn(""))
    setline("Updated: ", lambda v: t)
    if req.get("commit"):
        setline("Commit: ", lambda v: v if req["commit"] in v else (v + ", " if v else "") + req["commit"])
    if req.get("plan_tasks"):
        def union(v):
            have = [x.strip() for x in v.split(",") if x.strip() and x.strip().lower() != "none"]
            return ", ".join(have + [x for x in req["plan_tasks"] if x not in have])
        setline("Plan tasks: ", union)
    # the sections
    notes = []
    if "summary" in req:
        sec = section(secs, "Summary")
        if new or req.get("summary_replace") or not [b for b in sec[2] if b.strip()]:
            sec[2][:] = [req["summary"]]
        else:
            notes.append("summary kept: the doc has one; pass \"summary_replace\": true to replace it")
    for name, key in SECTION_KEY.items():
        items = req.get(key)
        if not items:
            continue
        sec = section(secs, name)
        if name == "Files Changed":
            merge_files(sec, items, new)
            continue
        for it in items:
            line = bullet(it)
            if name == "Testing Done" or (name in DATED and not new):
                if not re.match(r"- \d{4}-\d{2}-\d{2}", line):
                    line = "- %s — %s" % (t, line[2:])
            sec[2].append(line)
    if "follow_up" in req:
        sec = section(secs, "Follow-up")
        sec[2][:] = [bullet(x) for x in req["follow_up"]] or ["- none"]
    elif new and not req.get("light"):
        section(secs, "Follow-up")[2][:] = ["- none"]
    if new:      # no empty heading in a new doc: say there is nothing, or that nothing was verified
        for sec in secs:
            if sec[0] in ORDER and not any(x.strip() for x in sec[2]):
                sec[2][:] = ["- unverified: no gate has run for it yet" if sec[0] == "Testing Done" else "- none"] if sec[0] not in ("Summary", "Change Log") else sec[2]
    for name in req.get("relabel") or []:
        sec = find(secs, name)
        if sec is None:
            raise ValueError("relabel: the doc has no section %r" % name)
        if "[SUPERSEDED" not in sec[1]:
            sec[1] = "## [SUPERSEDED %s] %s — REVERTED, DO NOT RE-IMPLEMENT" % (t, name)
    if req.get("changelog"):
        line = "- %s — %s%s" % (t, req["changelog"], " (commit %s)" % req["commit"] if req.get("commit") else "")
        section(secs, "Change Log")[2].append(line)
    elif new:
        section(secs, "Change Log")[2].append("- %s — initial%s" % (t, " (commit %s)" % req["commit"] if req.get("commit") else ""))
    return notes


def new_doc(req):
    feature, name = req.get("feature"), req.get("name")
    if not (isinstance(feature, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]*", feature)):
        raise ValueError("feature must be kebab-case (the business area, not a source directory)")
    if not (isinstance(name, str) and re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+){0,3}", name)):
        raise ValueError("name must be 1–4 lowercase words joined by hyphens")
    ident = str(req.get("id") or int(time.time()))
    path = "%s/%s/%s_%s.md" % (TASKS, feature, ident, name)
    if os.path.exists(path):
        raise ValueError("%s exists — pass \"doc\" to update it" % path)
    title = " ".join(w.capitalize() for w in name.split("-"))
    t = today()
    header = ["# " + title, "Date: " + t, "Updated: " + t, "Commit: ", "Plan tasks: none", ""]
    secs = [[n, "## " + n, []] for n in (["Summary", "Change Log"] if req.get("light") else ORDER)]
    return path, ident, header, secs


def main(argv):
    root = c.find_root()
    if not root:
        print("FAIL: no .claude/clio above %s — run /clio:setup" % os.getcwd())
        return 1
    os.chdir(root)
    try:
        req = c.loads(sys.stdin.read())
    except ValueError as e:
        print("FAIL: stdin is not valid JSON (%s)" % e)
        return 1
    if not isinstance(req, dict) or set(req) - KEYS:
        print("FAIL: one JSON object with only these keys: %s" % ", ".join(sorted(KEYS)))
        return 1
    try:
        if req.get("doc"):
            path = req["doc"]
            if not os.path.isfile(path):
                raise ValueError("%s does not exist — a new doc takes feature and name, and is never created at a guessed path" % path)
            m = re.match(r"(\d+)_", os.path.basename(path))
            ident = m.group(1) if m else ""
            header, secs = parse(open(path, encoding="utf-8").read())
            new = False
        else:
            path, ident, header, secs = new_doc(req)
            new = True
        notes = apply(header, secs, req, new)
        feature_dir = os.path.dirname(path)
        os.makedirs(feature_dir, exist_ok=True)
        if req.get("feature_what") and not os.path.isfile(feature_dir + "/summary.md"):
            with open(feature_dir + "/summary.md", "w", encoding="utf-8") as f:
                f.write("# %s\nDomain: %s · Plan: `clio q plan %s` · Spec: `%s`\n\n## What this is\n%s\n\n## Cross-cutting side effects\n\n"
                        "## General Memory\n" % (os.path.basename(feature_dir).replace("-", " ").title(), req.get("domain", ""),
                                                 req.get("plan", os.path.basename(feature_dir)), req.get("spec", "memory/%s.md" % os.path.basename(feature_dir)),
                                                 req["feature_what"]))
        with open(path, "w", encoding="utf-8") as f:
            f.write(render(header, secs))
    except (ValueError, OSError) as e:
        print("FAIL: %s" % e)
        return 1
    print("doc: %s" % path)
    print("id: %s" % ident)
    print("%s" % ("created" if new else "updated"))
    for n in notes:
        print("note: " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
