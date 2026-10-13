#!/bin/sh
# Build every SeismicWire binary from pinned sources.
#   LIBMSEED_SRC  libmseed 3.5.4 source folder (commit d6e6ad306de5b7bdde072e5a5e3d58ddcc11abd8)
#   LIBFUZZER     libFuzzer.a built from LLVM 23.1.3 compiler-rt/lib/fuzzer
#   OUT           output folder
# Binaries:
#   fuzz_A        arm A: harness, libmseed with ASan + UBSan + coverage
#   fuzz_B        arm B: the same, plus the oracle and reference decoder (sanitizers, no coverage)
#   replay_prof   corpus replay for line and branch coverage (profile build, no sanitizers)
#   replay_diff   oracle replay of given files without instrumentation (triage)
#   ref_fuzz      the reference decoder fuzzed alone (development hardening only)
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)
LIBMSEED_SRC=${LIBMSEED_SRC:-$HERE/../libmseed-3.5.4}
LIBFUZZER=${LIBFUZZER:-$HERE/../build/libFuzzer.a}
OUT=${OUT:-$HERE/../build/bin}
CC=${CC:-clang}
SRCS="fileutils.c genutils.c msio.c lookup.c yyjson.c msrutils.c extraheaders.c pack.c packdata.c
tracelist.c gmtime64.c crc32c.c parseutils.c unpack.c unpackdata.c selection.c logging.c"

BASE="-g -O1 -fno-omit-frame-pointer"
SAN="-fsanitize=address,undefined ${SW_NO_SANITIZE:+-fno-sanitize=$SW_NO_SANITIZE}"
COV="-fsanitize-coverage=inline-8bit-counters,pc-table,trace-cmp"
PROF="-fprofile-instr-generate -fcoverage-mapping"

mkdir -p "$OUT"
TMP="$OUT/../objs"
mkdir -p "$TMP"

lib () { # name flags
  mkdir -p "$TMP/$1"
  for f in $SRCS; do
    $CC $2 -I"$LIBMSEED_SRC" -c "$LIBMSEED_SRC/$f" -o "$TMP/$1/${f%.c}.o" &
  done
  wait
  ar rcs "$TMP/$1.a" "$TMP/$1"/*.o
}

lib fuzz "$BASE $SAN $COV"
lib prof "$BASE $PROF"
lib plain "-g -O2"

INC="-I$LIBMSEED_SRC -I$HERE/ref"
$CC $BASE $SAN $COV $INC -c "$HERE/harness/harness.c" -o "$TMP/harness_A.o"
$CC $BASE $SAN $COV $INC -DSW_ORACLE -c "$HERE/harness/harness.c" -o "$TMP/harness_B.o"
$CC $BASE $SAN $INC -c "$HERE/harness/oracle.c" -o "$TMP/oracle_san.o"
$CC $BASE $SAN $INC -c "$HERE/ref/swref.c" -o "$TMP/swref_san.o"

$CC $BASE $SAN $COV "$TMP/harness_A.o" "$TMP/fuzz.a" "$LIBFUZZER" -lc++ -o "$OUT/fuzz_A"
$CC $BASE $SAN $COV "$TMP/harness_B.o" "$TMP/oracle_san.o" "$TMP/swref_san.o" "$TMP/fuzz.a" "$LIBFUZZER" -lc++ -o "$OUT/fuzz_B"

# replay drivers: a plain main() that feeds each file to the same harness entry
$CC $BASE $PROF $INC "$HERE/harness/harness.c" "$HERE/harness/replay_main.c" "$TMP/prof.a" -o "$OUT/replay_prof"
$CC -g -O2 $INC -DSW_ORACLE "$HERE/harness/harness.c" "$HERE/harness/replay_main.c" "$HERE/harness/oracle.c" \
  "$HERE/ref/swref.c" "$TMP/plain.a" -o "$OUT/replay_diff"

# the reference alone, for hardening before the freeze
$CC $BASE $SAN $COV $INC "$HERE/harness/ref_fuzz.c" "$HERE/ref/swref.c" "$LIBFUZZER" -lc++ -o "$OUT/ref_fuzz"

shasum -a 256 "$OUT"/fuzz_A "$OUT"/fuzz_B "$OUT"/replay_prof "$OUT"/replay_diff "$OUT"/ref_fuzz
