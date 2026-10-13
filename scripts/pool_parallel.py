#!/usr/bin/env python3
"""pool_parallel.py: run the frozen analyze.py pool step with crash signatures computed in parallel.

  pool_parallel.py precompute [WORKERS]   compute and cache signatures for all crash artefacts present now
  pool_parallel.py pool [WORKERS]         fill any missing signatures, then run analyze.cmd_pool() unchanged
  pool_parallel.py selftest N             check on N artefacts that the cached path gives the same
                                          signatures as analyze.crash_signature called directly

analyze.py is frozen (FREEZE_AMENDMENT_1.md) and is not changed. Its pool step replays every crash
artefact one at a time; with tens of thousands of artefacts that takes many hours. This wrapper calls
the same function, analyze.crash_signature, in a process pool and caches each result by file path and
SHA-256 (results/sig_cache.json), then runs analyze.cmd_pool() with crash_signature replaced by the
cache lookup. The signature definition does not change. The cache holds no arm labels and is not opened
during triage.
"""
import glob
import hashlib
import json
import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze  # noqa: E402

CACHE = os.path.join(analyze.RES, "sig_cache.json")


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def artefacts():
    out = []
    for t in analyze.TRIALS:
        out += sorted(glob.glob(os.path.join(analyze.RUNS, t, "artifacts", "*")))
    return out


def load():
    return json.load(open(CACHE)) if os.path.exists(CACHE) else {}


def save(cache):
    os.makedirs(analyze.RES, exist_ok=True)
    tmp = CACHE + ".tmp"
    json.dump(cache, open(tmp, "w"), sort_keys=True)
    os.replace(tmp, CACHE)


def one(path):
    return path, sha256(path), analyze.crash_signature(path)


def fill(workers):
    cache = load()
    todo = [p for p in artefacts() if p not in cache or cache[p]["sha256"] != sha256(p)]
    print("artefacts: %d; to compute: %d; workers: %d" % (len(artefacts()), len(todo), workers), flush=True)
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for path, h, sig in ex.map(one, todo, chunksize=8):
            cache[path] = {"sha256": h, "sig": sig}
            done += 1
            if done % 500 == 0:
                save(cache)
                print("computed %d of %d" % (done, len(todo)), flush=True)
    save(cache)
    return cache


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "precompute"
    if cmd == "selftest":
        n = int(sys.argv[2])
        pool = artefacts()
        sample = random.SystemRandom().sample(pool, min(n, len(pool)))
        with ProcessPoolExecutor(max_workers=4) as ex:
            par = dict((p, s) for p, _, s in ex.map(one, sample))
        same = sum(1 for p in sample if analyze.crash_signature(p) == par[p])
        print("selftest: %d of %d signatures identical (parallel against direct call)" % (same, len(sample)))
        return
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    cache = fill(workers)
    if cmd == "pool":
        analyze.crash_signature = lambda p: cache[p]["sig"]
        analyze.cmd_pool()


if __name__ == "__main__":
    main()
