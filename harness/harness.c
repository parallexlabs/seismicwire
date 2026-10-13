/*
 * SeismicWire fuzzing harness: one entry point for both arms.
 * Arm A (baseline) is this file alone. Arm B adds -DSW_ORACLE and links oracle.c, which is
 * compiled without coverage instrumentation, so both arms are guided by the same coverage.
 *
 * Copyright 2026 ParalleX Labs Inc. Licensed under the Apache License, Version 2.0.
 */
#include <stddef.h>
#include <stdint.h>

#include "libmseed.h"

#ifdef SW_ORACLE
void sw_oracle_init (void);
void sw_oracle_check (const uint8_t *data, size_t size, int rv, const MS3Record *msr);
#endif

static void sw_nolog (const char *msg) { (void)msg; }

int LLVMFuzzerInitialize (int *argc, char ***argv)
{
  (void)argc;
  (void)argv;
  ms_rloginit (sw_nolog, NULL, sw_nolog, NULL, 0);
#ifdef SW_ORACLE
  sw_oracle_init ();
#endif
  return 0;
}

int LLVMFuzzerTestOneInput (const uint8_t *data, size_t size)
{
  MS3Record *msr = NULL;
  volatile uint64_t sink = 0;
  int rv = msr3_parse ((const char *)data, (uint64_t)size, &msr, MSF_UNPACKDATA, 0);

  if (rv == MS_NOERROR && msr && msr->datasamples && msr->numsamples > 0)
  {
    const uint8_t *s = (const uint8_t *)msr->datasamples;
    uint64_t n = (uint64_t)msr->numsamples * (uint64_t)ms_samplesize (msr->sampletype);
    for (uint64_t i = 0; i < n; i++)
      sink += s[i];
  }
#ifdef SW_ORACLE
  sw_oracle_check (data, size, rv, msr);
#endif
  msr3_free (&msr);
  (void)sink;
  return 0;
}
