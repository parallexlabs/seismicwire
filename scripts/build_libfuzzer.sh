#!/bin/sh
# Build libFuzzer.a from LLVM 23.1.3 compiler-rt/lib/fuzzer.
#   FUZZER_SRC  folder holding compiler-rt/lib/fuzzer (LLVM 23.1.3)
#   OUT         output folder (libFuzzer.a and the objects)
# Added after the trials to document the build. The flags of the original build were not
# recorded; these give objects of nearly the same size, but the archive's SHA-256 differs from
# the frozen libFuzzer.a (FREEZE_AMENDMENT_1.md section 1) because debug information embeds paths.
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)
FUZZER_SRC=${FUZZER_SRC:-$HERE/../llvm-fuzzer}
OUT=${OUT:-$HERE/../build}
mkdir -p "$OUT/fuzzer-obj"
for f in "$FUZZER_SRC"/compiler-rt/lib/fuzzer/Fuzzer*.cpp; do
  b=$(basename "$f" .cpp)
  ${CXX:-clang++} -c -g -O2 -std=c++17 "$f" -o "$OUT/fuzzer-obj/$b.o"
done
rm -f "$OUT/libFuzzer.a"
ar rcs "$OUT/libFuzzer.a" "$OUT"/fuzzer-obj/Fuzzer*.o
echo "built $OUT/libFuzzer.a"
