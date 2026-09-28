"""cliolib — the code Clio's scripts share: Markdown tables, the working-tree fingerprint, batch
templates and JUnit reports, the repo root and the JSONL ledgers. Python 3.9+, standard library only.

Each entry script (skills/*/scripts/*.py, hooks/*.py) puts skills/lib on sys.path and imports from
here; nothing in this package prints, exits or changes directory on import.
"""
