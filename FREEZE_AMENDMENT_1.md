# SeismicWire freeze amendment 1 (section 10 of the pre-registration)

Recorded 2026-10-11 02:24 PT, before the first fuzzing trial against libmseed. Pre-registration v1: PREREGISTRATION.md, SHA-256 7c27ecd736e7346ab1125a596d8fd81191be31ca800204417b3da5be6b402a0a (recorded 2026-10-11 02:04 PT). Nothing in it changes. This amendment fixes the code, the seeds and the implementation details below.

## 1. Frozen files (SHA-256)

Repository files:
- harness/harness.c 6ccae41c76e7e616da508b8b04e752ba47adcb3d2cd34423cd608f8633d5919b
- harness/oracle.c 1f4ba96c6694de3c51c25d676889b23857e7a1035b22aa00a62761ce1fb5313b
- harness/replay_main.c 97e5bb98ab1e83a8e09aa891818a8e3ac091ef8d13db822ea28b2cfb871302e6
- harness/ref_fuzz.c 335ac6c0d8408c61c180f1a4e17a506c4038cd4a324bbda87966767efd77ad16
- harness/ref_dump.c abea0301be8cddefc4949242ade0eadd9a350055a2f9bb013befee9de6530a2f
- ref/swref.c 4973c05618a276a3488fd52c9e859ec9317df68a4997586e5ba91e05b39608da
- ref/swref.h 0eb6784a8611422a11d5f763b92990c0dad984c95c137ca5fa22232b3c637a4b
- scripts/build.sh 72328cffe0a3de9483d676d6128246c3451c9f2026f6038111f250c4a16e3539
- scripts/run_trial.sh de9d595bff6b8ea115a8f177bdf57194af11f53ba4823b7fcd342e11f92c5e08
- scripts/pgrun.py d0913a7c44d04675b28d3414b24c882b97186d0a2a2e3043481d890b7ec2a872
- scripts/analyze.py 7733ada744cd2913373b86e3b8c6e71c9ee96afcf644a32e27982c8304fd0272
- scripts/check_fdsn_ref.py 06a21c7eb262fc896bf7bd2ee7759a16c58290961322296625def2e1a81d5351

Binaries used by the trials (built by scripts/build.sh on 2026-10-11):
- fuzz_A 937daa0a0a22c1f6be3e77ea591a5cf1eb83cb8a95b2cee774d7b4b1ee697275
- fuzz_B ce8bb47739820d0ca7b8a6551083918de0b78d1c44a553d50d4ba12149dacb0c
- replay_prof 54a8e2fcf3452d43234dd456ad5abf5ca0170ce9ff7da1aff5fe0727385f04eb
- replay_diff d8c05baeb39c62dd0e14acef8f8e9a3ea0fb5acf039b1659a9d604525fca83af
- libFuzzer.a b02e7d6c59b954520deb2146bd8de6d43931e6ee727cd684acb734c38a62ea3c

## 2. Seeds

59 files: the 46 files of libmseed 3.5.4 test/data and the 13 miniSEED 3 records of the FDSN reference data set (docs.fdsn.org/projects/miniseed3, appendix B, read 2026-10-11 between 02:10 and 02:11 PT). Manifest: results/seed-manifest.sha256, SHA-256 0e1cb10883f37e4c00d980823e79dc7a6d4d11f7e9ce29347b25e33082474e7a.

## 3. Second decoder for triage

seisplotjs 3.2.7 (MIT), installed with npm and its install scripts disabled; Node.js 20.11.0.

## 4. Smoke replay (no mutation)

Both arms ran the 59 seeds once (-runs=0): no AddressSanitizer or UndefinedBehaviorSanitizer report, so no check is disabled. Both arms load the same 54,940 coverage counters and reach the same coverage on the seeds (2,385 counters); libFuzzer reports 3,545 features for arm A and 3,548 for arm B.

## 5. Development findings (excluded from the comparison)

1. Oracle replay of the seeds: the two decoders agree on every compared field for the 57 records both accept (18,734 samples). The one disagreement is an acceptance difference: libmseed accepts testdata-no-blockette1000-steim1.mseed2, which has no blockette 1000; the reference does not. This is a documented leniency, not a defect.
2. The first replay of the 46 libmseed files showed two more differences, both in areas the specifications leave open. The reference was changed before this freeze, and both choices are marked SPEC-OPEN in ref/swref.c:
   - little-endian Steim samples are not compared, because since 2003 Steim records are big endian only (SEED 2.4, chapter 6) and the placement of 8- and 16-bit differences in a little-endian word is not specified (files reference-testdata-steim1-LE and steim2-LE had differed);
   - 128-byte records (blockette 1000 exponent 7) are accepted, although the manual says a record "can be as small as 256 bytes".
3. The reference decoder matches all 13 FDSN reference records against their published JSON values (scripts/check_fdsn_ref.py). Fuzzing the reference alone for 301 seconds (30,078,632 inputs) produced no sanitizer report.

## 6. Implementation details fixed now

- Sample rate: compared bit for bit for miniSEED 3 (the field is copied) and within a relative 1e-9 in Hz for 2.4 (the rate is computed); a negative value is read as a period.
- Values not compared where the specifications leave them open: the 2.4 payload length (appendix C gives field 17 no mapping), the identifier unless every code uses the allowed characters with a 3-character channel, the sample rate when the 2.4 multiplier is 0, and samples for encodings the reference does not decode.
- Disagreement signature: field, format version, encoding and the reference's feature bits. Signatures starting with "info." (an accepted Steim record whose last sample differs from the reverse integration constant) are reported but are not disagreements.
- Sanitizer settings: ASAN_OPTIONS detect_leaks=0:abort_on_error=0:symbolize=1; UBSAN_OPTIONS halt_on_error=1:print_stacktrace=1.
- Each trial runs under scripts/pgrun.py with a stop at 2 hours plus 600 seconds as a backstop; libFuzzer's own -max_total_time=7200 ends the trial normally.
- Coverage denominator: the 17 libmseed library sources, including code the harness never calls; the same for both arms. On the seeds alone: 3,229 of 14,589 lines (22.13%) and 1,512 of 9,703 branches (15.58%).

## 7. Exploratory addition (reported apart)

Offline replay of each arm A final corpus through the oracle (analyze.py replayA). It shows whether arm A generated inputs that expose a disagreement it could not see. It does not change the primary claim rule.

## 8. Run order

Wave 1 starts after this amendment is saved: A1, B1, A2, B2, A3 and B3 at the same time. Wave 2 (A4, B4, A5, B5) starts when wave 1 has ended. Deviations so far: none.
