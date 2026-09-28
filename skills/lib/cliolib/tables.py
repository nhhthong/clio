"""The one place that reads Clio's Markdown tables and lists.

One set of rules for every reader: a line inside <!-- … --> is not read, a table row may be
indented, cells are trimmed of spaces and tabs, and an empty cell reads as `–`. Columns of a plan
table are found by header name. Every function returns plain tuples of strings, in file order.
selftest: skills/lib/selftest.py — fixtures and the exact output expected of each function.
"""
import os
import re

DASH = "–"
_ROW = re.compile(r"[ \t]*\|")
_ID = re.compile(r"[0-9]+(\.[0-9]+)*")


def read_lines(path):
    """A file's lines, newline dropped, bytes that are not UTF-8 kept as they are (surrogateescape)
    so a hash over them matches one over the raw file."""
    with open(path, encoding="utf-8", errors="surrogateescape", newline="") as f:
        text = f.read()
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def live(lines):
    """The lines outside <!-- … -->: the line that opens a comment, and every line up to and
    including the one that closes it, are skipped — a table commented out is not a table."""
    incom = False
    for line in lines:
        if "<!--" in line:
            incom = True
        if incom:
            if "-->" in line:
                incom = False
            continue
        yield line


def _z(x):
    return x if x != "" else DASH


def _cells(line):
    """The line split on `|`, cells between the outer bars trimmed of spaces and tabs. Index i is
    the i-th field counting from 1, as a `|`-split would number it: field 1 is before the first bar."""
    parts = line.split("|")
    for i in range(1, len(parts) - 1):
        parts[i] = parts[i].strip(" \t")
    return parts


def _f(parts, i):
    return parts[i - 1] if 1 <= i <= len(parts) else ""


def plan_rows(files):
    """Plan tables (.claude/clio/docs/plans/*.md), one tuple per task row:
        (file, id, task, req, levels, needs, done, kind)
    kind is `row` under a header with a Levels column (4.0+), `old` under a pre-4.0 header (Test
    column; levels is then `–`). Columns are found by header name, so a reordered table still reads
    right; rows before any header use today's positions (Done = the last cell). The header resets
    per file."""
    out = []
    for path in files:
        kind, tc, rc, lc, nc, dc = "row", 3, 4, 5, 6, 0
        for line in live(read_lines(path)):
            if not _ROW.match(line):
                continue
            c = _cells(line)
            n = len(c)
            if _f(c, 2) == "#":
                kind, tc, rc, lc, nc, dc = "old", 3, 4, 0, 0, 0
                for i in range(3, n):
                    name = _f(c, i)
                    if name == "Task":
                        tc = i
                    if name == "req":
                        rc = i
                    if name == "Levels":
                        lc, kind = i, "row"
                    if name == "Needs":
                        nc = i
                    if name == "Done":
                        dc = i
                continue
            tid = _f(c, 2)
            if not _ID.fullmatch(tid):
                continue
            out.append((path, tid, _z(_f(c, tc)), _z(_f(c, rc)),
                        _z(_f(c, lc)) if lc else DASH, _z(_f(c, nc)) if nc else DASH,
                        _z(_f(c, dc if dc else n - 1)), kind))
    return out


def req_rows(path):
    """requirements.md's row table, one (num, status) per numbered row; status is the 4th cell
    (Decision status), markers and all."""
    if not path or not os.path.isfile(path):
        return []
    out = []
    for line in live(read_lines(path)):
        if not _ROW.match(line):
            continue
        c = _cells(line)
        if _ID.fullmatch(_f(c, 2)):
            out.append((_f(c, 2), _z(_f(c, 5))))
    return out


def case_rows(levels, files):
    """Case tables (.claude/clio/docs/tests/*.md). `levels` is the allowed level names, space-separated.
    Current: | Case | Task | Level | Covers | Behaviour | Expected (source) | Command | Repeat |
    pre-4.1 (no Covers column, accepted unchanged — its rows just carry no id to enforce):
             | Case | Task | Level | Behaviour | Expected (source) | Command | Repeat |
    One tuple per case row: (case, task, level, covers, command, repeat, tracked, error).
    tracked is 1 for a Covers-column row, 0 for a pre-4.1 one. error is "" for a well-formed row; a
    malformed one is still returned, so the case it belongs to fails loudly instead of running a
    truncated command."""
    allowed = " " + levels + " "
    out = []
    for path in files:
        for line in live(read_lines(path)):
            if not _ROW.match(line):
                continue
            f = _cells(line)
            nf = len(f)
            case_id = _f(f, 2)
            if case_id == "Case" or re.fullmatch(r"[-: ]+", case_id):
                continue
            err, trk, cov, cmd, rep = "", 1, "", "", ""
            if nf == 9:
                trk, cmd, rep = 0, _f(f, 7), _f(f, 8)
            elif nf == 10:
                cov, cmd, rep = _f(f, 5), _f(f, 8), _f(f, 9)
            else:
                err = ("the row splits into %d cells, not 7 (pre-4.1) or 8 — a `|` in the command? "
                       "wrap it in a script" % (nf - 2))
            if err == "":
                if cmd.startswith("`"):
                    cmd = cmd[1:]
                if cmd.endswith("`"):
                    cmd = cmd[:-1]
                na = cmd in ("", DASH, "-")
                level = _f(f, 4)
                if (" " + level + " ") not in allowed:
                    err = "level " + level + " is not one of: " + levels
                elif not na and (not re.fullmatch(r"[0-9]+", rep) or int(rep) < 1):
                    err = "Repeat " + rep + " is not a whole number >= 1"
            out.append((_z(case_id), _z(_f(f, 3)), _z(_f(f, 4)), _z(cov), _z(cmd), _z(rep), trk, err))
    return out


def case_lines(task, files):
    """The case rows of one task exactly as written, runs of spaces and tabs squeezed to one — what
    approve hashes. The output must not change between versions: a stored approval is a hash of it."""
    out = []
    for path in files:
        for line in live(read_lines(path)):
            if _ROW.match(line) and _f(line.split("|"), 3).strip(" \t") == task:
                out.append(re.sub(r"[ \t]+", " ", line))
    return out


def list_bullets(title, files):
    """The bullets of one named list in a tests doc (`<Title>:` on its own line), whitespace-squeezed,
    in order — only those: the list ends at the next heading, table row or paragraph, so a bullet
    under `## Notes` is never read as part of it. A wrapped bullet's indented continuation stays
    inside it."""
    out = []
    for path in files:
        in_list = False
        for line in live(read_lines(path)):
            h = re.sub(r"[*_#]", "", line).strip(" \t")
            if h.endswith(":"):
                h = h[:-1]
            if h == title and not re.match(r"[ \t]*-", line):
                in_list = True
                continue
            if not in_list or re.fullmatch(r"[ \t]*", line) or re.match(r"[ \t]+[^ \t-]", line):
                continue
            if re.match(r"-[ \t]*[^ \t]", line):
                out.append(re.sub(r"[ \t]+", " ", line))
                continue
            in_list = False
    return out


def _fields(raw):
    body = re.sub(r"^-[ \t]*", "", raw).strip(" \t")
    return re.split(r"[ \t]+", body) if body else []


def na_rows(files):
    """`- <task> · <level.n> — <reason>` bullets of a tests doc's `Not applicable:` list, one
    (task, id, line) each; the `·` between task and id may have no spaces around it."""
    out = []
    for raw in list_bullets("Not applicable", files):
        f = _fields(raw.replace("·", " "))
        out.append((f[0] if f else "", f[1] if len(f) > 1 else "", raw))
    return out


def waiver_rows(files):
    """`- <case-id> — <reason>` bullets of a tests doc's `Red waived:` list: a critical case whose
    red cannot be reproduced from history, approved by the user. One (case, line) each."""
    out = []
    for raw in list_bullets("Red waived", files):
        f = _fields(raw)
        out.append((f[0] if f else "", raw))
    return out
