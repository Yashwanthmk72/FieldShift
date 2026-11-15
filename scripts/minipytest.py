#!/usr/bin/env python3
# AI-assisted: written with an AI coding assistant.
"""Tiny offline stand-in for pytest, used ONLY in sandboxes where pytest cannot be installed.
Supports what this repo's tests use: plain/async test functions, fixtures, tmp_path, monkeypatch, parametrize, skipif, raises, approx.
It is NOT pytest. Real results must come from `pytest -q`. Usage: python3 scripts/minipytest.py [paths...]"""
import asyncio, contextlib, inspect, importlib.util, math, os, re, shutil, sys, tempfile, traceback, types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("FIELDSHIFT_ENV", "development")


class Skip(Exception):
    pass


class _Raises:
    def __init__(self, exc, match=None):
        self.exc, self.match = exc, match
    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        if t is None:
            raise AssertionError(f"DID NOT RAISE {self.exc}")
        if not issubclass(t, self.exc):
            return False
        if self.match and not re.search(self.match, str(v)):
            raise AssertionError(f"'{self.match}' not found in '{v}'")
        self.value = v
        return True


class approx:
    def __init__(self, x, rel=1e-6, abs=1e-12):
        self.x, self.rel, self.abs = x, rel, abs
    def __eq__(self, o):
        return math.isclose(o, self.x, rel_tol=self.rel, abs_tol=self.abs)
    def __repr__(self):
        return f"approx({self.x})"


class _Mark:
    def parametrize(self, names, cases):
        names = [n.strip() for n in names.split(",")] if isinstance(names, str) else names
        def deco(f):
            f._params = (names, cases)
            return f
        return deco
    def skipif(self, cond, reason=""):
        def deco(f):
            if cond:
                f._skip = reason
            return f
        return deco


FIXTURES = {}
def fixture(f=None, **kw):
    if f is None:
        return lambda g: fixture(g)
    FIXTURES[f.__name__] = f
    return f


class MonkeyPatch:
    def __init__(self):
        self.undo_list = []
    def setitem(self, d, k, v):
        self.undo_list.append((d, k, d.get(k, KeyError)))
        d[k] = v
    def setattr(self, o, n, v=None, raising=True):
        if isinstance(o, str):
            mod, _, attr = o.rpartition("."); o, n, v = importlib.import_module(mod), attr, n
        self.undo_list.append((o, n, getattr(o, n, KeyError), "attr"))
        setattr(o, n, v)
    def setenv(self, k, v):
        self.setitem(os.environ, k, v)
    def delenv(self, k, raising=True):
        if k in os.environ:
            self.undo_list.append((os.environ, k, os.environ[k])); del os.environ[k]
    def undo(self):
        for item in reversed(self.undo_list):
            if len(item) == 4:
                o, n, old, _ = item
                setattr(o, n, old) if old is not KeyError else delattr(o, n)
            else:
                d, k, old = item
                d.pop(k, None) if old is KeyError else d.__setitem__(k, old)


shim = types.ModuleType("pytest")
def _importorskip(name):
    return importlib.import_module(name)
shim.importorskip = _importorskip
shim.raises, shim.approx, shim.mark, shim.fixture, shim.skip = _Raises, approx, _Mark(), fixture, lambda r="": (_ for _ in ()).throw(Skip(r))
sys.modules.setdefault("pytest", shim)
try:
    import pytest as _real  # noqa
    REAL = hasattr(_real, "main")
except Exception:
    REAL = False


def call(f, kwargs):
    r = f(**kwargs)
    if inspect.iscoroutine(r):
        asyncio.run(r)


def run_file(path, results):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        results.append((path.name, "<import>", "ERROR", f"{type(e).__name__}: {e}"))
        return
    for name, f in list(vars(mod).items()):
        if not name.startswith("test_") or not callable(f):
            continue
        if getattr(f, "_skip", None) is not None:
            results.append((path.name, name, "SKIP", f._skip)); continue
        names, cases = getattr(f, "_params", ([], [()]))
        for case in cases:
            tmp, mp, gens = [], MonkeyPatch(), []
            try:
                kw = dict(zip(names, case if isinstance(case, (tuple, list)) and len(names) > 1 else (case,)))
                for p in inspect.signature(f).parameters:
                    if p in kw:
                        continue
                    if p == "tmp_path":
                        d = Path(tempfile.mkdtemp()); tmp.append(d); kw[p] = d
                    elif p == "monkeypatch":
                        kw[p] = mp
                    elif p in FIXTURES or hasattr(mod, p):
                        fx = FIXTURES.get(p) or getattr(mod, p)
                        a = {}
                        for q in inspect.signature(fx).parameters:
                            if q == "tmp_path":
                                d = Path(tempfile.mkdtemp()); tmp.append(d); a[q] = d
                        v = fx(**a)
                        if inspect.isgenerator(v):
                            gens.append(v); v = next(v)
                        kw[p] = v
                call(f, kw)
                results.append((path.name, name, "PASS", ""))
            except Skip as s:
                results.append((path.name, name, "SKIP", str(s)))
            except Exception as e:
                results.append((path.name, name, "FAIL", "".join(traceback.format_exception_only(type(e), e)).strip()[:300]))
            finally:
                mp.undo()
                for g in gens:
                    try: next(g)
                    except StopIteration: pass
                for d in tmp:
                    shutil.rmtree(d, ignore_errors=True)


def main(argv):
    paths = [Path(a) for a in argv] or [ROOT / "tests"]
    files = []
    for p in paths:
        files += sorted(p.glob("test_*.py")) if p.is_dir() else [p]
    results = []
    for f in files:
        if "frontend" in f.parts and not argv:
            continue
        run_file(f, results)
    for fn, n, s, m in results:
        if s != "PASS":
            print(f"{s:5} {fn}::{n} {m}")
    c = {k: sum(1 for r in results if r[2] == k) for k in ("PASS", "FAIL", "ERROR", "SKIP")}
    print(f"\nminipytest (NOT pytest): {c['PASS']} passed, {c['FAIL']} failed, {c['ERROR']} import errors, {c['SKIP']} skipped")
    return 1 if c["FAIL"] or c["ERROR"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
