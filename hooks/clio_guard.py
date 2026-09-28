#!/usr/bin/env python3
"""clio_guard.py — PreToolUse hook. runs.jsonl is test evidence: only `clio test` may append to it.
Refuses an Edit/Write on it and a Bash command that writes, deletes or reverts it any other way
(redirect, tee, sed -i, rm, truncate, dd, mv, cp/install onto it, git restore/checkout). Reads —
cat, jq, grep, a cp *from* it — pass. Acts only in a repo with .claude/clio, so another tool's
runs.jsonl elsewhere is never touched. Exit 2 blocks the call and hands stderr to Claude.
ponytail: pattern match on the command text — a script that opens the file itself gets past it.
It stops the shortcut, not a determined bypass; the gate's fingerprint and approval do the rest.
Python 3.9+, standard library only."""
import json
import os
import re
import sys

WRITES = [
    re.compile(r">>?\s*\S*runs\.jsonl"),                                                   # > or >> onto it
    re.compile(r"(^|\s)(tee|truncate|rm|dd)(\s|$)|sed\s+(-[a-zA-Z]*i|--in-place)"),
    re.compile(r"(^|\s)mv(\s|$)"),
    re.compile(r"git\s+(restore|checkout)(\s|$)"),
]
COPY = re.compile(r"(^|\s)(cp|install)(\s|$)")
WRITER = re.compile(r"(^|[\s/])clio\s+test(\s|$)")                                    # bin/clio test …


def refuse(msg):
    sys.stderr.write("clio: %s — runs.jsonl is written only by `clio test` run/approve; run the case instead.\n" % msg)
    sys.exit(2)


def clio_above(d):
    d = os.path.abspath(d)
    while True:
        if os.path.isdir(os.path.join(d, ".claude", "clio")):
            return True
        parent = os.path.dirname(d)
        if parent == d:
            return False
        d = parent


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
        if isinstance(path, str) and path.endswith(".claude/clio/database/runs.jsonl"):
            refuse(tool + " on runs.jsonl refused")
    elif tool == "Bash":
        cmd = inp.get("command") or ""
        if not isinstance(cmd, str) or "runs.jsonl" not in cmd:
            return
        # Clio's runs.jsonl only: named by its path, or a bare name inside a repo that has .claude/clio.
        if "clio/database/runs.jsonl" not in cmd and not clio_above(data.get("cwd") or os.getcwd()):
            return
        # Split on ; && || | and newlines, then judge each simple command on its own.
        for part in re.sub(r"(\|\||&&|;|\|)", "\n", cmd).split("\n"):
            if "runs.jsonl" not in part or WRITER.search(part):
                continue
            words = part.split()
            last = words[-1] if words else ""
            if any(r.search(part) for r in WRITES) or (COPY.search(part) and last.endswith("runs.jsonl")):
                refuse("a command writing, deleting or reverting runs.jsonl refused: " + part)


if __name__ == "__main__":
    main()
