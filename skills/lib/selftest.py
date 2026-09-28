#!/usr/bin/env python3
"""selftest.py — cliolib.tables against fixtures holding every awkward row the parsers must agree
on: an indented row, a table inside <!-- -->, a pre-4.0 header, a reordered header, a superseded
row, an empty cell, a `|` inside a command. Prints OK or each mismatch; exit 1 on any."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cliolib import tables  # noqa: E402

bad = 0


def eq(got, want, what):
    global bad
    if got != want:
        print("FAIL %s\n--- got\n%s\n--- want\n%s" % (what, got, want))
        bad = 1


def tsv(rows):
    return "\n".join("\t".join(str(x) for x in r) for r in rows)


def write(name, text):
    with open(name, "w", encoding="utf-8") as f:
        f.write(text)


with tempfile.TemporaryDirectory() as d:
    os.chdir(d)
    write("plan.md", """# Plan — orders
| # | Task | req | Test that proves it | Needs | Done |
|---|------|-----|---------------------|-------|------|
| 3.2 | 401 without session | 3 | `go test ./x` | – | superseded 2026-09-24 → 3.2.1 |

<!--
| 9.9 | commented out | 9 | unit | – | – | [ ] |
-->

| # | Task | req | Levels | Needs | Touches | Done |
|---|------|-----|--------|-------|---------|------|
| 3.1 | list | 3 | unit, api | 0.4 | `orders/h.go` | [x] 2026-09-20 |
  | 3.2.1 | 401 without session | 3 | critical · api, security | 3.1 | | [ ] |
| 7.1 | — waits on `ocr-dpi-open` | 7.1 | – | – | – | – |
""")
    write("reordered.md", """| # | Levels | Task | Done | req | Needs |
|---|---|---|---|---|---|
| 5.1 | unit | moved columns | [ ] | 5 | – |
""")
    eq(tsv(tables.plan_rows(["plan.md", "reordered.md"])), "\n".join([
        "plan.md\t3.2\t401 without session\t3\t–\t–\tsuperseded 2026-09-24 → 3.2.1\told",
        "plan.md\t3.1\tlist\t3\tunit, api\t0.4\t[x] 2026-09-20\trow",
        "plan.md\t3.2.1\t401 without session\t3\tcritical · api, security\t3.1\t[ ]\trow",
        "plan.md\t7.1\t— waits on `ocr-dpi-open`\t7.1\t–\t–\t–\trow",
        "reordered.md\t5.1\tmoved columns\t5\tunit\t–\t[ ]\trow"]), "plan_rows")

    write("req.md", """| # | Task | Spec file(s) | Decision status (NOT build status) |
|---|------|--------------|-------------|
| 1 | login | [memory/a.md](memory/a.md) | ✅ |
 | 7.10 | ocr | [memory/b.md](memory/b.md) | ⚠️ dpi open |
<!-- | 8 | draft | x | ✅ | -->
""")
    eq(tsv(tables.req_rows("req.md")), "1\t✅\n7.10\t⚠️ dpi open", "req_rows")
    eq(tables.req_rows("missing.md"), [], "req_rows of a missing file")

    write("tests.md", """| Case | Task | Level | Covers | Behaviour | Expected (source) | Command | Repeat |
|---|---|---|---|---|---|---|---|
| 3.1-u1 | 3.1 | unit | unit.1 | ok | 50 (spec) | `go test -run A$` | 1 |
  | 3.1-a1 | 3.1 | api | api.1 | ok | 200 | `go test -run B$` | 1 |
| 3.1-x1 | 3.1 | unit | unit.1 | pipe | x | `a || b` | 1 |
| 3.1-z1 | 3.1 | smoke | – | n/a | x | – | – |
<!-- | 3.1-c1 | 3.1 | unit | unit.1 | commented | x | `true` | 1 | -->
| 2.1-u1 | 2.1 | unit | old format | x | `true` | 3 |

- 3.1 · api.9 — a bullet before any Not applicable list is not an excuse

Not applicable:
- 3.1 · api.2 — read-only route
  wrapped onto a second line
-   3.1·unit.3   —   spaced oddly

## Notes

- 3.1 · unit.1 — already covered elsewhere (a note, not an excuse)
""")
    eq(tsv(tables.case_rows("unit api smoke", ["tests.md"])), "\n".join([
        "3.1-u1\t3.1\tunit\tunit.1\tgo test -run A$\t1\t1\t",
        "3.1-a1\t3.1\tapi\tapi.1\tgo test -run B$\t1\t1\t",
        "3.1-x1\t3.1\tunit\t–\t–\t–\t1\tthe row splits into 10 cells, not 7 (pre-4.1) or 8 — a `|` in the command? wrap it in a script",
        "3.1-z1\t3.1\tsmoke\t–\t–\t–\t1\t",
        "2.1-u1\t2.1\tunit\t–\ttrue\t3\t0\t"]), "case_rows")
    eq([r[7] for r in tables.case_rows("unit", ["tests.md"]) if r[0] == "3.1-a1"],
       ["level api is not one of: unit"], "case_rows level check")
    eq(len(tables.case_lines("3.1", ["tests.md"])), 4, "case_lines: the commented row is not approved")
    eq(tables.case_lines("3.1", ["tests.md"])[0],
       "| 3.1-u1 | 3.1 | unit | unit.1 | ok | 50 (spec) | `go test -run A$` | 1 |", "case_lines normalised")
    eq([r[:2] for r in tables.na_rows(["tests.md"])], [("3.1", "api.2"), ("3.1", "unit.3")], "na_rows ids")

    write("waivers.md", """- 3.1-u1 — a bullet before the list is not a waiver

**Red waived:**
- 3.1-u2 — correct since abc123; red --base abc123 passed
- 3.1-u3   —  spaced   oddly

Not applicable:
- 3.1 · api.2 — not a waiver
""")
    eq([r[0] for r in tables.waiver_rows(["waivers.md"])], ["3.1-u2", "3.1-u3"], "waiver_rows ids")
    eq(tables.waiver_rows(["waivers.md"])[-1][1], "- 3.1-u3 — spaced oddly", "waiver_rows normalised")
    eq([r[:2] for r in tables.na_rows(["waivers.md"])], [("3.1", "api.2")], "na_rows beside a waiver list")

    os.chdir("/")

if bad == 0:
    print("OK")
sys.exit(bad)
