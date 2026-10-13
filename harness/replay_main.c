/*
 * Replay driver: feeds each file named on the command line to the harness entry once.
 * Used for coverage measurement (profile build) and for oracle triage without instrumentation.
 *
 * Copyright 2026 ParalleX Labs Inc. Licensed under the Apache License, Version 2.0.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int LLVMFuzzerInitialize (int *argc, char ***argv);
int LLVMFuzzerTestOneInput (const uint8_t *data, size_t size);

int main (int argc, char **argv)
{
  LLVMFuzzerInitialize (&argc, &argv);
  for (int i = 1; i < argc; i++)
  {
    FILE *f = fopen (argv[i], "rb");
    long n;
    uint8_t *buf;
    if (!f)
      continue;
    fseek (f, 0, SEEK_END);
    n = ftell (f);
    fseek (f, 0, SEEK_SET);
    buf = (uint8_t *)malloc (n > 0 ? (size_t)n : 1);
    if (buf && fread (buf, 1, (size_t)n, f) == (size_t)n)
    {
      if (getenv ("SW_VERBOSE"))
        fprintf (stderr, "FILE %s\n", argv[i]);
      LLVMFuzzerTestOneInput (buf, (size_t)n);
    }
    free (buf);
    fclose (f);
  }
  return 0;
}
