/*
 * Fuzz the reference decoder alone (development hardening before the freeze).
 *
 * Copyright 2026 ParalleX Labs Inc. Licensed under the Apache License, Version 2.0.
 */
#include <stddef.h>
#include <stdint.h>

#include "swref.h"

int LLVMFuzzerTestOneInput (const uint8_t *data, size_t size)
{
  swref_record rec;
  volatile uint64_t sink = 0;
  swref_parse (data, size, &rec);
  if (rec.samples && rec.numsamples > 0)
  {
    size_t sz = rec.sampletype == 'd' ? 8 : rec.sampletype == 't' ? 1 : 4;
    const uint8_t *s = (const uint8_t *)rec.samples;
    for (size_t i = 0; i < (size_t)rec.numsamples * sz; i++)
      sink += s[i];
  }
  swref_free (&rec);
  (void)sink;
  return 0;
}
