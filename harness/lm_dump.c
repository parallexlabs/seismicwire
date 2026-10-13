/*
 * Print libmseed's reading of each file as one JSON line (boundary suite and triage).
 *
 * Copyright 2026 ParalleX Labs Inc. Licensed under the Apache License, Version 2.0.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "libmseed.h"

static void nolog (const char *m) { (void)m; }

int main (int argc, char **argv)
{
  ms_rloginit (nolog, NULL, nolog, NULL, 0);
  for (int a = 1; a < argc; a++)
  {
    FILE *f = fopen (argv[a], "rb");
    long n;
    char *buf;
    MS3Record *msr = NULL;
    int rv;
    if (!f)
      continue;
    fseek (f, 0, SEEK_END);
    n = ftell (f);
    fseek (f, 0, SEEK_SET);
    buf = (char *)malloc ((size_t)n + 1);
    if (!buf || fread (buf, 1, (size_t)n, f) != (size_t)n)
      return 2;
    fclose (f);
    rv = msr3_parse (buf, (uint64_t)n, &msr, MSF_UNPACKDATA, 0);
    printf ("{\"file\": \"%s\", \"rv\": %d", argv[a], rv);
    if (rv == MS_NOERROR && msr)
    {
      printf (", \"formatversion\": %d, \"reclen\": %d, \"sid\": \"%s\", \"starttime_ns\": %lld, \"samprate\": %.17g, "
              "\"encoding\": %d, \"pubversion\": %d, \"flags\": %d, \"samplecnt\": %lld, \"datalength\": %u, "
              "\"numsamples\": %lld, \"sampletype\": \"%c\", \"samples\": [",
              msr->formatversion, msr->reclen, msr->sid, (long long)msr->starttime, msr->samprate, msr->encoding,
              msr->pubversion, msr->flags, (long long)msr->samplecnt, msr->datalength, (long long)msr->numsamples,
              msr->sampletype ? msr->sampletype : '0');
      for (int64_t i = 0; i < msr->numsamples && msr->sampletype != 't'; i++)
      {
        if (i)
          printf (", ");
        if (msr->sampletype == 'i')
          printf ("%d", ((int32_t *)msr->datasamples)[i]);
        else if (msr->sampletype == 'f')
          printf ("%.9g", ((float *)msr->datasamples)[i]);
        else if (msr->sampletype == 'd')
          printf ("%.17g", ((double *)msr->datasamples)[i]);
      }
      printf ("]");
    }
    printf ("}\n");
    msr3_free (&msr);
    free (buf);
  }
  return 0;
}
