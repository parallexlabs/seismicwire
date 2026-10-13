# SeismicWire pre-registration: semantic differential testing of libmseed versus sanitizer fuzzing at equal CPU budget

Version 1. Written 2026-10-11 before any fuzzing run against libmseed. Its SHA-256 is recorded in the freeze amendment (FREEZE_AMENDMENT_1.md). No parameter below changes after a run starts; any change is a dated deviation with its reason, and a freeze amendment (section 10) adds the code hashes before the first run.

## 1. Question

At equal CPU budget, does adding an independent semantic oracle to coverage-guided fuzzing find defects in libmseed's record decoding that sanitizer-only fuzzing does not find? The oracle is a reference decoder written from the format specifications and compared with libmseed field by field and sample by sample.

## 2. Target and tools (pinned)

- Target: libmseed 3.5.4, the release of 2026-08-06, commit d6e6ad306de5b7bdde072e5a5e3d58ddcc11abd8 (github.com/EarthScope/libmseed, Apache-2.0). Unchanged source; built by script.
- Fuzzing engine: libFuzzer from LLVM 23.1.3 (tag llvmorg-23.1.3, commit 0d261d1ca552c95a8f007e061c787ac7132fbcbc), compiled with the system compiler.
- Compiler: Apple clang 21.0.0 (clang-2100.3.34.2), arm64-apple-darwin27.0.0. Machine: 28 cores and 96 GB memory, shared with other work.
- Sanitizers in both arms: AddressSanitizer and UndefinedBehaviorSanitizer (-fsanitize=address,undefined), -O1 -g, coverage flags inline-8bit-counters, pc-table and trace-cmp. Leak detection off in both arms. A UBSan report stops the input like a crash.
- Specifications used by the reference decoder: SEED Reference Manual version 2.4 (FDSN), chapter 3 (BTIME), chapter 8 (fixed section of data header, blockettes 100, 1000 and 1001) and appendix B (Steim1 and Steim2); FDSN miniSEED 3 (docs.fdsn.org/projects/miniseed3), record definition, data encodings and appendix C (mapping from miniSEED 2.4).
- Second independent decoder for triage only: seisplotjs (github.com/crotwell/seisplotjs, MIT), pinned by version in the freeze amendment.

## 3. Harness (same entry in both arms)

Each input is one byte buffer. The harness calls msr3_parse(buffer, length, &record, MSF_UNPACKDATA, 0) with CRC validation off, reads every decoded sample, and frees the record. libmseed logging is silenced.

## 4. Arms

- Arm A (baseline): the harness alone. Oracle: sanitizer reports, crashes, timeouts over 10 seconds and memory over 2,048 MB.
- Arm B (SeismicWire): the same harness, plus the reference decoder run in the same process on the same buffer. When both decoders accept the record, these values are compared: format version, source identifier, start time in nanoseconds, sample rate, encoding, publication version, record flags, sample count, record length, payload length, sample type, and every decoded sample (exact integer equality; bitwise equality for floats). When one accepts and the other rejects, that is logged as an acceptance difference. A disagreement is logged with its field signature and the first 20 inputs per signature are saved; the run continues. Oracle: everything in arm A plus these disagreements.
- The arms differ only in the oracle: same engine, sanitizers, harness entry, flags, seeds and budget. Arm B pays for its oracle in fewer executions per second; that cost is part of the comparison.

## 5. Budget and runs

- Five trials per arm, libFuzzer seeds 1 to 5. Each trial runs 2 hours of wall time with one fuzzing child process (-fork=1), continuing past crashes, timeouts and memory limits (-ignore_crashes=1, -ignore_timeouts=1, -ignore_ooms=1), -max_len=16384, -timeout=10, -rss_limit_mb=2048, no dictionary.
- CPU time of every trial (parent and children) is measured and reported. If the CPU time of any trial differs by more than 10% from the arm A median, the report says so.
- At most six trials run at once, in pairs started together so each pair shares machine conditions: A1 with B1, A2 with B2 and A3 with B3, then A4 with B4 and A5 with B5. Total: 20 CPU-hours.
- Seed corpus, identical for every trial: the 46 files of libmseed 3.5.4 test/data, plus the FDSN miniSEED 3 reference records if they are downloaded before the freeze. Each trial starts from its own copy.
- Every job runs in its own process group and is stopped by group, with a check that no child survives.

## 6. Outcomes

Primary: distinct confirmed libmseed defects per arm, as the union over the five trials, and the number of trials that found each one. A defect is confirmed only by the triage of section 7 and counted once per root cause (the code a fix would change).

Primary claim rule: the release may say that SeismicWire found defects that sanitizer fuzzing did not find at equal budget only if at least one confirmed defect was found by at least one arm B trial and by none of the five arm A trials. It then states the counts (for example, found in 4 of 5 B trials and 0 of 5 A trials).

Secondary:
- time to first finding for each confirmed defect (trials that did not find it are censored at 2 hours);
- line and branch coverage of libmseed: each trial's final corpus replayed through a profile-instrumented build of the same commit, measured with llvm-cov; median and range per arm; Mann-Whitney U (two-sided) and the Vargha and Delaney A12 effect size (Journal of Educational and Behavioral Statistics 25(2):101 to 132, 2000, doi 10.3102/10769986025002101), reported as descriptive at five trials per arm;
- executions per second per arm;
- oracle false-alarm rate: the share of arm B disagreement signatures that triage assigns to the reference decoder, the harness or a specification ambiguity.

Clean-result rule: if no arm finds a confirmed defect, the release says "no defect found in 20 CPU-hours under these conditions", reports coverage and execution rates, and makes no breakthrough claim.

## 7. Triage (blinded to the arm)

- All crash stacks and disagreement signatures from both arms are pooled. Arm labels are replaced by random IDs until every candidate is classified; then the key is opened.
- For each candidate: a minimized input (libFuzzer minimization for crashes; a delta-debugging script that keeps the same signature for disagreements), a reproduction on a build without instrumentation, the specification clause (SEED 2.4 page or miniSEED 3 section), and the second decoder's output where it supports the feature.
- Categories: libmseed defect; reference decoder defect; specification ambiguity; documented libmseed leniency (it accepts input the specification forbids but reports correct values); harness artefact. Only "libmseed defect" counts.
- Severity, reported beside each defect: wrong values returned without an error; crash or memory error; undefined behaviour without visible effect; valid record rejected.

## 8. Disclosure

Confirmed defects go privately to the libmseed maintainers before any public release. The public release shows the method, the harness, aggregate counts and fixed issues only, with no details of an unfixed defect.

## 9. Exploratory work (reported apart, not part of the comparison)

- C: arm B with a structure-aware mutator that keeps length fields and the miniSEED 3 CRC consistent, five trials of 2 hours if CPU allows.
- D: a deterministic boundary suite derived from the specifications (leap seconds, day 366, sample rate factor and multiplier signs, blockette 100 rates, blockette 1001 microseconds, time correction with and without the applied flag, every Steim nibble type, frame boundaries, byte orders), run through libmseed, the reference and seisplotjs.
- E: a build and rollback drill: libmseed 3.5.4 built twice in clean folders with artefact hashes compared, the test suite run, a rollback to the previous release and a rerun, with times and differences recorded.
- F: a code metrics dossier for the same commit.

## 10. Freeze amendment (before the first run)

Before the first trial: the SHA-256 of every harness, the reference decoder, the runner and the analysis script; the seed corpus manifest with hashes; the seisplotjs version; and the outcome of the smoke replay. Before the freeze, harnesses are only compiled and replayed on the seed corpus without mutation, and the reference decoder may be fuzzed on its own to harden it. Any libmseed finding from that development work is listed as a development finding and is excluded from the comparison. If the seed replay triggers a UBSan report, that check is listed as a development finding and disabled in both arms with -fno-sanitize, named in the freeze amendment.

## 11. Limitations stated in advance

- Two-hour trials are short; Klees and others recommend much longer runs and repeated trials (Evaluating Fuzz Testing, ACM CCS 2018, pages 2123 to 2138, doi 10.1145/3243734.3243804). Five trials per arm give low power for coverage tests.
- The reference decoder and the experiment come from the same team. Blinded triage and the second decoder reduce, but do not remove, that bias.
- One platform (macOS arm64) and one library version.
- Differential testing guided by fuzzing is established (for example NEZHA, IEEE Symposium on Security and Privacy 2017, pages 615 to 632, doi 10.1109/SP.2017.27). The new part is its application to seismic record formats with an oracle written from the FDSN specifications; on 2026-10-11 no published study (OpenAlex) or public repository (GitHub repository search) of fuzzing or differential testing of miniSEED decoders was found, and libmseed has no OSS-Fuzz project.
