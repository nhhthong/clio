#!/usr/bin/env python3
"""setup.py check | run --domains "a b" [--lite] [--ignore] [--git-init] — run from the project root
  check  print what blocks setup or what already exists (MISSING / NOT A GIT REPO / ALREADY SET UP / PARTLY SET UP)
  run    create .claude/clio/, fill Domains in requirements.md, write .gitattributes (unless --ignore)
Exit 1 on MISSING or ALREADY SET UP."""
import os
import re
import shutil
import subprocess
import sys

C = ".claude/clio"
REQ = C + "/docs/specs/requirements.md"
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "requirements.md")
LITE = "Lite mode — no requirement source; every record uses req: [] and joins on domain/keywords/files.\n"


def state():
    out = [f"MISSING: {t}" for t in ("bash", "git") if not shutil.which(t)]
    if sys.version_info < (3, 9):
        out.append("MISSING: python3 >= 3.9")
    if subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True).returncode:
        out.append("NOT A GIT REPO")
    done = all(os.path.isfile(f"{C}/{p}") for p in ("docs/specs/requirements.md", "database/index.jsonl", "database/debt.jsonl"))
    if done:
        out.append("ALREADY SET UP")
    elif os.path.isdir(C):
        out.append("PARTLY SET UP")
    return out


def run(domains, lite, ignore):
    for d in ("database/plan", "database/test", "docs/specs/memory", "docs/tasks", "docs/decisions"):
        os.makedirs(f"{C}/{d}", exist_ok=True)
    if not os.path.isfile(REQ):
        shutil.copy(TEMPLATE, REQ)
    for f in ("index", "debt", "runs"):
        open(f"{C}/database/{f}.jsonl", "a").close()
    words = sorted(set(domains.split()) | {"infra", "all"})
    text = open(REQ, encoding="utf-8").read()
    text = re.sub(r"<domains[^>]*>", " ".join(f"`{w}`" for w in words), text, count=1)
    if lite:
        text = text.split("## By requirement number")[0] + "## By requirement number\n\n" + LITE
    open(REQ, "w", encoding="utf-8").write(text)
    if not ignore:
        open(f"{C}/.gitattributes", "w").write("database/*.jsonl merge=union\n")


def main(argv):
    if not argv or argv[0] not in ("check", "run"):
        print(__doc__)
        return 1
    if argv[0] == "check":
        out = state()
        print("\n".join(out) or "OK")
        return int(any(l.startswith("MISSING") or l == "ALREADY SET UP" for l in out))
    if "--git-init" in argv:
        subprocess.run(["git", "init"], check=True)
    domains = argv[argv.index("--domains") + 1] if "--domains" in argv else ""
    run(domains, "--lite" in argv, "--ignore" in argv)
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
