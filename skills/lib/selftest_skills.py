#!/usr/bin/env python3
"""selftest_skills.py — the skills are prose, and nothing runs them but a model. This checks what a script can:
every `clio …` command a skill tells the model to run exists, is covered by that skill's allowed-tools (or is
one of the commands that must raise the user's own yes), every link and ${CLAUDE_PLUGIN_ROOT} path resolves,
no file is orphaned, no 4.x layout term survives, and each SKILL.md has what the loader needs."""
import glob
import os
import re
import sys

ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SKILLS = os.path.join(ROOT, "skills")
bad = 0


def miss(msg):
    global bad
    print(msg)
    bad = 1


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


# --- what exists, read off the code ---------------------------------------------------------------------
def subs(path, var="cmd"):
    return set(re.findall(r'%s == "([a-z][a-z-]*)"' % var, read(os.path.join(ROOT, path))))


Q = subs("skills/context/scripts/q.py")
TEST = subs("skills/test/scripts/clio_test.py") | {"fp"}
VALIDATE = {"index", "debt", "all"}
TOP = {"q": Q, "test": TEST, "validate": VALIDATE, "add": {"plan", "test"}, "selftest": {None}}
# Commands that must raise the permission prompt on purpose: the prompt is the user's own yes.
USER_YES = {("test", "approve"), ("test", "withdraw")}
USER_YES_ARGS = {("test", "migrate"): "--write"}

CMD = re.compile(r"(?:\$\{CLAUDE_PLUGIN_ROOT\}/bin/)?\bclio ((?:q|test|add|validate|selftest))\b(?: ([a-z][a-z0-9-]*))?([^`\n]*)")


def code_text(text):
    """Only what the model is told to run: fenced blocks and inline code."""
    fenced = re.findall(r"```[a-z]*\n(.*?)```", text, re.S)
    inline = re.findall(r"`([^`\n]+)`", re.sub(r"```.*?```", "", text, flags=re.S))
    return "\n".join(fenced + inline)


def allowed(skill_md):
    m = re.search(r"^allowed-tools: (.*)$", read(skill_md), re.M)
    pats = []
    for p in re.findall(r"Bash\((.*?)\)", m.group(1) if m else ""):
        toks = p.replace("${CLAUDE_PLUGIN_ROOT}/bin/", "").split()
        pats.append(toks)
    return pats


def covered(pats, toks):
    for p in pats:
        star = p[-1] == "*"
        head = p[:-1] if star else p
        if toks[:len(head)] == head and (star or len(toks) == len(head)):
            return True
    return False


# --- per skill ---------------------------------------------------------------------------------------------
all_md = sorted(glob.glob(os.path.join(SKILLS, "**", "*.md"), recursive=True))
referenced = set()
for md in all_md:
    text = read(md)
    d = os.path.dirname(md)
    # links to files, and plugin-root paths
    for tgt in re.findall(r"\]\(([^)#]+\.md)\)", text):
        if tgt.startswith("memory/") or os.path.basename(md) == "requirements.md":
            continue                      # sample rows of a project's requirements.md, not links
        p = os.path.normpath(os.path.join(d, tgt))
        referenced.add(p)
        if not os.path.isfile(p):
            miss("%s: link to %s does not exist" % (os.path.relpath(md, ROOT), tgt))
    for tgt in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)", text):
        tgt = tgt.rstrip(".,;:)")
        p = os.path.join(ROOT, tgt)
        referenced.add(p)
        if not os.path.exists(p):
            miss("%s: ${CLAUDE_PLUGIN_ROOT}/%s does not exist" % (os.path.relpath(md, ROOT), tgt))
    for tgt in re.findall(r"`((?:cases|steps)/[A-Z-]+\.md|[A-Z][A-Z-]+\.md)`", text):
        referenced.add(os.path.normpath(os.path.join(d, tgt)))
    for tgt in re.findall(r"(?<![\w/])((?:cases|steps)/[A-Z-]+\.md)", text):
        referenced.add(os.path.normpath(os.path.join(d, tgt)))

for skill_md in sorted(glob.glob(os.path.join(SKILLS, "*", "SKILL.md"))):
    skill = os.path.basename(os.path.dirname(skill_md))
    head = read(skill_md).split("---")[1] if read(skill_md).startswith("---") else ""
    for key in ("name", "description", "argument-hint", "allowed-tools"):
        if key == "argument-hint" and skill in ("setup",):
            continue
        if not re.search(r"^%s:" % key, head, re.M):
            miss("%s: frontmatter has no %s" % (skill, key))
    desc = re.search(r"^description:\s*(.*?)(?=^[a-z-]+:|\Z)", head, re.M | re.S)
    if desc and len(" ".join(desc.group(1).split())) > 700:
        miss("%s: description is %d characters — it loads every session, keep it under 700" % (skill, len(" ".join(desc.group(1).split()))))
    pats = allowed(skill_md)
    files = [skill_md] + sorted(glob.glob(os.path.join(os.path.dirname(skill_md), "**", "*.md"), recursive=True))
    for f in dict.fromkeys(files):
        for m in CMD.finditer(code_text(read(f))):
            top, sub, rest = m.group(1), m.group(2), m.group(3)
            if top == "selftest":
                continue
            where = "%s: `clio %s%s`" % (os.path.relpath(f, ROOT), top, " " + sub if sub else "")
            if sub is not None and sub not in TOP[top]:
                if top == "add" or sub in ("a", "an", "the", "is", "of", "to", "and", "or", "in", "on", "it", "for", "its"):
                    continue
                miss("%s names a subcommand that does not exist" % where)
                continue
            words = rest.split()
            key = (top, sub)
            full = ["clio", top] + ([sub] if sub else []) + words
            if key in USER_YES or (key in USER_YES_ARGS and USER_YES_ARGS[key] in words):
                if covered(pats, full):
                    miss("%s is the user's own yes but the allowed-tools of %s lets it run unasked" % (where, skill))
                continue
            if sub is None:
                continue                  # the tool named in prose ("`clio q` reads …"), not a command to run
            if not covered(pats, ["clio", top, sub] + ["x"]) and not covered(pats, ["clio", top, sub]):
                miss("%s is not covered by the allowed-tools of the %s skill" % (where, skill))

# --- no orphan, no stale layout -------------------------------------------------------------------------
for md in all_md:
    if os.path.basename(md) == "SKILL.md" or os.path.normpath(md) in {os.path.normpath(x) for x in referenced}:
        continue
    if md.endswith(os.path.join("setup", "templates", "requirements.md")):
        continue
    miss("%s is referenced from no skill file" % os.path.relpath(md, ROOT))

STALE = [r"docs/plans/", r"docs/tests/", r"## Re-planned", r"Not applicable:\s*$", r"plans/infra\.md", r"\bMutation: ", r"\bDone cell\b", r"\bLevels cell\b"]
EXCUSED = {"MIGRATE.md", "CHANGE.md"}     # they explain the 4.x layout on purpose
for md in all_md + [os.path.join(ROOT, "README.md")]:
    if os.path.basename(md) in EXCUSED:
        continue
    text = read(md)
    for pat in STALE:
        for m in re.finditer(pat, text, re.M):
            line = text.count("\n", 0, m.start()) + 1
            miss("%s:%d still names the 4.x layout (%s)" % (os.path.relpath(md, ROOT), line, pat.strip()))

if bad == 0:
    print("OK")
sys.exit(bad)
