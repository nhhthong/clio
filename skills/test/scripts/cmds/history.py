"""`clio test history <case-id>` — every recorded run of one case, oldest first."""
import testcore as tc
from cliolib import common as c


def cmd_history(cid):
    """Every recorded run of one case, oldest first: date · result passed/runs · fp · red@base ·
    batch · exit · commit — what a person reads when the gate's verdict needs explaining."""
    lines = []
    for r in tc.records():
        if r.get("case") != cid:
            continue
        passed = r.get("passed")
        runs_ = r.get("runs")
        lines.append("  ".join([
            c.tostring(r.get("date")) if r.get("date") is not None else "",
            c.tostring(r.get("result")) if r.get("result") is not None else "",
            "%s/%s" % ("?" if passed is None or passed is False else c.tostring(passed),
                       "?" if runs_ is None or runs_ is False else c.tostring(runs_)),
            c.tostring(r.get("fp")) if r.get("fp") is not None else "",
            "red@" + c.tostring(r["red_base"]) if c.truthy(r.get("red_base")) else "-",
            "batch" if c.truthy(r.get("batch")) else "-",
            "exit " + c.tostring(r.get("exit")),
            c.tostring(r["commit"]) if c.truthy(r.get("commit")) else "-"]))
    tc.say("\n".join(lines) if lines else "no runs recorded for " + cid)
    return 0
