#!/usr/bin/env python3
"""analyze.py: pre-registered analysis of the SeismicWire trials (PREREGISTRATION.md, section 6).

  analyze.py stats      per-trial wall and CPU time, executions, crash artefacts, oracle signatures
  analyze.py coverage   line and branch coverage of libmseed from each trial's final corpus
  analyze.py pool       pooled triage sheet with random candidate IDs (key kept apart)
  analyze.py outcome    primary and secondary outcomes from results/triage.tsv after unblinding
  analyze.py replayA    exploratory: arm A final corpora replayed through the oracle offline

Paths: SW_ROOT (default: the folder above this repository); writes to SW_ROOT/results/.
"""
import glob
import json
import os
import random
import re
import subprocess
import sys
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("SW_ROOT", os.path.abspath(os.path.join(HERE, "..", "..")))
RUNS = os.path.join(ROOT, "runs")
RES = os.path.join(ROOT, "results")
BIN = os.path.join(ROOT, "build", "bin")
LIBMSEED = os.environ.get("LIBMSEED_SRC", os.path.join(ROOT, "libmseed-3.5.4"))
TRIALS = ["%s%d" % (a, s) for a in "AB" for s in range(1, 6)]


def a12(x, y):
    """Vargha and Delaney A12: probability that a value from x exceeds one from y (ties half)."""
    gt = sum(1 for i in x for j in y if i > j)
    eq = sum(1 for i in x for j in y if i == j)
    return (gt + 0.5 * eq) / (len(x) * len(y))


def mwu(x, y):
    try:
        from scipy.stats import mannwhitneyu
        r = mannwhitneyu(x, y, alternative="two-sided")
        return {"U": float(r.statistic), "p": float(r.pvalue)}
    except Exception as e:  # report the failure, never a made-up value
        return {"error": str(e)}


def last_status(log):
    """Last libFuzzer fork-mode status line: '#N: cov: C ft: F corp: K exec/s E oom/timeout/crash: a/b/c time: Ts'."""
    best = None
    pat = re.compile(r"^#(\d+): cov: (\d+) ft: (\d+) corp: (\d+) exec/s:? (\d+) oom/timeout/crash: (\d+)/(\d+)/(\d+) time: (\d+)s")
    for line in open(log, errors="replace"):
        m = pat.match(line)
        if m:
            best = dict(zip(["execs", "cov", "ft", "corp", "exec_s", "ooms", "timeouts", "crashes", "time_s"], map(int, m.groups())))
    return best


def trial_stats(t):
    d = os.path.join(RUNS, t)
    if not os.path.exists(os.path.join(d, "job.json")):
        return None
    job = json.load(open(os.path.join(d, "job.json")))
    ex = json.load(open(os.path.join(d, "exit.json"))) if os.path.exists(os.path.join(d, "exit.json")) else None
    st = last_status(os.path.join(d, "job.log"))
    arts = sorted(glob.glob(os.path.join(d, "artifacts", "*")))
    first_art = min((os.path.getmtime(a) - job["start"] for a in arts), default=None)
    sigs = {}
    for f in glob.glob(os.path.join(d, "findings", "counts-*.tsv")):
        for line in open(f):
            k, v = line.rstrip("\n").split("\t")
            sigs[k] = sigs.get(k, 0) + int(v)
    first_sig = {}
    sf = os.path.join(d, "findings", "signatures.tsv")
    if os.path.exists(sf):
        for line in open(sf):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3:
                first_sig[p[2]] = min(first_sig.get(p[2], 1e18), int(p[0]) - job["start"])
    return {"trial": t, "start": job["start_local"], "exit": ex, "status": st, "artifacts": len(arts),
            "first_artifact_s": first_art, "oracle_counts": sigs, "first_signature_s": first_sig}


def cmd_stats():
    os.makedirs(RES, exist_ok=True)
    out = {t: trial_stats(t) for t in TRIALS}
    json.dump(out, open(os.path.join(RES, "stats.json"), "w"), indent=1, sort_keys=True)
    for t, s in out.items():
        if not s:
            print(t, "not started")
            continue
        e, st = s["exit"] or {}, s["status"] or {}
        print("%s wall=%s cpu=%s execs=%s exec/s=%s artifacts=%d oracle_signatures=%d" % (
            t, e.get("wall_s"), round(e.get("user_cpu_s", 0) + e.get("sys_cpu_s", 0), 1) if e else None,
            st.get("execs"), st.get("exec_s"), s["artifacts"],
            len([k for k in s["oracle_counts"] if not k.startswith("_") and not k.startswith("info.")])))
    cpus = {t: (s["exit"]["user_cpu_s"] + s["exit"]["sys_cpu_s"]) for t, s in out.items() if s and s["exit"]}
    a = [v for t, v in cpus.items() if t[0] == "A"]
    if a:
        m = median(a)
        for t, v in cpus.items():
            if abs(v - m) > 0.10 * m:
                print("NOTE: %s CPU %.0f s differs by more than 10%% from the arm A median %.0f s" % (t, v, m))


def coverage_of(corpus, tag):
    """Replay a corpus through the profile build; return libmseed line and branch coverage."""
    work = os.path.join(RES, "cov", tag)
    os.makedirs(work, exist_ok=True)
    files = sorted(glob.glob(os.path.join(corpus, "*")))
    env = dict(os.environ, LLVM_PROFILE_FILE=os.path.join(work, "p-%p.profraw"))
    for i in range(0, len(files), 200):
        subprocess.run([os.path.join(BIN, "replay_prof")] + files[i:i + 200], env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    prof = os.path.join(work, "merged.profdata")
    subprocess.run(["xcrun", "llvm-profdata", "merge", "-sparse", "-o", prof] +
                   glob.glob(os.path.join(work, "*.profraw")), check=True)
    rep = subprocess.run(["xcrun", "llvm-cov", "export", "-summary-only", "-instr-profile", prof,
                          os.path.join(BIN, "replay_prof")], capture_output=True, text=True, check=True).stdout
    data = json.loads(rep)["data"][0]["files"]
    lines = [0, 0]
    branches = [0, 0]
    for f in data:
        if os.path.abspath(f["filename"]).startswith(os.path.abspath(LIBMSEED)):
            s = f["summary"]
            lines[0] += s["lines"]["covered"]; lines[1] += s["lines"]["count"]
            branches[0] += s["branches"]["covered"]; branches[1] += s["branches"]["count"]
    return {"lines_covered": lines[0], "lines": lines[1], "branches_covered": branches[0], "branches": branches[1],
            "line_pct": round(100.0 * lines[0] / max(lines[1], 1), 2),
            "branch_pct": round(100.0 * branches[0] / max(branches[1], 1), 2), "inputs": len(files)}


def cmd_coverage():
    os.makedirs(RES, exist_ok=True)
    out = {"seed": coverage_of(os.path.join(ROOT, "corpus-seed"), "seed")}
    for t in TRIALS:
        c = os.path.join(RUNS, t, "corpus")
        if os.path.isdir(c) and os.path.exists(os.path.join(RUNS, t, "exit.json")):
            out[t] = coverage_of(c, t)
    for key in ("line_pct", "branch_pct"):
        a = [out[t][key] for t in out if t.startswith("A")]
        b = [out[t][key] for t in out if t.startswith("B")]
        if a and b:
            out["summary_" + key] = {"A_median": median(a), "A_range": [min(a), max(a)], "B_median": median(b),
                                     "B_range": [min(b), max(b)], "A12_B_over_A": a12(b, a), "mann_whitney": mwu(b, a)}
    json.dump(out, open(os.path.join(RES, "coverage.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps({k: v for k, v in out.items() if k.startswith("summary") or k == "seed"}, indent=1))


def crash_signature(path):
    """Replay one artefact with the arm A binary and keep the first three frames inside libmseed."""
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:symbolize=1", UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    r = subprocess.run([os.path.join(BIN, "fuzz_A"), path], capture_output=True, text=True, env=env, timeout=60)
    kind = re.search(r"(ERROR: AddressSanitizer: [\w-]+|runtime error: [^\n]{0,80}|ERROR: libFuzzer: [\w-]+)", r.stderr)
    frames = re.findall(r"#\d+ 0x[0-9a-f]+ in (\S+) (\S+?):\d+", r.stderr)
    lm = ["%s@%s" % (fn, os.path.basename(loc)) for fn, loc in frames if os.path.abspath(LIBMSEED) in os.path.abspath(loc)][:3]
    return (kind.group(1) if kind else "no-report") + " | " + " < ".join(lm)


def cmd_pool():
    """Pooled candidates with random IDs; the key goes to results/blind_key.json (not opened in triage)."""
    os.makedirs(RES, exist_ok=True)
    cands = {}
    for t in TRIALS:
        d = os.path.join(RUNS, t)
        for a in sorted(glob.glob(os.path.join(d, "artifacts", "*"))):
            sig = "crash: " + crash_signature(a)
            cands.setdefault(sig, {"trials": set(), "examples": []})
            cands[sig]["trials"].add(t)
            cands[sig]["examples"].append(a)
        for f in glob.glob(os.path.join(d, "findings", "*.bin")):
            sig = "oracle: " + os.path.basename(f).rsplit("__", 1)[0]
            if sig.startswith("oracle: info."):
                continue
            cands.setdefault(sig, {"trials": set(), "examples": []})
            cands[sig]["trials"].add(t)
            cands[sig]["examples"].append(f)
    ids = random.SystemRandom().sample(range(1000, 9999), len(cands))
    key, sheet = {}, []
    for (sig, c), cid in zip(sorted(cands.items()), ids):
        key["C%d" % cid] = sorted(c["trials"])
        sheet.append((cid, sig, sorted(c["examples"])[0], len(c["examples"])))
    random.SystemRandom().shuffle(sheet)
    json.dump(key, open(os.path.join(RES, "blind_key.json"), "w"), indent=1, sort_keys=True)
    with open(os.path.join(RES, "triage_sheet.tsv"), "w") as f:
        f.write("candidate\tsignature\texample\texamples\tcategory\troot_cause\tseverity\tspec_clause\tsecond_decoder\tnote\n")
        for cid, sig, ex, n in sheet:
            f.write("C%d\t%s\t%s\t%d\t\t\t\t\t\t\n" % (cid, sig, ex, n))
    print("%d candidates; sheet results/triage_sheet.tsv; key results/blind_key.json" % len(sheet))


def cmd_outcome():
    """Primary outcome after triage: results/triage.tsv (the filled sheet) plus the key."""
    key = json.load(open(os.path.join(RES, "blind_key.json")))
    rows = [l.rstrip("\n").split("\t") for l in open(os.path.join(RES, "triage.tsv"))][1:]
    defects = {}
    for r in rows:
        cid, cat, root = r[0], r[4], r[5]
        if cat == "libmseed defect":
            defects.setdefault(root, set()).update(key[cid])
    out = {}
    for root, trials in sorted(defects.items()):
        a = sorted(t for t in trials if t[0] == "A")
        b = sorted(t for t in trials if t[0] == "B")
        out[root] = {"A_trials": a, "B_trials": b, "B_only": bool(b) and not a}
    claim = any(v["B_only"] for v in out.values())
    res = {"defects": out, "A_union": sum(1 for v in out.values() if v["A_trials"]),
           "B_union": sum(1 for v in out.values() if v["B_trials"]),
           "primary_claim_allowed": claim,
           "clean_result": not out}
    json.dump(res, open(os.path.join(RES, "outcome.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps(res, indent=1))


def cmd_replayA():
    """Exploratory: replay each arm A final corpus through the uninstrumented oracle."""
    for t in TRIALS[:5]:
        c = os.path.join(RUNS, t, "corpus")
        if not os.path.isdir(c):
            continue
        fd = os.path.join(RES, "replayA", t)
        os.makedirs(fd, exist_ok=True)
        files = sorted(glob.glob(os.path.join(c, "*")))
        for i in range(0, len(files), 200):
            subprocess.run([os.path.join(BIN, "replay_diff")] + files[i:i + 200], env=dict(os.environ, SW_FINDINGS=fd),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
        sigs = {}
        for f in glob.glob(os.path.join(fd, "counts-*.tsv")):
            for line in open(f):
                k, v = line.rstrip("\n").split("\t")
                sigs[k] = sigs.get(k, 0) + int(v)
        print(t, json.dumps({k: v for k, v in sorted(sigs.items())}))


if __name__ == "__main__":
    {"stats": cmd_stats, "coverage": cmd_coverage, "pool": cmd_pool, "outcome": cmd_outcome,
     "replayA": cmd_replayA}[sys.argv[1] if len(sys.argv) > 1 else "stats"]()
