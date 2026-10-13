#!/usr/bin/env python3
"""pgrun.py: run long jobs in their own process group, and stop them by group.

  pgrun.py start NAME [--wall SECONDS] -- CMD [ARGS...]   start CMD detached in a new session
  pgrun.py status [NAME]                                   show state, pid, group, elapsed and CPU
  pgrun.py stop NAME                                       stop the whole group, then check that nothing survives

Each job gets runs/NAME/ with: cmd.txt, job.log (stdout and stderr), job.json (pid, pgid, start)
and, when it ends, exit.json (exit status, wall time, user and system CPU of the job and all its
children). A supervisor process waits for the job and writes exit.json; with --wall it stops the
group after that many seconds. The job and the supervisor run in separate sessions, so stopping
the job's group never stops the supervisor before it records the result.
"""
import json
import os
import resource
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.environ.get("SW_RUNS", os.path.join(os.path.dirname(HERE), "..", "runs"))


def jobdir(name):
    return os.path.abspath(os.path.join(RUNS, name))


def group_pids(pgid):
    """Live members of a process group (zombies are already dead and are left out)."""
    out = subprocess.run(["ps", "-ax", "-o", "pid=,pgid=,stat="], capture_output=True, text=True).stdout
    pids = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and int(parts[1]) == pgid and not parts[2].startswith("Z"):
            pids.append(int(parts[0]))
    return pids


def signal_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, PermissionError):  # macOS: EPERM when only zombies are left
        pass


def stop_group(pgid, grace=10.0):
    """TERM the group, wait, KILL what is left; return the pids still alive afterwards."""
    if not group_pids(pgid):
        return []
    signal_group(pgid, signal.SIGTERM)
    end = time.time() + grace
    while time.time() < end and group_pids(pgid):
        time.sleep(0.5)
    if group_pids(pgid):
        signal_group(pgid, signal.SIGKILL)
        time.sleep(1.0)
    return group_pids(pgid)


def supervise(name, wall, cmd):
    d = jobdir(name)
    log = open(os.path.join(d, "job.log"), "ab", buffering=0)
    t0 = time.time()
    p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         start_new_session=True)
    with open(os.path.join(d, "job.json"), "w") as f:
        json.dump({"pid": p.pid, "pgid": p.pid, "supervisor": os.getpid(), "start": t0,
                   "start_local": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "wall_limit": wall}, f)
    timed_out = False
    while True:
        rc = p.poll()
        if rc is not None:
            break
        if wall and time.time() - t0 > wall:
            timed_out = True
            stop_group(p.pid)
        time.sleep(1.0)
    survivors = stop_group(p.pid, grace=2.0)  # children left behind by a finished parent
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    with open(os.path.join(d, "exit.json"), "w") as f:
        json.dump({"returncode": rc, "wall_s": round(time.time() - t0, 1), "timed_out": timed_out,
                   "user_cpu_s": round(ru.ru_utime, 1), "sys_cpu_s": round(ru.ru_stime, 1),
                   "survivors": survivors, "end_local": time.strftime("%Y-%m-%d %H:%M:%S %Z")}, f)


def cmd_start(argv):
    name = argv[0]
    wall = 0.0
    rest = argv[1:]
    if rest and rest[0] == "--wall":
        wall = float(rest[1])
        rest = rest[2:]
    if not rest or rest[0] != "--":
        sys.exit("usage: pgrun.py start NAME [--wall S] -- CMD ...")
    cmd = rest[1:]
    d = jobdir(name)
    if os.path.exists(os.path.join(d, "job.json")) and not os.path.exists(os.path.join(d, "exit.json")):
        sys.exit("job %s is already running" % name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "cmd.txt"), "w") as f:
        f.write(" ".join(cmd) + "\n")
    pid = os.fork()
    if pid == 0:
        os.setsid()
        if os.fork() != 0:
            os._exit(0)
        devnull = os.open(os.devnull, os.O_RDWR)
        for fd in (0, 1, 2):
            os.dup2(devnull, fd)
        try:
            supervise(name, wall, cmd)
        finally:
            os._exit(0)
    os.waitpid(pid, 0)
    for _ in range(50):
        if os.path.exists(os.path.join(d, "job.json")):
            break
        time.sleep(0.1)
    print(open(os.path.join(d, "job.json")).read())


def cmd_status(argv):
    names = argv if argv else (sorted(os.listdir(RUNS)) if os.path.isdir(RUNS) else [])
    for name in names:
        d = jobdir(name)
        jj = os.path.join(d, "job.json")
        if not os.path.exists(jj):
            continue
        j = json.load(open(jj))
        if os.path.exists(os.path.join(d, "exit.json")):
            e = json.load(open(os.path.join(d, "exit.json")))
            print("%-14s ENDED rc=%s wall=%ss cpu=%ss survivors=%s" % (
                name, e["returncode"], e["wall_s"], round(e["user_cpu_s"] + e["sys_cpu_s"], 1), e["survivors"]))
        else:
            alive = group_pids(j["pgid"])
            print("%-14s RUNNING pgid=%d procs=%d elapsed=%ds" % (name, j["pgid"], len(alive), time.time() - j["start"]))


def cmd_stop(argv):
    name = argv[0]
    j = json.load(open(os.path.join(jobdir(name), "job.json")))
    left = stop_group(j["pgid"])
    print("stopped group %d; survivors: %s" % (j["pgid"], left or "none"))
    if left:
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    {"start": cmd_start, "status": cmd_status, "stop": cmd_stop}[sys.argv[1]](sys.argv[2:])
