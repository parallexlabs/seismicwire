/*
 * Print the reference decoder's reading of one file as JSON (conformance checks).
 *
 * Copyright 2026 ParalleX Labs Inc. Licensed under the Apache License, Version 2.0.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "swref.h"

int main (int argc, char **argv)
{
  FILE *f;
  long n;
  uint8_t *buf;
  swref_record r;
  if (argc < 2 || !(f = fopen (argv[1], "rb")))
    return 2;
  fseek (f, 0, SEEK_END);
  n = ftell (f);
  fseek (f, 0, SEEK_SET);
  buf = (uint8_t *)malloc ((size_t)n + 1);
  if (!buf || fread (buf, 1, (size_t)n, f) != (size_t)n)
    return 2;
  swref_parse (buf, (size_t)n, &r);
  printf ("{\"status\": %d, \"reason\": \"%s\", \"formatversion\": %d, \"reclen\": %d, \"sid\": \"%s\", "
          "\"sid_defined\": %d, \"starttime_ns\": %lld, \"samprate\": %.17g, \"encoding\": %d, \"pubversion\": %d, "
          "\"flags\": %d, \"samplecnt\": %lld, \"datalength\": %u, \"datastate\": %d, \"sampletype\": \"%c\", "
          "\"steim_xn_mismatch\": %d, \"samples\": [",
          (int)r.status, r.reason ? r.reason : "", r.formatversion, r.reclen, r.sid, r.sid_defined,
          (long long)r.starttime_ns, r.samprate, r.encoding, r.pubversion, r.flags, (long long)r.samplecnt,
          r.datalength, (int)r.datastate, r.sampletype ? r.sampletype : '0', r.steim_xn_mismatch);
  for (int64_t i = 0; i < r.numsamples && r.sampletype != 't'; i++)
  {
    if (i)
      printf (", ");
    if (r.sampletype == 'i')
      printf ("%d", ((int32_t *)r.samples)[i]);
    else if (r.sampletype == 'f')
      printf ("%.9g", ((float *)r.samples)[i]);
    else
      printf ("%.17g", ((double *)r.samples)[i]);
  }
  printf ("], \"text_len\": %lld, \"numsamples\": %lld}\n", r.sampletype == 't' ? (long long)r.numsamples : 0LL, (long long)r.numsamples);
  swref_free (&r);
  free (buf);
  fclose (f);
  return 0;
}
