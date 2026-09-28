"""Batch templates and the JUnit XML they leave: which cases one runner start can take, and what the
report says about each. Text in, tuples out — nothing here runs a test or writes evidence.

A runner that boots something heavy (Maven + JVM + Spring: ~7 s) pays it once per case when every
case is its own command. A `Batch:` line in .claude/rules/*.md (test/SKILL.md § 1b finds and writes
it) names the one command that runs many tests and the JUnit XML it leaves behind:
  Batch: `mvn -pl api test -Dtest={tests}` · join: `,` · report: `api/target/surefire-reports/TEST-*.xml`
A case joins a batch only if its own command IS that template with {tests} = its test id, so the
batch runs exactly the cases' commands, merged.
selftest: skills/lib/selftest_junit.py — golden output per runner's report shape.
"""
import glob
import re

from . import tables

_ATTR = {}


def batches(rules_dir=".claude/rules"):
    """One (template, join, report glob) per live `Batch:` line in the rules files."""
    out = []
    for path in sorted(glob.glob(rules_dir + "/*.md")):
        for line in tables.live(tables.read_lines(path)):
            if not re.match(r"[-* \t]*Batch:", line):
                continue
            fields = re.sub(r"^[-* \t]*Batch:[ \t]*", "", line).split(" · ")
            tpl, join, report = fields[0], ",", ""
            for f in fields[1:]:
                if f.startswith("join:"):
                    join = re.sub(r"^join:[ \t]*", "", f)
                elif f.startswith("report:"):
                    report = re.sub(r"^report:[ \t]*", "", f)
            tpl, join, report = (re.sub(r"`[ \t]*$", "", re.sub(r"^`", "", x)) for x in (tpl, join, report))
            if "{tests}" in tpl and report != "":
                out.append((tpl, join, report))
    return out


def batch_id(cmd, tpl):
    """The test id a case command fills a template with, or None when the command is not that
    template word for word — or fills it with a list or a pattern instead of one plain id."""
    pre, _, suf = tpl.partition("{tests}")
    if not (cmd.startswith(pre) and cmd.endswith(suf) and len(cmd) >= len(pre) + len(suf)):
        return None
    tid = cmd[len(pre):len(cmd) - len(suf)]
    if tid == "" or re.search(r"[\s,+*]", tid):
        return None
    return tid


def _attr(tag, k):
    """An attribute by its exact name — `name=` must not match inside `classname=` (vitest writes
    classname first)."""
    m = _ATTR.get(k)
    if m is None:
        m = _ATTR[k] = re.compile("[ \t]" + k + '="([^"]*)"')
    found = m.search(tag)
    return found.group(1) if found else ""


def junit(files):
    """JUnit XML → one (class, test, status, rep) per <testcase>. class is the full classname (two
    packages' OrderTest stay apart); test drops `(…)` and `[n]`; status 0 pass, 1 failure/error,
    2 skipped; rep is 1 when the entry is a repetition of the same call — a bare name (go -count) or
    `name()[k]` (JUnit 5 @RepeatedTest) — and 0 for a parameterised one (`name(String)[k]`,
    `name[k]`): ten parameter sets are ten different calls, not ten repeats of one.
    Read line by line: CDATA (a captured log line reading `<error …>`) is text, never markup, and
    several testcases may share a line (`<testcase …></testcase>`, `<testcase …><skipped/></testcase>`)."""
    out = []
    for path in files:
        state = {"open": False, "incd": False, "c": "", "n": "", "st": 0, "rp": 0}

        def emit():
            out.append((state["c"], state["n"], state["st"], state["rp"]))
            state["open"] = False

        def scan(t):
            if not state["open"]:
                return
            if re.search(r"<(failure|error)[ \t>/]", t):
                state["st"] = 1
            if re.search(r"<skipped[ \t>/]", t) and state["st"] == 0:
                state["st"] = 2
            if "</testcase>" in t:
                emit()

        for line in tables.read_lines(path):
            if state["incd"]:
                i = line.find("]]>")
                if i < 0:
                    continue
                line, state["incd"] = line[i + 3:], False
            while "<![CDATA[" in line:
                i = line.find("<![CDATA[")
                rest = line[i + 9:]
                j = rest.find("]]>")
                if j < 0:
                    line, state["incd"] = line[:i], True
                    break
                line = line[:i] + rest[j + 3:]
            while True:
                m = re.search(r"<testcase[ \t>][^>]*>", line)
                if not m:
                    break
                scan(line[:m.start()])
                tag, line = m.group(0), line[m.end():]
                name = _attr(tag, "name")
                base = re.sub(r"[(\[].*", "", name)
                rest = name[len(base):]
                state.update(c=_attr(tag, "classname"), n=base, st=0, open=True,
                             rp=1 if (rest == "" or re.fullmatch(r"\(\)\[[0-9]+\]", rest)) else 0)
                if tag.endswith("/>"):
                    emit()
            scan(line)
    return out


def suggest_template(cmds):
    """A `Batch:` template guessed from commands that ran alone: their longest common prefix, cut back
    to the last delimiter (space = ( ' "), + {tests} + their longest common suffix, cut forward the same
    way. None when fewer than two commands or they share no such shape."""
    if len(cmds) < 2:
        return None
    p = s = cmds[0]
    for cmd in cmds[1:]:
        while not cmd.startswith(p):
            p = p[:-1]
        while s and not cmd.endswith(s):
            s = s[1:]
    while p and p[-1] not in " =('\"":
        p = p[:-1]
    while s and s[0] not in " )'\"$":
        s = s[1:]
    return p + "{tests}" + s if p else None
