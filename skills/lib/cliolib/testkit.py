"""testkit — what every selftest shares: a scratch repo, `clio` called as a user would, and checks that
report every miss before failing. Tests only; nothing at runtime imports it."""
import atexit
import os
import shutil
import subprocess
import sys
import tempfile

CLIO = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "bin", "clio"))
bad = 0


def scratch():
    """A fresh directory, made the cwd, removed at exit."""
    d = tempfile.mkdtemp()
    atexit.register(shutil.rmtree, d, True)
    os.chdir(d)
    return d


def clio(*args, env=None, cwd=None):
    """Run `clio <args>` → (exit code, stdout, stderr)."""
    e = dict(os.environ, **env) if env else None
    p = subprocess.run([sys.executable, CLIO] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, env=e, cwd=cwd)
    return p.returncode, p.stdout, p.stderr


def out(*args, **k):
    """stdout of `clio <args>`, trailing newline dropped — what $(...) gives in a shell."""
    return clio(*args, **k)[1].rstrip("\n")


def lines(s):
    return [l for l in s.split("\n") if l]


def git(*args, check=True):
    p = subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t"] + list(args), check=check,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return p.stdout.strip()


def write(path, text, mode="w"):
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode) as f:
        f.write(text)


def read(path):
    with open(path) as f:
        return f.read()


def eq(got, want, why):
    global bad
    if got != want:
        print("expected [%s] got [%s] — %s" % (want, got, why))
        bad = 1


def ok(cond, why):
    global bad
    if not cond:
        print(why)
        bad = 1


def done():
    if bad == 0:
        print("OK")
    sys.exit(bad)
