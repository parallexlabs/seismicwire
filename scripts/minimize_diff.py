#!/usr/bin/env python3
"""minimize_diff.py: shrink an input while the oracle still reports the same disagreement signature
(the delta-debugging step of the pre-registered triage, PREREGISTRATION.md section 7).

  minimize_diff.py REPLAY_DIFF INPUT SIGNATURE OUTPUT

Two passes, each kept only if the signature is still reported:
1. truncation: the shortest prefix of the input (binary search, then a linear check);
2. zeroing: delta debugging over byte ranges, setting ranges to zero rather than removing them,
   so record offsets stay valid.
Prints the number of non-zero bytes before and after, and a list of the bytes that remain non-zero.
"""
import os
import shutil
import subprocess
import sys
import tempfile

FIND = None  # one scratch findings folder per run, kept next to the output as <output>.findings at the end


def has_sig(replay, data, sig):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
        f.write(data)
        path = f.name
    try:
        env = dict(os.environ, SW_VERBOSE="1", SW_FINDINGS=FIND)
        r = subprocess.run([replay, path], capture_output=True, text=True, env=env, timeout=30)
        return any(line.split(" ")[1] == sig for line in r.stderr.splitlines() if line.startswith("DIFF "))
    finally:
        os.unlink(path)


def truncate(replay, data, sig):
    lo, hi = 1, len(data)
    while lo < hi:
        mid = (lo + hi) // 2
        if has_sig(replay, data[:mid], sig):
            hi = mid
        else:
            lo = mid + 1
    return data[:hi] if has_sig(replay, data[:hi], sig) else data


def zero_ddmin(replay, data, sig):
    data = bytearray(data)
    n = 2
    while True:
        live = [i for i, b in enumerate(data) if b]
        if not live:
            break
        chunk = max(1, len(live) // n)
        changed = False
        for start in range(0, len(live), chunk):
            trial = bytearray(data)
            for i in live[start:start + chunk]:
                trial[i] = 0
            if has_sig(replay, bytes(trial), sig):
                data = trial
                changed = True
        if not changed:
            if chunk == 1:
                break
            n = min(n * 2, len(live))
        else:
            n = max(n - 1, 2)
    return bytes(data)


def main():
    global FIND
    replay, inp, sig, out = sys.argv[1:5]
    FIND = tempfile.mkdtemp(prefix="swmin-")
    data = open(inp, "rb").read()
    if not has_sig(replay, data, sig):
        sys.exit("the input does not reproduce signature %s" % sig)
    before = sum(1 for b in data if b)
    data = truncate(replay, data, sig)
    data = zero_ddmin(replay, data, sig)
    assert has_sig(replay, data, sig)
    open(out, "wb").write(data)
    after = [(i, b) for i, b in enumerate(data) if b]
    print("length %d; non-zero bytes %d -> %d" % (len(data), before, len(after)))
    print(" ".join("%d:%02x" % (i, b) for i, b in after[:200]))
    keep = out + ".findings"
    n = 1
    while os.path.exists(keep):
        keep = "%s.findings-%d" % (out, n)
        n += 1
    shutil.move(FIND, keep)
    print("replay findings kept in", keep)


if __name__ == "__main__":
    main()
