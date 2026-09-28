"""What a test run is bound to: the working tree's content as a git tree id, split into test files
and the code under test. Every function takes the repo (or `red` worktree) directory it works on.

The ids must stay byte-for-byte what earlier versions computed: runs.jsonl in every repo using Clio
holds them, and a changed id voids all that evidence at once.
selftest: skills/lib/selftest_fingerprint.py
"""
import hashlib
import json
import os
import re
import shutil
import tempfile

from . import common as c

# Paths that are test code, not the code under test. A red run counts only if these were the same as
# at the pass and the rest was not — "same test, other code" — so breaking the test instead of the code
# proves nothing. Covers the usual layouts: Go `_test.go`, JS/TS `.test.`/`.spec.`, pytest `test_*.py`,
# JVM `src/test/`, Rails `spec/`, `tests/`, `__tests__/`, `testdata/`, `*Test.java`.
# ponytail: one fixed pattern; make it a per-repo setting when a real layout falls outside it.
TEST_PATHS = re.compile(r"(^|/)(tests?|__tests__|specs?|testdata|e2e|cypress)/|[_.](test|spec)\.[^/]*$"
                        r"|(^|/)(test_[^/]*|conftest)\.py$|Tests?\.(java|kt|scala|cs|swift|php)$")


def blob_hash(data):
    """`git hash-object --stdin`, first 12 hex digits — computed here, no process needed."""
    if isinstance(data, str):
        data = data.encode("utf-8", "surrogateescape")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()[:12]


def artifacts(runs):
    """Files earlier runs created (coverage files, mutation reports): outputs of a test, not code.
    Files only: a directory entry (ends in /, written before 4.1) would hide any source added to it later."""
    out = set()
    if not os.path.isfile(runs):
        return out
    with open(runs, encoding="utf-8", errors="surrogateescape") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict):
                for a in c.items(r.get("artifacts")):
                    if isinstance(a, str) and not a.endswith("/"):
                        out.add(a)
    return out


def _pathspecs(cmd, specs, cwd, env):
    """git add / git rm with their pathspecs as arguments — an artifact path always `literal`, never a
    glob. (Not --pathspec-from-file: `git rm` only has it from 2.26, and on an older git the call
    would fail quietly and leave .claude/ in the tree.)"""
    return c.git(cmd + ["--"] + specs, cwd=cwd, env=env)


def fp_tree(repo, runs):
    """The working tree's content as a full git tree id: every tracked and untracked, non-ignored file,
    minus .claude/ and known test artifacts. Content-addressed, so committing the same code keeps the
    id; any edit to code changes it. Built in a copy of the real index so git reuses its stat cache."""
    fd, idx = tempfile.mkstemp()
    os.close(fd)
    try:
        gi = c.git_out(["rev-parse", "--git-path", "index"], cwd=repo)
        gi = os.path.join(repo, gi) if gi and not os.path.isabs(gi) else gi
        if gi and os.path.isfile(gi):
            # copy2 keeps the index's mtime: git re-hashes a file whose mtime is not older than the index
            # ("racy git"). A copy stamped "now" let a same-size edit made in the second after a
            # `git add` pass as unchanged, and the fp did not move.
            shutil.copy2(gi, idx)
        else:
            os.remove(idx)
        env = {"GIT_INDEX_FILE": idx}
        # An artifact that has since been tracked is source now (a generated file committed, a
        # snapshot kept): it counts again, or edits to it would never move the fp.
        tracked = set(c.git(["ls-files", "-z"], cwd=repo).stdout.split("\0"))
        ex = sorted(artifacts(runs) - tracked)
        # -f: without it git refuses a path staged and then edited again (a ledger mid-memo), silently
        # leaving its staged copy in the tree — every later `git add` of that ledger then moves the fp.
        _pathspecs(["rm", "-r", "-q", "-f", "--cached", "--ignore-unmatch"],
                   [".claude"] + [":(literal)" + a for a in ex], repo, env)
        _pathspecs(["add", "-A"], [".", ":(exclude).claude"] + [":(exclude,literal)" + a for a in ex], repo, env)
        return c.git_out(["write-tree"], cwd=repo, env=env)
    finally:
        if os.path.exists(idx):
            os.remove(idx)


def fp(repo, runs):
    return fp_tree(repo, runs)[:12]


def split_fp(repo, tree):
    """(test-fp, code-fp) of a tree from fp_tree: each is the hash of that half of its `ls-tree -r`
    listing, lines exactly as git prints them."""
    listing = c.git(["ls-tree", "-r", tree], cwd=repo).stdout.split("\n")
    test, code = [], []
    for line in listing:
        if not line:
            continue
        path = line.split("\t", 1)[1] if "\t" in line else ""
        (test if TEST_PATHS.search(path) else code).append(line + "\n")
    return blob_hash("".join(test)), blob_hash("".join(code))


def untracked(repo):
    """Untracked, non-ignored files right now — diffed around a run to find what it created. Files,
    not directories: excluding a whole new directory would hide code written into it after the run."""
    out = c.git(["ls-files", "-o", "--exclude-standard", "-z", "--", ".", ":(exclude).claude"], cwd=repo).stdout
    return {p for p in out.split("\0") if p}
