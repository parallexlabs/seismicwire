#!/bin/sh
# Start one pre-registered trial in its own process group (pgrun.py).
#   run_trial.sh ARM SEED       ARM is A or B; SEED is the libFuzzer seed (1 to 5)
# Environment: SW_ROOT (default: the folder above this repository), SW_HOURS (default 2).
# Layout: $SW_ROOT/runs/<ARM><SEED>/ with corpus/, artifacts/, findings/ (arm B) and the
# pgrun files (cmd.txt, job.json, job.log, exit.json).
set -eu
ARM=$1
SEED=$2
HERE=$(cd "$(dirname "$0")/.." && pwd)
SW_ROOT=${SW_ROOT:-$(cd "$HERE/.." && pwd)}
HOURS=${SW_HOURS:-2}
SECS=$(python3 -c "print(int(float('$HOURS') * 3600))")
NAME="$ARM$SEED"
RUN="$SW_ROOT/runs/$NAME"
BIN="$SW_ROOT/build/bin/fuzz_$ARM"

case "$ARM" in A|B) ;; *) echo "arm must be A or B" >&2; exit 2 ;; esac
[ -x "$BIN" ] || { echo "missing $BIN" >&2; exit 2; }
[ -e "$RUN/job.json" ] && { echo "$NAME already started" >&2; exit 2; }

mkdir -p "$RUN/corpus" "$RUN/artifacts" "$RUN/findings"
cp "$SW_ROOT"/corpus-seed/* "$RUN/corpus/"

export ASAN_OPTIONS="detect_leaks=0:abort_on_error=0:symbolize=1"
export UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1"
export SW_FINDINGS="$RUN/findings"
export SW_RUNS="$SW_ROOT/runs"

python3 "$HERE/scripts/pgrun.py" start "$NAME" --wall $((SECS + 600)) -- "$BIN" \
  -fork=1 -ignore_crashes=1 -ignore_timeouts=1 -ignore_ooms=1 \
  -max_total_time="$SECS" -seed="$SEED" -max_len=16384 -timeout=10 -rss_limit_mb=2048 \
  -print_final_stats=1 -artifact_prefix="$RUN/artifacts/" "$RUN/corpus"
