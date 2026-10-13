#!/usr/bin/env python3
"""diskguard.py: stop the running SeismicWire trials, by process group, if free disk space falls too low.

  diskguard.py MIN_FREE_GIB TRIAL [TRIAL ...]

Every 20 seconds it reads the free space of the data volume. It writes one sample a minute to
runs/diskguard-samples.tsv (time, free GiB, size of runs/ in MiB). If free space falls below
MIN_FREE_GIB, or if the file STOP_TRIALS appears in the work folder (any seat may create it),
it stops each named trial with pgrun.py stop (whole group, then a survivor check),
appends the stop time and reason to DEVIATIONS.md, and exits. It ends by itself when no named
trial is running any more.
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ROOT = os.path.dirname(REPO)
RUNS = os.path.join(ROOT, "runs")
VOL = "/System/Volumes/Data"


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S PT")


def free_gib():
    s = os.statvfs(VOL)
    return s.f_bavail * s.f_frsize / 1024.0 ** 3


def runs_mib():
    total = 0
    for d, _, files in os.walk(RUNS):
        for f in files:
            try:
                total += os.lstat(os.path.join(d, f)).st_size
            except OSError:
                pass
    return total / 1024.0 ** 2


def running(name):
    d = os.path.join(RUNS, name)
    return os.path.exists(os.path.join(d, "job.json")) and not os.path.exists(os.path.join(d, "exit.json"))


def main():
    limit = float(sys.argv[1])
    trials = sys.argv[2:]
    samples = os.path.join(RUNS, "diskguard-samples.tsv")
    last = 0.0
    while True:
        live = [t for t in trials if running(t)]
        if not live:
            print(now(), "no named trial is running; guard ends", flush=True)
            return
        f = free_gib()
        if time.time() - last >= 60:
            with open(samples, "a") as fh:
                fh.write("%s\t%.2f\t%.1f\n" % (now(), f, runs_mib()))
            last = time.time()
        asked = os.path.exists(os.path.join(ROOT, "STOP_TRIALS"))
        if f < limit or asked:
            t0 = now()
            out = []
            for t in live:
                r = subprocess.run([sys.executable, os.path.join(HERE, "pgrun.py"), "stop", t],
                                   capture_output=True, text=True)
                out.append("%s: %s" % (t, (r.stdout + r.stderr).strip()))
            why = "the STOP_TRIALS file was present" if asked else "free space was below the guard"
            line = ("\n%s. Disk guard stop (" + why + "): free space on %s was %.2f GiB (guard %.0f GiB) at %s. "
                    "Stopped by process group: %s. Result: %s. The comparison uses only the time each trial ran; "
                    "see exit.json in each run folder.\n")
            with open(os.path.join(REPO, "DEVIATIONS.md")) as fh:
                n = sum(1 for l in fh if l[:1].isdigit() and ". " in l[:5])
            with open(os.path.join(REPO, "DEVIATIONS.md"), "a") as fh:
                fh.write(line % (n + 1, VOL, f, limit, t0, ", ".join(live), "; ".join(out)))
            print(t0, "stopped", live, flush=True)
            return
        time.sleep(20)


if __name__ == "__main__":
    main()
