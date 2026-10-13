#!/usr/bin/env python3
"""pool_sig2.py: crash signatures v1 (frozen) and v2 (corrected) from one replay per artefact (deviation 8).

  pool_sig2.py fill [WORKERS]            replay every crash artefact once; cache v1 and v2 signatures
  pool_sig2.py retry-timeouts [WORKERS]  replay again the artefacts whose replay timed out (for example after a pause)
  pool_sig2.py selftest N                check on N random artefacts that v1 equals analyze.crash_signature
  pool_sig2.py counts                    number of distinct v1 and v2 crash signatures (no trial or arm information)
  pool_sig2.py pool                      run the frozen analyze.cmd_pool() with crash_signature = cached v2,
                                         then replace the sheet's example paths by blind copies

Why: the frozen analyze.crash_signature keeps libmseed frames only when the frame's file path lies
inside the libmseed source folder, but the macOS symbolizer prints file basenames ("file.c:LINE").
Every frame is therefore dropped: AddressSanitizer reports merge by error kind alone, and
UndefinedBehaviorSanitizer reports split by the faulting address that their message contains.
v2 keeps the frozen replay command, environment and regular expressions, and changes two things:
a frame counts as a libmseed frame when its file basename is a libmseed source file, and hexadecimal
addresses in the error text are masked as "0x?". v1 is computed from the same replay output exactly as
the frozen function does, so both can be reported. analyze.py itself is not changed.
"""
import glob
import hashlib
import json
import os
import random
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze  # noqa: E402

CACHE = os.path.join(analyze.RES, "sig_cache_v2.json")
KIND = re.compile(r"(ERROR: AddressSanitizer: [\w-]+|runtime error: [^\n]{0,80}|ERROR: libFuzzer: [\w-]+)")
FRAME = re.compile(r"#\d+ 0x[0-9a-f]+ in (\S+) (\S+?):\d+")
LM_BASENAMES = sorted(
    os.path.basename(p)
    for p in glob.glob(os.path.join(analyze.LIBMSEED, "*.[ch]"))
)


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def artefacts():
    out = []
    for t in analyze.TRIALS:
        out += sorted(glob.glob(os.path.join(analyze.RUNS, t, "artifacts", "*")))
    return out


def signatures(stderr):
    kind = KIND.search(stderr)
    frames = FRAME.findall(stderr)
    k1 = kind.group(1) if kind else "no-report"
    lm1 = ["%s@%s" % (fn, os.path.basename(loc)) for fn, loc in frames
           if os.path.abspath(analyze.LIBMSEED) in os.path.abspath(loc)][:3]
    k2 = re.sub(r"0x[0-9a-fA-F]+", "0x?", k1)
    lm2 = ["%s@%s" % (fn, os.path.basename(loc)) for fn, loc in frames
           if os.path.basename(loc) in LM_BASENAMES][:3]
    return k1 + " | " + " < ".join(lm1), k2 + " | " + " < ".join(lm2)


def one(path):
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:symbolize=1",
               UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    try:
        r = subprocess.run([os.path.join(analyze.BIN, "fuzz_A"), path], capture_output=True,
                           text=True, env=env, timeout=60)
        v1, v2 = signatures(r.stderr)
    except subprocess.TimeoutExpired:
        v1 = v2 = "replay-timeout"
    return path, sha256(path), v1, v2


def load():
    return json.load(open(CACHE)) if os.path.exists(CACHE) else {}


def save(cache):
    os.makedirs(analyze.RES, exist_ok=True)
    tmp = CACHE + ".tmp"
    json.dump(cache, open(tmp, "w"), sort_keys=True)
    os.replace(tmp, CACHE)


def fill(workers, only_timeouts=False):
    cache = load()
    if only_timeouts:
        todo = [p for p, v in cache.items() if v["v1"] == "replay-timeout"]
    else:
        todo = [p for p in artefacts() if p not in cache or cache[p]["sha256"] != sha256(p)]
    print("artefacts: %d; to replay: %d; workers: %d" % (len(artefacts()), len(todo), workers), flush=True)
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for path, h, v1, v2 in ex.map(one, todo, chunksize=8):
            cache[path] = {"sha256": h, "v1": v1, "v2": v2}
            done += 1
            if done % 500 == 0:
                save(cache)
                print("replayed %d of %d" % (done, len(todo)), flush=True)
    save(cache)
    return cache


def blind_examples(res=None):
    """Replace each example path on the sheet (it names the trial folder) by a blind copy.

    The frozen sheet lists sorted(examples)[0], a path under runs/<trial>/, so an arm B path would
    show that no arm A trial found the candidate. Each example is copied to
    results/triage_examples/<candidate>.bin and the original paths are sealed in
    results/example_map.json, which, like blind_key.json, is not opened until every candidate is
    classified."""
    import shutil
    res = res or analyze.RES
    sheet = os.path.join(res, "triage_sheet.tsv")
    rows = [line.rstrip("\n").split("\t") for line in open(sheet)]
    head, body = rows[0], rows[1:]
    col = head.index("example")
    outdir = os.path.join(res, "triage_examples")
    os.makedirs(outdir, exist_ok=True)
    sealed = {}
    for r in body:
        cid, src = r[0], r[col]
        dst = os.path.join(outdir, cid + ".bin")
        shutil.copyfile(src, dst)
        sealed[cid] = src
        r[col] = dst
    json.dump(sealed, open(os.path.join(res, "example_map.json"), "w"), indent=1, sort_keys=True)
    tmp = sheet + ".tmp"
    with open(tmp, "w") as fh:
        for r in [head] + body:
            fh.write("\t".join(r) + "\n")
    os.replace(tmp, sheet)
    print("examples blinded: %d; original paths sealed in example_map.json" % len(body))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "counts"
    if cmd == "selftest":
        n = int(sys.argv[2])
        sample = random.SystemRandom().sample(artefacts(), n)
        same = 0
        for p in sample:
            _, _, v1, _ = one(p)
            same += v1 == analyze.crash_signature(p)
        print("selftest: v1 equals analyze.crash_signature on %d of %d artefacts" % (same, n))
    elif cmd in ("fill", "retry-timeouts"):
        workers = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        fill(workers, only_timeouts=(cmd == "retry-timeouts"))
    elif cmd == "counts":
        cache = load()
        print("cached artefacts: %d; distinct v1: %d; distinct v2: %d; timeouts: %d" % (
            len(cache), len({v["v1"] for v in cache.values()}), len({v["v2"] for v in cache.values()}),
            sum(v["v1"] == "replay-timeout" for v in cache.values())))
    elif cmd == "pool":
        cache = load()
        missing = [p for p in artefacts() if p not in cache]
        if missing:
            sys.exit("missing signatures for %d artefacts: run fill first" % len(missing))
        analyze.crash_signature = lambda p: cache[p]["v2"]
        analyze.cmd_pool()
        blind_examples()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
