Status: complete

# Build and rollback drill report: libmseed v3.5.4 and v3.5.3

Scope: this drill works only inside drill/. Every number below comes from a command run in this run, shown next to it. Source: https://github.com/EarthScope/libmseed (Apache-2.0).

Seed corpus check (read only): `ls -1 corpus-seed/ | wc -l` -> 59 files. This matches the expected count of 59 seed records.

## E1. Environment

Command: `clang --version`
```
Apple clang version 21.0.0 (clang-2100.3.34.2)
Target: arm64-apple-darwin27.0.0
Thread model: posix
InstalledDir: /Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin
```

Command: `uname -a`
```
Darwin Mac-Studio.local 27.0.0 Darwin Kernel Version 27.0.0: Tue Aug 11 21:05:42 PDT 2026; root:xnu-13432.1.9~1/RELEASE_ARM64_T6031 arm64
```

Command: `date`
```
Sun Oct 11 02:38:08 PDT 2026
```

Command: `TZ=America/Vancouver date` (Pacific time, PT)
```
Sun Oct 11 02:38:08 PDT 2026
```

Extra, not in the numbered steps but needed later: `git --version` -> `git version 2.54.0 (Apple Git-157)`; `python3 --version` -> `Python 3.13.9`; `which lizard` -> not found (installed in step F1); `xcrun --find llvm-profdata` -> /Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/llvm-profdata; `xcrun --find llvm-cov` -> /Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/llvm-cov.

## E2. Clone the three working copies

Commands:
```
git clone --depth 1 --branch v3.5.4 https://github.com/EarthScope/libmseed.git drill/src-3.5.4-a
git clone --depth 1 --branch v3.5.4 https://github.com/EarthScope/libmseed.git drill/src-3.5.4-b
git clone --depth 1 --branch v3.5.3 https://github.com/EarthScope/libmseed.git drill/src-3.5.3
```
All three exited 0. Each clone landed in detached HEAD at the tag (git's normal behaviour for `--branch <tag>`).

Commit hash and committer date, `git -C <dir> log -1 --format='%H %cI'`:
- src-3.5.4-a: `d6e6ad306de5b7bdde072e5a5e3d58ddcc11abd8 2026-08-05T20:49:28-07:00`
- src-3.5.4-b: `d6e6ad306de5b7bdde072e5a5e3d58ddcc11abd8 2026-08-05T20:49:28-07:00`
- src-3.5.3: `2d34a80a2edd8ea8c1adc3169726fb6f8e0c2578 2026-07-30T09:15:35-07:00`

The two v3.5.4 clones have the identical commit hash, as expected for the same tag. `git describe --tags` confirms src-3.5.4-a -> `v3.5.4` and src-3.5.3 -> `v3.5.3`.

## E3. Build the static library and hash the results

Command per folder: `/usr/bin/time -p make -C <dir> static`. The project's Makefile compiles 17 .c files (see LIB_SRCS in Makefile) with `cc -fPIC -c <src> -o <obj>` and links them with `ar -crs libmseed.a <objs>`. All three builds exited 0.

Build time (`/usr/bin/time -p`, seconds):
| dir | real | user | sys |
|---|---|---|---|
| src-3.5.4-a (first build) | 4.96 | 1.39 | 0.53 |
| src-3.5.4-b (first build) | 1.91 | 1.21 | 0.44 |
| src-3.5.3 | 1.79 | 1.14 | 0.44 |

The first build was slower, most likely disk/compiler cache warm-up, not a code difference (same source, same flags).

SHA-256 of libmseed.a and each .o, command `shasum -a 256 libmseed.a *.o` run inside each folder:

src-3.5.4-a:
```
d0b7599c621cca359f3ed7a6715c1067e1a957989d463275797e1ba7269ba04d  crc32c.o
3987f0d97a6cc1da59f6afb9dd4852cf4882d3bc25d460db1632bbe8200cd195  extraheaders.o
08bd1e2da90c85dfb225f30fb9a68ef55bc77ee112e955baf99ba7701bd2e1ad  fileutils.o
a1a5491ae599f3334458a2b62646c02e7b4228e51110f6f151addc49859353b9  genutils.o
f6a619926a2861bf743c8bffe3360e50ebb8812e9dce755e9ab44008f00a45f2  gmtime64.o
af6e273a6884bcb8255244822f04eb832fe07cb471c0d496f8a87d3669e999cc  libmseed.a
3e3a577940754573921c008767a69a473e3960556a44553ae3727659eaf48218  logging.o
f1a75976f98f6b6aef10d2bf293e69661170da11c45a4411278dfcfbf0ea303a  lookup.o
2b5f3a7ddd2cc2efdb9fdd286fa00ccdc3a947d4e146cfcb7f57bb2022cffec6  msio.o
29ae3f997ec7c42dc8a1bb93e86aa73e8b2addddc60161d54ebc31faee271220  msrutils.o
23722cf43b4bc3ddca46510d5b7bd6241a4d72dfec301665dacb7781e26bd50d  pack.o
b97d9a7cf35ada4757694576443a3e3c57b003cb796ca0809d084c80c692f861  packdata.o
1b3e4083c2f9d895266a1ff62a5d82ccc8f54d3fb684c4b224febe2560555a95  parseutils.o
ba3d0513abff5dc75255b565265814ac2673584707efd02455d3324f8c05e777  selection.o
3ccd8356612f2bdb3613e0282c0657816047697699e12068a2b5550727e1d20a  tracelist.o
4b61696786f73a33dcdfc4691c4ec8d012cf19c73ab7ae4b6dd674a8ff9b82ae  unpack.o
68a69ffc8a5523d4c78418d36e02c1a0c1b03b39c2929fcd55f5ed8e0b43ce4c  unpackdata.o
fc4e59b7f1b7a532bb24c0cd45d05b421a5796ef61126405276034e68711ea52  yyjson.o
```

src-3.5.4-b: identical to src-3.5.4-a for all 17 .o files; libmseed.a hash is `fdb576eed3639289ce58e465a64034fc38c0413fea85a7bc5062d76dd24d6035` (different, see E4).

src-3.5.3 (hashes that differ from v3.5.4 reflect real source changes between releases, expected):
```
d0b7599c621cca359f3ed7a6715c1067e1a957989d463275797e1ba7269ba04d  crc32c.o
3987f0d97a6cc1da59f6afb9dd4852cf4882d3bc25d460db1632bbe8200cd195  extraheaders.o
fb8b51eb4e64ee3f6872a571c942abf20b2645c71a8351030db510617b698785  fileutils.o
a1a5491ae599f3334458a2b62646c02e7b4228e51110f6f151addc49859353b9  genutils.o
0b8a8e2c27139bc2f9ce12b7faac45e2509f3310c14ce14493a4f334e9ff10f2  gmtime64.o
d359b33fa42c9798ec9e811fc861284767eadc43eece2cdee5292cf730ecf227  libmseed.a
3e3a577940754573921c008767a69a473e3960556a44553ae3727659eaf48218  logging.o
f1a75976f98f6b6aef10d2bf293e69661170da11c45a4411278dfcfbf0ea303a  lookup.o
2b5f3a7ddd2cc2efdb9fdd286fa00ccdc3a947d4e146cfcb7f57bb2022cffec6  msio.o
2c935285d56b0b8c60ee2894fc06abe246592270694ea4b957660a948ef67300  msrutils.o
06151e2cb5b24777b3d3a78d7db8112d0581d034701b79e9fab4ff317b4efce0  pack.o
b97d9a7cf35ada4757694576443a3e3c57b003cb796ca0809d084c80c692f861  packdata.o
1b3e4083c2f9d895266a1ff62a5d82ccc8f54d3fb684c4b224febe2560555a95  parseutils.o
ba3d0513abff5dc75255b565265814ac2673584707efd02455d3324f8c05e777  selection.o
b13147e1d8d96517551601d1250808dd2d14fecdb8e3d8f811f2c73aa093bbd6  tracelist.o
4b61696786f73a33dcdfc4691c4ec8d012cf19c73ab7ae4b6dd674a8ff9b82ae  unpack.o
68a69ffc8a5523d4c78418d36e02c1a0c1b03b39c2929fcd55f5ed8e0b43ce4c  unpackdata.o
fc4e59b7f1b7a532bb24c0cd45d05b421a5796ef61126405276034e68711ea52  yyjson.o
```
(Full listings also saved as drill/_sha_src-3.5.4-a.txt, _sha_src-3.5.4-b.txt, _sha_src-3.5.3.txt.)

## E4. Compare build a and build b of v3.5.4

Command: `diff _sha_src-3.5.4-a.txt _sha_src-3.5.4-b.txt`. Result: exactly one line differs, libmseed.a. All 17 .o files are bit-for-bit identical between the two independent builds.

Cause check: `ar tv src-3.5.4-a/libmseed.a | head -5` and the same for -b both show per-member lines like `rw-r--r-- 504/600 18344 Oct 11 02:41 2026 fileutils.o`, i.e. the archive stores a modify time (and uid/gid) per member. Build a and build b ran at different wall-clock seconds, so the embedded member timestamps differ even though the member bytes (the .o files) are identical. This is the suspected cause: timestamps in the archive.

Fix test: moved the first-build libmseed.a and *.o from src-3.5.4-a and src-3.5.4-b to the system Trash, folder libmseed-drill-e4/{a_first_build,b_first_build}/ (mv, not rm), then rebuilt both with `ZERO_AR_DATE=1 /usr/bin/time -p make -C <dir> static`.

Rebuild time (seconds): src-3.5.4-a real 1.76, user 1.16, sys 0.43; src-3.5.4-b real 2.15, user 1.34, sys 0.46.

SHA-256 after the fix, both folders, all 18 files (17 .o + libmseed.a) are now identical, including the archive:
```
libmseed.a  08c12e21d73bd54d76a66c5de8f1a8e29f3fb915b0cfdf2c319d5eff612577d6   (both a and b)
```
Command `diff _sha2_src-3.5.4-a.txt _sha2_src-3.5.4-b.txt` -> exit code 0, no output, no differences.

Result: with `ZERO_AR_DATE=1` set, the v3.5.4 static-library build is fully bit-for-bit reproducible across two independent clones and builds on this machine. Without it, only the .a archive is non-reproducible (object code was always reproducible here); the object files were already reproducible even without the flag.

## E5. Run the project's own test suite

Read `test/Makefile` first (target `test all: $(EXAMPLE_BINS) $(TEST_RUNNER) runtests`, with `runtests` running `./test-runner`). Command: `/usr/bin/time -p make -C <dir> test`. The test build auto-detected `curl-config` on this machine, so it compiled with `-DLIBMSEED_URL` and linked `-lcurl`.

src-3.5.4-a: 9 example programs built, all PASSED. `[==========] Running 89 test suites.` ... `SUCCESS: 89 test suites passed in 3.29ms`. Summary block: Total test suites 89, run 89, warnings 0, skipped 0, failed 0. Wall time for the whole `make test` (build + run): real 3.90s, user 1.24s, sys 1.01s.

src-3.5.3: 9 example programs built, all PASSED. `[==========] Running 88 test suites.` ... `SUCCESS: 88 test suites passed in 38.12ms`. Summary block: Total test suites 88, run 88, warnings 0, skipped 0, failed 0. Wall time: real 5.04s, user 1.25s, sys 0.94s.

v3.5.4 has one more test suite than v3.5.3 (89 vs 88); both have zero failures. Full logs saved at drill/_test_src-3.5.4-a.log and drill/_test_src-3.5.3.log.

## E6. Behaviour check across versions

Wrote drill/decode_dump.c. It links libmseed.a, and for each file on the command line calls `msr3_parse(buffer, length, &msr, MSF_UNPACKDATA, 0)` (checked the real signature and the `MS3Record` fields in libmseed.h: `sid`, `starttime` as `nstime_t` = `int64_t` nanoseconds, `samprate` as `double`, `encoding` as `int16_t`, `samplecnt`, `numsamples`, `sampletype`, `datasamples`, `datasize`). `diff` of the struct definition and of the `msr3_parse` prototype between src-3.5.4-a/libmseed.h and src-3.5.3/libmseed.h (lines 340 to 460) showed no change, so the same decode_dump.c source is valid for both.

Per file it prints one tab separated line: file name, return code, sid, starttime (ns), samprate (%.17g), encoding, samplecnt, numsamples, sampletype, and the path of a raw dump of `msr->datasamples` (datasize bytes). The SHA-256 of that raw dump is computed afterward instead of inside the C program.

Build commands (both exit 0, no warnings):
```
cc -I src-3.5.4-a decode_dump.c src-3.5.4-a/libmseed.a -o decode_dump_354
cc -I src-3.5.3  decode_dump.c src-3.5.3/libmseed.a  -o decode_dump_353
```

Run over all 59 seed files from corpus-seed/ (read only):
```
decode_dump_354 decode_out/354 <59 seed files> > decode_354.tsv   (59 lines out)
decode_dump_353 decode_out/353 <59 seed files> > decode_353.tsv   (59 lines out)
```
One file, testdata-invalid-blockette-offsets.mseed2, fails to parse on both versions with the same return code and the same stderr message: `Error: FDSN:IU_COLA_00_L_H_Z: Blockette offset (40) is within the fixed header, impossible`, return code -1 (MS_GENERROR) on both. The other 58 files decode with return code 0 on both.

Field diff: `diff <(cut -f1-9 decode_354.tsv) <(cut -f1-9 decode_353.tsv)` -> exit 0, no output. Every field (sid, starttime, samprate, encoding, samplecnt, numsamples, sampletype) matches for all 59 files.

Decoded sample bytes diff: `shasum -a 256 *.raw` in each of decode_out/354 and decode_out/353 (58 raw files each, the 59th file produced no data), sorted and diffed -> exit 0, no output. Every decoded sample buffer hashes the same between v3.5.4 and v3.5.3.

Result: no behavioural difference found between v3.5.4 and v3.5.3 on this 59 file seed corpus, for either the parsed header fields or the decoded sample bytes.

## E7. Rollback timing

Wrote drill/rollback.sh: clones v3.5.3 into a fresh timestamped folder (so reruns never need to delete a previous one), runs `make static`, runs `make test`, then builds decode_dump.c against that clone and runs it over the 59 seed files. Each part is timed with `/usr/bin/time -p`; the whole script was also run under `/usr/bin/time -p` for the total.

Command: `/usr/bin/time -p bash drill/rollback.sh > drill/rollback_run.log 2>&1`. Exit 0. Target folder created: drill/rollback-20261011-024653.

Timing (seconds, real/user/sys from `/usr/bin/time -p`):
| part | real | user | sys |
|---|---|---|---|
| clone v3.5.3 | 48.22 | 0.07 | 0.18 |
| build (make static) | 3.70 | 1.19 | 0.52 |
| test (make test, 88/88 passed) | 2.59 | 1.21 | 0.96 |
| behaviour check run (decode_dump over 59 files) | 0.59 | 0.00 | 0.03 |
| **total (whole script)** | **55.31** | **2.57** | **1.80** |

The behaviour-check compile step (`cc ... decode_dump.c ...`) was not separately wrapped in `/usr/bin/time -p`; by subtraction (55.31 - 48.22 - 3.70 - 2.59 - 0.59 = 0.21s) it, plus the `mkdir` and shell overhead, took about 0.2 s. This 0.21 s figure is a subtraction of measured numbers, not a direct measurement.

The clone was the dominant cost (48.22 s of 55.31 s total, about 87 percent), far more than the three local clones in step E2 (a few seconds each); this run's clone speed depended on network conditions at the time, not on the repository content.

Cross-check: the rollback's decode_dump output matches the earlier src-3.5.3 build's decode_dump output. The two differed only in file-listing order (a harmless difference between two separate shell globs, confirmed by `diff <(sort ...) <(sort ...)` -> exit 0); content, including every decoded-sample-byte SHA-256, was identical.

## E8. drill.sh: rerun steps 2 to 7 with one command

Wrote drill/drill.sh. It reruns step 2 (clone x3), step 3 (build x3, hash), step 4 (compare a vs b, then test the `ZERO_AR_DATE=1` fix and compare again), step 5 (test suite on a and c), step 6 (behaviour check), and step 7 (calls rollback.sh with its own output folder). Every run goes into a fresh timestamped folder so nothing has to be deleted; the one scratch move it needs (the pre-fix libmseed.a/.o, same as E4) goes to the system Trash, never rm.

Checked syntax first: `bash -n drill.sh` -> "syntax OK". Then ran it for real, once, as its own validation: `/usr/bin/time -p bash drill.sh > drill_run.log 2>&1`. Exit 0. Output folder: drill/drillrun-20261011-025016 (folder name from the run's own timestamp, confirmed with `ls -la drill/`).

This was a second, independent end-to-end run of the whole drill, and it reproduced every earlier finding:
- Commit hashes: identical to step E2 (`d6e6ad3...` for v3.5.4, `2d34a80a...` for v3.5.3), confirming the tags are pinned.
- Step 4 first comparison (before the fix): `diff` exit 1 (a and b differ) - same as E4.
- Step 4 second comparison (after `ZERO_AR_DATE=1`): `diff` exit 0 (a and b identical) - same as E4.
- Step 5 tests: v3.5.4-a 89/89 suites passed, v3.5.3 88/88 suites passed, 0 failed, both runs - same counts as E5.
- Step 6 behaviour check: field diff v3.5.4 vs v3.5.3 exit 0, no differences - same as E6.
- Step 7 rollback via rollback.sh: exit 0, 89/89 then another 88/88 test pass inside it, behaviour check build and run both exit 0 - same as E7.

Timing from this run (seconds, `/usr/bin/time -p`):
| part | real |
|---|---|
| clone 3.5.4-a | 48.51 |
| clone 3.5.4-b | 44.08 |
| clone 3.5.3 | 42.30 |
| build 3.5.4-a (first) | 2.52 |
| build 3.5.4-b (first) | 2.38 |
| build 3.5.3 | 2.82 |
| rebuild 3.5.4-a (ZERO_AR_DATE=1) | 3.25 |
| rebuild 3.5.4-b (ZERO_AR_DATE=1) | 2.63 |
| test 3.5.4-a | 3.89 |
| test 3.5.3 | 3.89 |
| rollback.sh (step 7, clone+build+test+check) | 54.26 |
| **drill.sh total** | **212.87** |

Finding: the three independent `git clone` calls in this run took 42 to 49 seconds each, versus about 1 to 2 seconds each back in step E2 and well under a second for the rebuilds. All local steps (build, test, behaviour check) stayed fast and consistent (2 to 4 seconds each) across both full runs of the drill. The network clone time varies a lot run to run and dominates total wall time; the build, test and compare steps do not. This is the main source of variability in how long a rollback takes on this machine, not the library's own build or test speed.

## Done

Part E (this file) is complete: environment recorded, three clones built and hashed, the archive non-reproducibility found and fixed with `ZERO_AR_DATE=1`, both versions' test suites pass (89/89 for v3.5.4, 88/88 for v3.5.3), a behaviour check (drill/decode_dump.c) found no difference between v3.5.4 and v3.5.3 on the 59 file seed corpus, a timed rollback (drill/rollback.sh) ran once, and a one-command full rerun (drill/drill.sh) ran once and reproduced every earlier result.

Part F, the code metrics dossier for v3.5.4, is in drill/METRICS.md.

Scratch files kept in drill/ for traceability: _build_*.log, _sha_*.txt, _sha2_*.txt, _rebuild_*.log, _test_*.log, decode_out/, decode_*.tsv, decode_*.cols.tsv, decode_raw_sha_*.txt, rollback_run.log, drill_run.log, lizard_functions.csv, _gh_releases.json, _nvd_libmseed.json, _cov_*.log. The only discard moved out of the folder was the pre-fix libmseed.a/.o pair from step E4, moved (not deleted) to the system Trash, folder libmseed-drill-e4/.
