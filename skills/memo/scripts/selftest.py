#!/usr/bin/env python3
"""selftest.py — the smallest check that fails if `clio validate`'s logic breaks."""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from cliolib.testkit import clio, read, scratch, write  # noqa: E402

REPO = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
scratch()
os.makedirs(".claude/clio/database")
os.makedirs(".claude/clio/docs/tasks/feat")
os.makedirs(".claude/clio/docs/specs/memory")
os.makedirs(".claude/clio/docs/plans")
write(".claude/clio/docs/specs/requirements.md",
      "| # | Task | Spec | Status |\n|---|---|---|---|\n| 1 | x | m | ✅ |\n| 2 | y | m | ⚠️ open |\n")
write(".claude/clio/docs/specs/memory/m.md", "")
PLAN = ".claude/clio/docs/plans/acct.md"
write(PLAN, "| # | Task | req | Levels | Needs | Done |\n|---|---|---|---|---|---|\n"
      "| 1.1 | login | 1 | unit | – | [ ] |\n| 1.2 | logout | 1 | unit | 1.1 | [ ] |\n")
A = ".claude/clio/docs/tasks/feat/1700000001_alpha.md"
B = ".claude/clio/docs/tasks/feat/1700000002_beta.md"
L = ".claude/clio/docs/tasks/legacy.md"                  # pre-3.0 flat doc, no id — still readable
for f in (A, B, L, ".claude/clio/docs/tasks/feat/summary.md"):
    write(f, "")
I = ".claude/clio/database/index.jsonl"
D = ".claude/clio/database/debt.jsonl"


def die(msg, out=None):
    print(msg)
    if out is not None:
        print(out)
    sys.exit(1)


def validate(mode):
    rc, out, _ = clio("validate", mode)
    return rc, out


def passes(mode, why):
    if validate(mode)[0] != 0:
        die("expected pass: " + why)


def fails(mode, why):
    if validate(mode)[0] == 0:
        die("expected FAIL: " + why)


def line(**rec):
    return json.dumps(rec, separators=(",", ":"), ensure_ascii=False) + "\n"


def idx(id_, doc, files, req, plan_tasks=()):
    return line(date="2026-01-01", id=id_, type="task", doc=doc, domain="x", plan_tasks=list(plan_tasks), files=files,
                commits=[], keywords=["k"], req=req, specs=[])


def old(doc, files, req):
    """A pre-3.0 record — no id, no plan_tasks. `all` names it, never fails on it."""
    return line(date="2026-01-01", type="task", doc=doc, domain="x", files=files, commits=[], keywords=["k"], req=req,
                specs=[])


def debt(id_, kind, req, blocked_by):
    return line(date="2026-01-01", id=id_, kind=kind, status="pending", domain="x", what=["w"], req=req, specs=[],
                docs=[], code=[], action="", source=None, blocked_by=blocked_by, issue=None)


def has(pat, out):
    return re.search(pat, out, re.M) is not None


write(I, idx("1700000001", A, ["a.go"], ["1"]))
passes("index", "valid index line")
write(I, idx("1700000001", A, ["a.go"], ["1"], ["1.1"]), "a")
passes("index", "plan_tasks carries the plan row")
# req is checked against requirements.md; plan_tasks must be checked against the plans the same way,
# or a typo'd id silently sends /clio:memo to tick a task nobody tested
write(I, idx("1700000001", A, ["a.go"], ["1"], ["9.9"]), "a")
fails("index", "plan_tasks 9.9 is in no plan row")
# an array, like req: a doc written before the one-doc-per-subtask split covers a range of them
write(I, idx("1700000001", A, ["a.go"], ["1"], ["1.1", "1.2"]), "a")
passes("index", "plan_tasks holds several ids")
write(I, idx("1700000001", A, ["a.go"], ["9"]), "a")
fails("index", "req 9 has no requirements row")
write(I, idx("1700000001", A, ["a.go"], [1]), "a")
fails("index", "req as a number — 7.1 and 7.10 would collide")
write(I, idx("1700000009", ".claude/clio/docs/tasks/feat/1700000009_gone.md", [], []), "a")
fails("index", "doc missing on disk")
write(I, "{not json\n", "a")
fails("index", "invalid JSON")
# id IS the filename prefix (INDEX-IT.md) — the binding that keeps one id bound to one doc
write(I, idx("1700000003", A, ["a.go"], ["1"]), "a")
fails("index", "id is not the doc's filename prefix")
write(I, old(A, ["a.go"], [1]), "a")
fails("index", "no id — 3.0 write path requires it")
write(I, line(date="2026-01-01", id="1700000001", type="task", doc=A, domain="x", plan_tasks=[], files=[],
              keywords=["k"], req=[], specs=[]), "a")
fails("index", "no commits array")
write(I, line(date="2026-01-01", id="1700000001", type="task", doc=A, plan_tasks=[], files=["a.go"], commits=[],
              keywords=["k"], req=[], specs=[]), "a")
fails("index", "no domain — INDEX-IT.md says always present")

write(D, debt("a", "spec-blocked", ["2"], "PO owes tax rule"))
passes("debt", "valid spec-blocked")
write(D, debt("c", "typo", [], None), "a")
fails("debt", "unknown kind")
write(D, debt("d", "code-debt", ["9"], None), "a")
fails("debt", "req 9 has no requirements row")
write(D, '{"id":"j","kind":"code-debt","status":"pending","what":["w"],"req":[],"specs":[],"code":[],"blocked_by":null}\n', "a")
fails("debt", "8 of 14 fields — DEBT-IT.md says all 14, always")

# debt mode is group-aware too, not just `all`: the record that FILES a spec-blocked needs its blocker,
# but a later record may null it once the answer lands (DEBT-IT.md § 1).
write(D, debt("e", "spec-blocked", ["2"], None))
fails("debt", "spec-blocked filed with null blocked_by")
write(D, debt("e", "spec-blocked", ["2"], "PO owes tax rule") + debt("e", "spec-blocked", ["2"], None))
passes("debt", "later record nulls blocked_by once unblocked")

# the FIRST record is what is judged, so a later line supplying the blocker does not launder a
# record that was filed with none — and the last line being the good one must not hide it
write(D, debt("i", "spec-blocked", ["2"], None) + debt("i", "spec-blocked", ["2"], "PO owes tax rule"))
fails("debt", "filed with null, fixed later — still the wrong filing")

# all: pre-2.0 delta ledger (scalar `commit`, shrinking files) and orphan doc both warn, run still
# passes; a clean doc that drops a reverted file must NOT be nagged as pre-2.0
write(I, line(date="2026-01-01", type="task", doc=L, domain="x", files=["a.go"], commit="abc", keywords=["k"], req=[1],
              specs=[])
      + old(L, ["b.go"], [1]) + idx("1700000001", A, ["c.go", "d.go"], ["1"]) + idx("1700000001", A, ["c.go"], ["1"]))
write(D, debt("a", "spec-blocked", ["2"], "PO owes tax rule")
      # pre-2.1 record: audit names it, run still passes
      + '{"id":"old","kind":"code-debt","status":"pending","what":["w"],"req":[],"specs":[],"code":[],"blocked_by":null}\n')
rc, out = validate("all")
if rc:
    die(out)
if not has("debt record is missing: date domain docs action source issue", out):
    die("expected missing-fields WARN for old", out)
if not has("legacy.md.*pre-2.0", out):
    die("expected pre-2.0 warn for legacy.md", out)
if not has("index record is missing: id plan_tasks", out):
    die("pre-3.0 record not named by the audit", out)
if has("1700000001_alpha.md.*pre-2.0", out):
    die("clean doc wrongly nagged as pre-2.0", out)
# a doc nested under tasks/<feature>/ must be visible to the orphan check — a non-recursive glob
# would make every 3.0 task doc invisible to it
if "orphan doc, no index record: " + B not in out:
    die("nested orphan not seen", out)
# summary.md is feature-level blurb, never an indexed doc
if has("orphan doc.*summary.md", out):
    die("summary.md wrongly called an orphan", out)

# all: a migrated doc — pre-3.0 records still key on the old path, which a migration moved away.
# The record carrying `supersedes` is what resolves them; without it this is a FAIL, with it an INFO.
M = ".claude/clio/docs/tasks/login/1700000005_login.md"
write(M, "")
write(I, old(".claude/clio/docs/tasks/2026-08-01_login.md", ["l.go"], [1])
      + line(date="2026-01-01", id="1700000005", type="task", doc=M, domain="x", plan_tasks=[], files=["l.go"], commits=[],
             keywords=["k"], req=[1], specs=[], supersedes=".claude/clio/docs/tasks/2026-08-01_login.md")
      + idx("1700000001", A, ["a.go"], ["1"]))
write(D, debt("a", "spec-blocked", ["2"], "PO owes tax rule"))
rc, out = validate("all")
if rc:
    die("a migrated doc must not fail the audit", out)
if "renamed doc, superseded" not in out:
    die("supersedes not resolved", out)
# a doc with an id that moved: its earlier line keeps the old path, which is history, not a broken link
write(I, line(date="2026-01-01", id="1700000005", type="task", doc=".claude/clio/docs/tasks/1700000005_login.md",
              domain="x", plan_tasks=[], files=["l.go"], commits=[], keywords=["k"], req=["1"], specs=[]) + read(I))
rc, out = validate("all")
if has("missing doc.*1700000005_login", out):
    die("moved id doc flagged by its history", out)
if "points at a missing file" in out:
    die("superseded path double-reported as FAIL", out)
# and the migration must read as finished: the superseded group's pre-3.0 records are history, so
# they must not keep reporting the very fields the successor just supplied — otherwise a migration
# finds work to do on every run and is never idempotent
if "index record is missing" in out:
    die("finished migration still reported as pending", out)
os.remove(M)
os.rmdir(os.path.dirname(M))

# all: a doc that gains an id but KEEPS its path — a spec or rules file the ledger indexes, which
# a migration gives an id without moving. Without bridging doc->id the pre-3.0 records form a second
# group whose last record is the old short one, and the finished migration reports as unfinished.
S = ".claude/clio/docs/specs/memory/m.md"
write(I, line(date="2026-01-01", type="task", doc=S, domain="x", files=["a.go"], commit="abc", keywords=["k"], req=[1],
              specs=[])
      + line(date="2026-01-02", id="1700000007", type="task", doc=S, domain="x", plan_tasks=[], files=["a.go"],
             commits=["abc"], keywords=["k"], req=[1], specs=[])
      + idx("1700000001", A, ["a.go"], ["1"]))
write(D, debt("a", "spec-blocked", ["2"], "PO owes tax rule"))
rc, out = validate("all")
if rc:
    die("a doc given an id in place must not fail", out)
if "index record is missing" in out:
    die("id-in-place migration still reported as pending", out)
if "pre-2.0" in out:
    die("pre-2.0 warn survived a completed migration", out)
# the filename-prefix rule is for the dirs Clio names; a spec file keeps its own name
if "is not the filename prefix" in out:
    die("prefix rule wrongly applied to a spec file", out)

# HOP2's section-reading command must not drop a section. A sed range ends ON the next heading and
# consumes it, so `## Side Effects` straight after `## Decisions` vanished — the one section that
# says what you can break. Run the documented command against a template-shaped doc.
write("sec.md", "# D\n## Summary\ns\n## Decisions\n- chose X\n## Side Effects\n- breaks Z\n## Testing Done\n- ran it\n"
      "## Follow-up\n- open\n## Change Log\n- init\n")
sec = subprocess.run(["awk", "/^## /{p = /^## (Decisions|Side Effects|Follow-up)/} p", "sec.md"],
                     stdout=subprocess.PIPE, universal_newlines=True).stdout
os.remove("sec.md")
for want in ("- chose X", "- breaks Z", "- open"):
    if want not in sec:
        die("HOP2 section read dropped: " + want, sec)
if "- ran it" in sec:
    die("HOP2 section read pulled in Testing Done", sec)
if "- init" in sec:
    die("HOP2 section read ran past Follow-up", sec)

# all: a malformed line does not suppress schema checks on the other records (2.0.1)
write(I, idx("1700000001", A, ["a.go"], ["1"])
      + line(date="2026-01-01", id="1700000002", type="nope", doc=B, domain="x", plan_tasks=[], files=[], commits=[],
             keywords=["k"], req=[1], specs=[])
      + "{broken\n")
write(D, debt("a", "spec-blocked", ["2"], "PO owes tax rule"))
rc, out = validate("all")
if rc == 0:
    die("expected FAIL behind a malformed line", out)
if "not valid JSON" not in out:
    die("expected malformed-line FAIL", out)
if "required field, bad type" not in out:
    die("bad-type record not checked past malformed line", out)

# all: spec-blocked names its blocker when filed; a later line may null it once unblocked (DEBT-IT § 1)
write(I, idx("1700000001", A, ["a.go"], ["1"]))
write(D, debt("f", "spec-blocked", ["2"], "PO owes a rule")
      + line(date="2026-01-01", id="f", kind="spec-blocked", status="pending", domain="x", what=["w"], req=[2], specs=[],
             docs=[], code=[], action="", source=None, blocked_by=None, issue=None)
      + debt("g", "spec-blocked", ["2"], None)
      + debt("i", "spec-blocked", ["2"], None)
      + debt("i", "spec-blocked", ["2"], "PO owes a rule"))
rc, out = validate("all")
if rc == 0:
    die("expected FAIL: spec-blocked g filed with null blocked_by", out)
if "debt g" not in out:
    die("g not flagged", out)
if "debt i" not in out:
    die("i filed with null, fixed later — not flagged", out)
if "debt f" in out:
    die("unblocked spec-blocked f wrongly flagged", out)
# one id, one finding: the rule lives in one place, so `all` must not report it twice
if len([l for l in out.split("\n") if "debt g" in l]) != 1:
    die("duplicate FAIL for g", out)

# A path written into a document's prose is not a field, so nothing else checks it — and renaming a
# doc is exactly what leaves one pointing at nothing. Template placeholders holding `<` are not paths.
write(I, idx("1700000001", A, ["a.go"], ["1"]))
write(D, debt("a", "spec-blocked", ["2"], "PO owes tax rule"))
write(A, "see `.claude/clio/docs/decisions/1700000099_gone.md` and `.claude/clio/docs/tasks/<feature>/<id>_x.md`\n", "a")
rc, out = validate("all")
if rc:
    die("a dead link must warn, not fail", out)
if "dead link in a document: .claude/clio/docs/decisions/1700000099_gone.md" not in out:
    die("dead link not reported", out)
if has("dead link.*<feature>", out):
    die("template placeholder wrongly reported as a path", out)
write(A, "")

# A spec-delta names a change the code has not followed. /clio:plan absorbs one by writing a task
# that carries its id, so an open, unblocked delta in no plan means the plan still matches the old
# decision — silently, until someone reads it. Blocked or done deltas are not the plan's to absorb.
write(I, idx("1700000001", A, ["a.go"], ["1"], ["1.1"]))
write(D, debt("sd", "spec-delta", ["1"], None))
rc, out = validate("all")
if rc:
    die("an unabsorbed spec-delta must warn, not fail", out)
if "spec-delta sd is in no plan" not in out:
    die("unabsorbed spec-delta not reported", out)
plan = read(PLAN)
write(PLAN, "| 9.9 | absorbs sd | 1 | t | - | [ ] |\n", "a")
out = validate("all")[1]
if "spec-delta sd is in no plan" in out:
    die("delta named in a plan still reported", out)
write(D, debt("sd", "spec-delta", ["1"], "PO owes the rule"))          # blocked: not the plan's to absorb
out = validate("all")[1]
if "is in no plan" in out:
    die("blocked delta wrongly reported", out)
write(PLAN, plan)

# a pre-4.0 plan (Test column) that was never re-planned is named; once a Levels table follows, it is not
OLD = ".claude/clio/docs/plans/old.md"
write(OLD, "| # | Task | req | Test that proves it | Needs | Done |\n|---|---|---|---|---|---|\n"
      "| 1.1 | x | 1 | `go test` | - | [x] 2026-01-01 |\n")
if "old.md is a pre-4.0 plan" not in validate("all")[1]:
    die("pre-4.0 plan not named")
write(OLD, "\n| # | Task | req | Levels | Needs | Touches | Done |\n|---|---|---|---|---|---|---|\n"
      "| 1.1.1 | harden | 1 | unit | 1.1 | - | [ ] |\n", "a")
if "old.md is a pre-4.0 plan" in validate("all")[1]:
    die("re-planned plan still named")
os.remove(OLD)

# The manifests and the four places the version lives. There is no CI, so this is the only thing
# that catches a release naming two different builds — run it before you tag.
os.chdir(REPO)
try:
    plugin = json.loads(read(".claude-plugin/plugin.json"))
    market = json.loads(read(".claude-plugin/marketplace.json"))
except ValueError:
    die("a manifest is not valid JSON")
# hooks/hooks.json loads by convention. Naming it in plugin.json too makes the loader read it twice
# and refuse both, which silently kills the drift nudge — so the manifest must NOT mention it.
if not os.path.isfile("hooks/hooks.json"):
    die("hooks/hooks.json is missing")
if "hooks" in plugin:
    die("plugin.json declares .hooks; the standard hooks/hooks.json already loads itself")
v = plugin.get("version")
if market["plugins"][0].get("version") != v:
    die("marketplace.json disagrees with plugin.json (%s)" % v)
if "version-%s-blue" % v not in read("README.md"):
    die("README badge is not version %s" % v)
if not re.search(r"(?m)^## %s[^0-9]" % re.escape(v), read("CHANGELOG.md")):
    die("CHANGELOG.md has no '## %s' heading" % v)

print("OK")
