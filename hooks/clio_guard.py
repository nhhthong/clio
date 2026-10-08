#!/usr/bin/env python3
"""clio_guard.py — PreToolUse hook. Two kinds of file have one writer each: runs.jsonl (test
evidence) is written only by `clio test`, and the plan and test stores (database/plan/*.jsonl,
database/test/*.jsonl) only by `clio add` and `clio test`, index.jsonl / debt.jsonl only by `clio add` — the one place a task becomes done is
`clio test tick`, after the gate. Refuses an Edit/Write on them and a Bash command that writes,
deletes or reverts them any other way (redirect, tee, sed -i, rm, truncate, dd, mv, cp/install, git
restore/checkout). Reads — cat, jq, grep, `cp <file> <somewhere outside the database dir>` — pass.
Acts only in a repo with .claude/clio, so another tool's runs.jsonl elsewhere is never touched. Exit
2 blocks the call and hands stderr to Claude.
The command is tokenized with shlex (quotes and `#` comments as bash reads them), split into simple
commands, and each judged on its own. A `clio test|add ...` call is an excuse only when it leads its
command and carries no `$(...)`, backtick or `<(...)` substitution. cp/install fail closed: the one
shape allowed is `cp <a guarded file> <destination outside .claude/clio/database>`.
ponytail: pattern match on the command text — a script that opens the file itself gets past it.
It stops the shortcut, not a determined bypass; the gate's fingerprint and approval do the rest.
Python 3.9+, standard library only."""
import json
import os
import re
import shlex
import sys

B = r"(^|[\s(){}!`])"                                             # a command word starts here
# A guarded file named in a command: the evidence file, or anything under the plan/test store dirs.
NAMED = r"(runs\.jsonl|clio/database/(plan|test)(/|\b)|database/(index|debt)\.jsonl)"
PROTECTED = re.compile(NAMED)
REDIRECT = re.compile(r">[>|]?\s*\S*" + NAMED)                   # > >> >| &> 2> onto one — raw text
WRITES = [
    re.compile(B + r"(tee|truncate|rm|dd|shred)(\s|$)|" + B + r"sed\s+(\S+\s+)*(-[a-zA-Z]*i|--in-place)"),
    re.compile(B + r"mv(\s|$)"),
    re.compile(B + r"git\s+(restore|checkout)(\s|$)"),
]
COPY = re.compile(r"^(\S*/)?(cp|install)$")
WRITER = re.compile(r"^(\S*/)?clio\s+(test|add)(\s|$)")
SUBST = ("$(", "`", "<(", ">(")
SEPS = {";", "&", "&&", "|", "||", "\n", ";;", "|&"}
DB = "/.claude/clio/database"
ARG_OPTS = {"-S", "-m", "-o", "-g", "-t", "--suffix", "--mode", "--owner", "--group", "--target-directory"}


def refuse(msg):
    sys.stderr.write("clio: %s — runs.jsonl is written only by `clio test`, the plan and test stores only by "
                     "`clio add` (and `clio test tick`, after the gate), index.jsonl and debt.jsonl only by `clio add "
                     "index|debt` (validated, rolled back on a FAIL); go through them instead.\n" % msg)
    sys.exit(2)


def guarded_path(p):
    """True for the evidence file or a plan/test store file of a Clio repo."""
    p = p if p.startswith("/") else "/" + p
    return p.endswith((DB + "/runs.jsonl", DB + "/index.jsonl", DB + "/debt.jsonl")) or re.search(re.escape(DB) + r"/(plan|test)/[^/]*$", p) is not None


def clio_above(d):
    d = os.path.abspath(d)
    while True:
        if os.path.isdir(os.path.join(d, ".claude", "clio")):
            return True
        parent = os.path.dirname(d)
        if parent == d:
            return False
        d = parent


def commands(cmd):
    """Simple commands as token lists. Quotes stay on the tokens (non-posix) so a quoted `#` is never
    taken for a comment; an unquoted token starting with `#` ends its command, as in bash."""
    lx = shlex.shlex(cmd, posix=False, punctuation_chars=";&|\n")
    lx.whitespace = " \t\r"
    lx.commenters = ""
    lx.whitespace_split = True
    out, cur, comment = [], [], False
    for t in lx:
        if t in SEPS or set(t) <= set(";&|\n"):
            out.append(cur)
            cur, comment = [], False
        elif not comment:
            if t.startswith("#"):
                comment = True
            else:
                cur.append(t)
    out.append(cur)
    return [c for c in out if c]


def unquote(t):
    try:
        parts = shlex.split(t)
    except ValueError:
        return t
    return parts[0] if len(parts) == 1 else t


def copy_ok(args, cwd):
    """True only for `cp [opts] <a guarded file> <dest outside the database dir>`. Anything else —
    a target-directory option, not exactly two operands, the evidence file as destination — False."""
    operands, skip, end = [], False, False
    for a in (unquote(t) for t in args):
        if skip:
            skip = False
        elif end or not a.startswith("-") or a == "-":
            operands.append(a)
        elif a == "--":
            end = True
        elif a.startswith("--target-directory") or (not a.startswith("--") and "t" in a[1:]):
            return False
        elif a in ARG_OPTS:
            skip = True
    if len(operands) != 2:
        return False
    src, dst = (os.path.normpath(os.path.join(cwd, p)) for p in operands)
    return guarded_path(src) and not (dst.endswith(DB) or DB + "/" in dst + "/")


def check(cmd, cwd):
    if REDIRECT.search(cmd):
        refuse("a redirect onto a guarded file refused")
    try:
        cmds = commands(cmd)
    except ValueError:
        refuse("a command naming a guarded file that cannot be parsed refused")
    for toks in cmds:
        text = " ".join(toks)
        if not PROTECTED.search(text):
            continue
        if WRITER.match(text) and not any(s in text for s in SUBST):
            continue
        for i, t in enumerate(toks):
            if COPY.match(unquote(t)) and not copy_ok(toks[i + 1:], cwd):
                refuse("a cp/install touching a guarded file refused — only `cp <it> <outside the database dir>` passes: " + text)
        if any(r.search(text) for r in WRITES):
            refuse("a command writing, deleting or reverting a guarded file refused: " + text)


def main():
    try:
        data = json.loads(sys.stdin.read())
    except ValueError:
        return
    if not isinstance(data, dict):
        return
    tool = data.get("tool_name") or ""
    inp = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    if tool in ("Write", "Edit", "MultiEdit"):
        path = inp.get("file_path") or ""
        if isinstance(path, str) and guarded_path(path):
            refuse(tool + " on " + path + " refused")
    elif tool == "Bash":
        cmd = inp.get("command") or ""
        if not isinstance(cmd, str) or not PROTECTED.search(cmd):
            return
        cwd = data.get("cwd") or os.getcwd()
        # Clio's runs.jsonl only: its directory named in the command, or a bare name inside a repo that
        # has .claude/clio. The directory, not the full path: `cp x/runs.jsonl <db dir>/` names no file.
        if "clio/database" not in cmd and not clio_above(cwd):
            return
        check(cmd, cwd)


if __name__ == "__main__":
    main()
