#!/usr/bin/env python3
"""selftest_context.py — `clio q context`: one report for what /clio:context used to gather in 4–5 hops."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from cliolib.testkit import clio, done, git, ok, out, scratch, write  # noqa: E402

scratch()
git("init", "-q")
for d in ("database/plan", "database/test", "docs/specs/memory", "docs/tasks/ui"):
    os.makedirs(".claude/clio/" + d)
os.makedirs(".claude/rules")
write(".claude/clio/docs/specs/requirements.md", """# Requirements
Domains: `ui` `infra`

## By requirement number

| # | Task | Spec file(s) | Decision status |
|---|------|--------------|-----------------|
| 1 | Main screen | [memory/ui.md](memory/ui.md) | ✅ decided |
| 2 | Theme picker | [memory/theme.md](memory/theme.md) | ⚠️ colours open |
| 3 | Export | [memory/export.md](memory/export.md) | ✅ decided |

## By topic keyword

| Task mentions | Read |
|---|---|
| palette / colour | memory/theme.md |
""")
write(".claude/clio/docs/specs/memory/ui.md", "# UI\n\n## Decisions\n- The screen has a list.\n- Keys: q quits.\n\n## Open — ⚠️\n- None.\n\n## Source\n> x\n")
write(".claude/clio/docs/specs/memory/theme.md", "# Theme\n\n## Decisions\n- Seven themes.\n\n## Open — ⚠️\n- ⚠️ Which accent for `default`? — owed by user, since 2026-10-01\n\n## Source\n> x\n")
write(".claude/clio/docs/specs/memory/export.md", "# Export\n\n## Decisions\n- CSV only.\n\n## Open — ⚠️\n- None.\n\n## Source\n> x\n")
DOC = ".claude/clio/docs/tasks/ui/1700000001_screen.md"
OLD = ".claude/clio/docs/tasks/ui/1700000002_old.md"
write(DOC, "# Screen\n\n## Summary\ns\n\n## Decisions\n- The list is a bubbles/list.\n\n## Side Effects\n- Resizes the panel.\n\n## Follow-up\n- Try it on a real terminal.\n\n## Change Log\n- x\n")
write(OLD, "# Old\n\n## [SUPERSEDED 2026-10-08] Decisions — REVERTED, DO NOT RE-IMPLEMENT\n- A two-column layout.\n\n## Follow-up\n- none\n")
write(".claude/clio/docs/tasks/ui/summary.md", "# UI\n\n## General Memory\n- Test keys with tea.KeyPressMsg.\n")
write(".claude/clio/database/index.jsonl",
      json.dumps({"date": "2026-10-01", "id": "1700000001", "type": "task", "doc": DOC, "domain": "ui", "plan_tasks": ["1.1"], "files": ["ui/screen.go"],
                  "commits": [], "keywords": ["screen"], "req": ["1"], "specs": [".claude/clio/docs/specs/memory/ui.md"]}) + "\n" +
      json.dumps({"date": "2026-10-08", "id": "1700000002", "type": "task", "doc": OLD, "domain": "ui", "plan_tasks": ["1.2"], "files": [],
                  "commits": [], "keywords": ["screen"], "req": ["1"], "specs": [".claude/clio/docs/specs/memory/ui.md"]}) + "\n")


def debt(i, kind, req, blocked, status="pending", domain="ui"):
    return json.dumps({"date": "2026-10-01", "id": i, "kind": kind, "status": status, "domain": domain, "what": ["what " + i], "req": req, "specs": [],
                       "docs": [], "code": [], "action": "a", "source": None, "blocked_by": blocked, "issue": None}) + "\n"


write(".claude/clio/database/debt.jsonl", debt("palette-open", "spec-blocked", ["3"], "user: which export?") + debt("lost", "code-debt", ["1"], None, status="done"))


def task(tid, req, area="ui", status="open", needs=(), touches=()):
    return json.dumps({"type": "task", "id": tid, "date": "2026-10-01", "task": "t " + tid, "req": req, "levels": ["unit"], "critical": False, "tier": "full",
                       "needs": list(needs), "touches": list(touches), "na": {}, "status": status, "by": None, "commit": None, "delta": None}) + "\n"


write(".claude/clio/database/plan/ui.jsonl", task("1.1", ["1"], status="done") + task("1.2", ["1"], status="done") + task("1.3", ["1"], needs=["1.1"], touches=["ui/screen.go"]) + task("1.4", ["1"], needs=["1.9"]))
write(".claude/clio/database/test/ui.jsonl", json.dumps({"type": "case", "id": "1.3-u1", "date": "2026-10-01", "task": "1.3", "level": "unit", "covers": ["unit.1"], "behaviour": "b",
                                                      "expected": "e", "source": "s", "command": "true", "repeat": 1, "status": "active"}) + "\n")
write(".claude/rules/go.md", "---\npaths:\n  - \"**/*.go\"\n---\n- gofmt\n")


def ctx(*a):
    return out("q", "context", *a)


# an area: rows, the spec file with its decision count, built docs with their load-bearing sections, the plan
r = ctx("ui")
ok("requirement rows (1)" in r and "spec .claude/clio/docs/specs/memory/ui.md: 2 decisions, 0 open" in r, "rows/spec: " + r)
ok("[Decisions]" in r and "The list is a bubbles/list." in r and "[Follow-up]" in r and "Try it on a real terminal." in r, "built sections: " + r)
ok("A two-column layout." not in r and "[SUPERSEDED 2026-10-08] — do not follow, the code is gone" in r, "a reverted section was shown as current: " + r)
ok("feature ui [General Memory]" in r and "Test keys with tea.KeyPressMsg." in r, "the feature memory: " + r)
ok("1.3" in r and "ready" in r and "1.4" in r and "waits on 1.9" in r, "plan: " + r)
ok("ui/screen.go" in r and ".claude/rules/go.md" in r, "rules for the touched file: " + r)
ok("no cases yet" in r and r.index("1.4") > r.index("1.3"), "cases flag: " + r)

# a row with its open ⚠️ and a debt it is tracked by... and one it is not
r = ctx("2")
ok("⚠️ Which accent for `default`?" in r, "the open point of the spec file: " + r)
ok("row 2 is ⚠️/❌ and no open debt record tracks it" in r, "an untracked ⚠️ row: " + r)

# a debt id resolves to its rows; the debt blocked on a row that reads ✅ is reported
r = ctx("palette-open")
ok("BLOCKED by user: which export?" in r, "the debt: " + r)
ok("row 3 is ✅" in r, "ctx of a debt id shows its row: " + r)
write(".claude/clio/database/debt.jsonl", debt("palette-open", "spec-blocked", ["3"], "user: which export?"), "a")
ok("debt palette-open waits on user: which export? but its row(s) 3 read ✅ now" in ctx("palette-open"), "a blocker already answered: " + ctx("palette-open"))

# a task id, a file, a word from the keyword table
ok("requirement rows (1)" in ctx("1.3") and "t 1.3" in ctx("1.3"), "a task id: " + ctx("1.3"))
ok("ui/screen.go" in ctx("ui/screen.go") and "1700000001_screen.md" in ctx("ui/screen.go"), "a file: " + ctx("ui/screen.go"))
ok("memory/theme.md" in ctx("colour") and "requirement rows (1)" in ctx("colour"), "a keyword: " + ctx("colour"))

# nothing matches: said, not an error
r = ctx("zzz-nothing")
ok("none matches" in r and "built (0 doc(s)" in r, "no match: " + r)

# no target: the overview
ok("ui: done=2 open=2" in ctx() or "ui: done=2 open=2" in out("q", "context"), "no target is the summary: " + out("q", "context"))
done()
