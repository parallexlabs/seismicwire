# Code metrics dossier: libmseed v3.5.4

Source: https://github.com/EarthScope/libmseed, tag v3.5.4, commit d6e6ad306de5b7bdde072e5a5e3d58ddcc11abd8 (see drill/DRILL_REPORT.md step E2). Working copy: drill/src-3.5.4-a unless noted. Every number below has its command next to it. "Library folder" means the top-level source folder (C sources and headers that the project's own Makefile builds into libmseed.a), not test/ or example/.

## F1. Size: files and lines of code

Commands: `wc -l *.c *.h` run inside drill/src-3.5.4-a (top level only); lizard NLOC from `python3 -m lizard <file>` (lizard 1.24.1, installed with `python3 -m pip install --user lizard`, see F2).

| file | wc -l | lizard NLOC | note |
|---|---:|---:|---|
| crc32c.c | 410 | 342 | |
| extraheaders.c | 1466 | 991 | |
| extraheaders.h | 50 | 12 | |
| fileutils.c | 1334 | 683 | |
| genutils.c | 2261 | 1353 | |
| gmtime64.c | 124 | 57 | |
| gmtime64.h | 22 | 4 | |
| internalstate.h | 147 | 68 | |
| libmseed.h | 1648 | 535 | |
| logging.c | 715 | 348 | |
| lookup.c | 239 | 169 | |
| mseedformat.h | 661 | 58 | |
| msio.c | 950 | 574 | |
| msio.h | 45 | 13 | |
| msrutils.c | 438 | 225 | |
| pack.c | 2632 | 1707 | |
| packdata.c | 719 | 391 | |
| packdata.h | 55 | 19 | |
| parseutils.c | 1457 | 1101 | |
| selection.c | 1049 | 643 | |
| tracelist.c | 4154 | 2432 | |
| unpack.c | 1862 | 1290 | |
| unpack.h | 44 | 11 | |
| unpackdata.c | 960 | 545 | |
| unpackdata.h | 59 | 26 | |
| yyjson.c | 11065 | 7654 | vendored third-party (see F2) |
| yyjson.h | 8230 | 3614 | vendored third-party (see F2) |

Totals: `wc -l *.c | tail -1` -> 31835 lines across 17 .c files. `wc -l *.h | tail -1` -> 10961 lines across 10 .h files. Combined: 42796 lines (27 files). Lizard's own total NLOC across the same 27 files (`python3 -m lizard *.c *.h`, final summary line): 24865.

Excluding the vendored yyjson.c and yyjson.h (see F2): 23501 lines by `wc -l` (42796 - 11065 - 8230), 13597 lines of lizard NLOC (24865 - 7654 - 3614), across 25 files.

## F2. Complexity (lizard)

Installed with `python3 -m pip install --user lizard`; version check `python3 -m lizard --version` -> 1.24.1. Ran `python3 -m lizard *.c *.h --csv` inside drill/src-3.5.4-a for per-function data (814 rows) and cross-checked against the plain-text summary from `python3 -m lizard *.c *.h`.

yyjson.c (and its header yyjson.h) is vendored third-party code (the yyjson JSON library), not code written for libmseed, so it is split out below.

Whole library, all 27 files (including vendored yyjson):
- Functions: 814
- Average cyclomatic complexity (CCN): 7.55
- Maximum CCN: 223, in pack.c

Library's own code only, 25 files (excluding yyjson.c and yyjson.h):
- Functions: 237
- Average CCN: 14.08
- Maximum CCN: 223, in pack.c

Vendored yyjson.c + yyjson.h only, for comparison:
- Functions: 577
- Average CCN: 4.86
- Maximum CCN: 137, in yyjson.c

Ten functions with the highest cyclomatic complexity, whole library (file, CCN, NLOC; function names are left out of this public copy), from the `--csv` run sorted on the CCN column; "(vendored)" marks yyjson.c:

| rank | file | CCN | NLOC |
|---:|---|---:|---:|
| 1 | pack.c | 223 | 681 |
| 2 | parseutils.c | 198 | 794 |
| 3 | yyjson.c (vendored) | 137 | 368 |
| 4 | unpack.c | 134 | 618 |
| 5 | tracelist.c | 121 | 372 |
| 6 | yyjson.c (vendored) | 118 | 334 |
| 7 | yyjson.c (vendored) | 97 | 378 |
| 8 | genutils.c | 95 | 187 |
| 9 | yyjson.c (vendored) | 91 | 344 |
| 10 | yyjson.c (vendored) | 83 | 211 |

Same ranking restricted to the library's own code (excluding yyjson):

| rank | file | CCN | NLOC |
|---:|---|---:|---:|
| 1 | pack.c | 223 | 681 |
| 2 | parseutils.c | 198 | 794 |
| 3 | unpack.c | 134 | 618 |
| 4 | tracelist.c | 121 | 372 |
| 5 | genutils.c | 95 | 187 |
| 6 | unpack.c | 73 | 171 |
| 7 | fileutils.c | 68 | 280 |
| 8 | packdata.c | 66 | 178 |
| 9 | selection.c | 65 | 211 |
| 10 | msio.c | 64 | 212 |

## F3. Test coverage of the project's own test suite

Built a fresh clone (drill/src-3.5.4-cov, tag v3.5.4) with Clang source-based coverage:
```
CFLAGS="-fprofile-instr-generate -fcoverage-mapping" make -C src-3.5.4-cov static
LLVM_PROFILE_FILE=drill/coverage/test-runner.profraw CFLAGS="-fprofile-instr-generate -fcoverage-mapping" make -C src-3.5.4-cov test
```
Both exited 0; the instrumented test-runner passed all 89 of 89 test suites (same result as the uninstrumented build in DRILL_REPORT.md step E5), and running it produced drill/coverage/test-runner.profraw (197656 bytes).

```
xcrun llvm-profdata merge -sparse test-runner.profraw -o test-runner.profdata
xcrun llvm-cov report ./test/test-runner -instr-profile=test-runner.profdata --show-branch-summary
xcrun llvm-cov export ./test/test-runner -instr-profile=test-runner.profdata > export.json
```
All three exited 0. `llvm-cov report` needed `--show-branch-summary` to print a Branches column at all (found via `xcrun llvm-cov report --help`); passing a list of library file names as extra arguments to `report` did not filter it (llvm-cov printed a "Source file doesn't exist" warning and returned the unfiltered, whole-binary report instead), so the library-only figures below were computed by summing the per-file `summary` blocks in the `export.json` output (the `export` subcommand's machine-readable format) for exactly the library's own file names. As a check, summing `export.json` over all 39 files it lists reproduced the `report` command's own TOTAL row exactly (lines 50.33%, functions 56.09%, regions 38.87%, branches 28.20%), so the per-file summing method is trustworthy.

Library .c + .h files only (23 of the 27 files in F1 appear in the coverage data; the other 4, gmtime64.h/msio.h/unpack.h/unpackdata.h, have no function bodies for llvm-cov to instrument, so they are not in the coverage mapping at all):

| scope | lines covered/total | line % | branches covered/total | branch % | functions covered/total | function % |
|---|---:|---:|---:|---:|---:|---:|
| Library .c + .h, including vendored yyjson | 8582 / 20234 | 42.41% | 4025 / 12889 | 31.23% | 369 / 801 | 46.07% |
| Library's own code only (excl. yyjson.c/.h) | 6109 / 11418 | 53.50% | 3121 / 6733 | 46.35% | 182 / 229 | 79.48% |
| Vendored yyjson.c + yyjson.h only | 2473 / 8816 | 28.05% | 904 / 6156 | 14.68% | 187 / 572 | 32.69% |

Line and branch coverage: with yyjson included, 42.41% line coverage and 31.23% branch coverage. Looking at the library's own code only (the more meaningful figure, since yyjson is vendored and mostly exercised through a handful of extra-headers tests rather than directly), line coverage is 53.50% and branch coverage is 46.35%. Nothing blocked this measurement; the only snag was the `report` command's source-file filter not working as expected, worked around with `export` plus a Python sum, both logged above.

## F4. Release history

API: `curl -H "User-Agent: ..." -H "Accept: application/vnd.github+json" "https://api.github.com/repos/EarthScope/libmseed/releases?per_page=15"` -> HTTP_STATUS:200 (1 of at most 5 reads of api.github.com planned for this work). Saved as drill/_gh_releases.json.

Last 10 releases (tag, published_at UTC, from the JSON, newest first as returned by the API):
| tag | published (UTC) |
|---|---|
| v3.5.4 | 2026-08-06T03:50:39Z |
| v3.5.3 | 2026-07-30T16:19:09Z |
| v3.5.2 | 2026-07-28T02:42:11Z |
| v3.5.1 | 2026-07-25T20:51:22Z |
| v2.19.9 | 2026-07-25T20:47:39Z |
| v3.5.0 | 2026-07-24T22:55:10Z |
| v3.4.1 | 2026-06-17T02:02:00Z |
| v3.4.0 | 2026-04-04T22:11:11Z |
| v3.3.0 | 2026-03-29T19:57:51Z |
| v3.2.4 | 2026-01-24T23:28:00Z |

Gaps between consecutive releases, computed with Python `datetime` from the same JSON (newest-to-oldest, in days): 6.48, 2.57, 2.24, 0.00, 0.91, 37.87, 73.16, 6.09, 63.85.

Median gap (Python `statistics.median` over the 9 gaps above): **6.09 days**.

Note: v2.19.9 was released in between v3.5.1 and v3.5.0, a few minutes apart, because EarthScope maintains a 2.x branch alongside 3.x; it is included because it is one of the 10 most recently published releases by date, as asked.

## F5. Known vulnerabilities

API: `curl -H "User-Agent: ..." "https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=libmseed"` -> HTTP_STATUS:200 (1 of at most 3 reads of the NVD API planned for this work; no second read was needed, so no 6 second wait was needed either). Saved as drill/_nvd_libmseed.json. Response body: `"resultsPerPage": 0, "startIndex": 0, "totalResults": 0, "vulnerabilities": []`, with the NVD server's own response timestamp `2026-10-11T09:59:06.781` (UTC), i.e. 2026-10-11 02:59 PT.

Result: none found in NVD on 2026-10-11.

## F6. Dependencies beyond the C standard library

From the top-level Makefile: building `libmseed.a` itself (`ar -crs libmseed.a <objects>`) does not link anything, so the static library has no linked dependencies at all.

The Makefile adds one optional dependency when `curl-config` is present on the build machine: if `LIBMSEED_URL` is in CFLAGS and `command -v curl-config` succeeds, it exports `-DLIBMSEED_URL` and appends `curl-config --libs` to LDLIBS/LDFLAGS (top-level Makefile lines 49-55; test/Makefile lines 11-16 do the same for the test build). `curl-config --version` on this machine -> `libcurl 8.7.1`; `curl-config --libs` -> `-lcurl`.

`otool -L` on the built test runner, both versions:
```
drill/src-3.5.4-a/test/test-runner:
	/usr/lib/libcurl.4.dylib (compatibility version 7.0.0, current version 9.0.0)
	/usr/lib/libSystem.B.dylib (compatibility version 1.0.0, current version 1359.0.0)
drill/src-3.5.3/test/test-runner:
	/usr/lib/libcurl.4.dylib (compatibility version 7.0.0, current version 9.0.0)
	/usr/lib/libSystem.B.dylib (compatibility version 1.0.0, current version 1359.0.0)
```

So, beyond the C standard library (libSystem on macOS): **libcurl**, and only because this build machine happens to have `curl-config`/libcurl installed; the Makefile treats it as optional and the library itself does not require it to build or to work (without curl-config, the Makefile skips `-DLIBMSEED_URL` and libcurl entirely, and only the URL-reading convenience feature is left out).
