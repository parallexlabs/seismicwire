/*
 * SeismicWire semantic oracle (arm B): decode the same buffer with the reference decoder and
 * compare it with libmseed. Compiled without coverage instrumentation (see harness.c).
 *
 * Each disagreement gets a signature: the field, the format version, the encoding and the
 * reference's feature bits. The first 20 inputs per signature are saved under SW_FINDINGS
 * (default ./findings) with one line each in signatures.tsv; counts per process go to
 * counts-<pid>.tsv at exit. The run continues after a disagreement.
 *
 * Copyright 2026 ParalleX Labs Inc. Licensed under the Apache License, Version 2.0.
 */
#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#include "libmseed.h"
#include "swref.h"

#define SAVE_PER_SIG 20
#define TABLE 4096

static char g_dir[1024] = "findings";
static struct { char sig[160]; uint64_t n; } g_tab[TABLE];
static uint64_t g_checked, g_both_ok, g_compared_samples;
static int g_verbose;

static void flush_counts (void)
{
  char path[1200];
  FILE *f;
  snprintf (path, sizeof (path), "%s/counts-%d.tsv", g_dir, (int)getpid ());
  f = fopen (path, "w");
  if (!f)
    return;
  fprintf (f, "_inputs\t%llu\n_both_accepted\t%llu\n_samples_compared\t%llu\n", (unsigned long long)g_checked,
           (unsigned long long)g_both_ok, (unsigned long long)g_compared_samples);
  for (int i = 0; i < TABLE; i++)
    if (g_tab[i].n)
      fprintf (f, "%s\t%llu\n", g_tab[i].sig, (unsigned long long)g_tab[i].n);
  fclose (f);
}

void sw_oracle_init (void)
{
  const char *d = getenv ("SW_FINDINGS");
  if (d && *d)
    snprintf (g_dir, sizeof (g_dir), "%s", d);
  mkdir (g_dir, 0755);
  g_verbose = getenv ("SW_VERBOSE") != NULL;
  atexit (flush_counts);
}

static uint64_t fnv (const char *s)
{
  uint64_t h = 1469598103934665603ull;
  for (; *s; s++)
    h = (h ^ (uint8_t)*s) * 1099511628211ull;
  return h;
}

/* Returns the new count for this signature (1 on first sight in this process). */
static uint64_t count_sig (const char *sig)
{
  uint64_t h = fnv (sig);
  for (int i = 0; i < TABLE; i++)
  {
    int k = (int)((h + (uint64_t)i) % TABLE);
    if (!g_tab[k].n)
    {
      snprintf (g_tab[k].sig, sizeof (g_tab[k].sig), "%s", sig);
      g_tab[k].n = 1;
      return 1;
    }
    if (!strcmp (g_tab[k].sig, sig))
      return ++g_tab[k].n;
  }
  return 2; /* table full: count nothing new, save nothing */
}

static void save_input (const char *sig, const uint8_t *data, size_t size, const char *detail)
{
  char safe[160], path[1400];
  size_t j = 0;
  for (const char *p = sig; *p && j + 1 < sizeof (safe); p++)
    safe[j++] = ((*p >= 'A' && *p <= 'Z') || (*p >= 'a' && *p <= 'z') || (*p >= '0' && *p <= '9') || *p == '-' || *p == '.') ? *p : '_';
  safe[j] = 0;
  for (int n = 0; n < SAVE_PER_SIG; n++)
  {
    int fd;
    snprintf (path, sizeof (path), "%s/%s__%02d.bin", g_dir, safe, n);
    fd = open (path, O_WRONLY | O_CREAT | O_EXCL, 0644);
    if (fd < 0)
    {
      if (errno == EEXIST)
        continue;
      return;
    }
    if (write (fd, data, size) != (ssize_t)size) { /* best effort */ }
    close (fd);
    snprintf (path, sizeof (path), "%s/signatures.tsv", g_dir);
    FILE *f = fopen (path, "a");
    if (f)
    {
      fprintf (f, "%ld\t%d\t%s\t%s__%02d.bin\t%zu\t%s\n", (long)time (NULL), (int)getpid (), sig, safe, n, size, detail);
      fclose (f);
    }
    return;
  }
}

static void report (const char *field, const swref_record *ref, const uint8_t *data, size_t size, const char *detail)
{
  char sig[160];
  snprintf (sig, sizeof (sig), "%s.v%d.e%d.f%02x", field, ref->formatversion, ref->encoding, ref->features);
  if (g_verbose)
    fprintf (stderr, "DIFF %s %s\n", sig, detail);
  if (count_sig (sig) == 1)
    save_input (sig, data, size, detail);
}

/* Sample rate in Hz from either representation (positive rate or negative period). */
static double hz (double v) { return v > 0 ? v : (v < 0 ? -1.0 / v : 0.0); }

static int same_rate (double a, double b, int v3)
{
  if (v3)
    return memcmp (&a, &b, sizeof (double)) == 0; /* miniSEED 3 field 6 is copied, not computed */
  if (isnan (a) || isnan (b))
    return isnan (a) && isnan (b);
  double x = hz (a), y = hz (b);
  double m = fabs (x) > fabs (y) ? fabs (x) : fabs (y);
  return fabs (x - y) <= 1e-9 * m;
}

void sw_oracle_check (const uint8_t *data, size_t size, int rv, const MS3Record *msr)
{
  swref_record ref;
  char d[256];
  int lm_ok = (rv == MS_NOERROR && msr != NULL);
  int ref_ok;

  g_checked++;
  swref_parse (data, size, &ref);
  ref_ok = (ref.status == SWREF_OK);

  if (lm_ok != ref_ok)
  {
    char field[96];
    /* acceptance differences: separate signatures by who rejected and why */
    if (lm_ok)
      snprintf (field, sizeof (field), "accept.lm-only.%s", ref.reason ? ref.reason : "?");
    else
      snprintf (field, sizeof (field), "accept.ref-only.rv%d", rv);
    for (char *p = field; *p; p++)
      if (*p == ' ')
        *p = '-';
    snprintf (d, sizeof (d), "rv=%d ref=%d", rv, (int)ref.status);
    report (field, &ref, data, size, d);
    swref_free (&ref);
    return;
  }
  if (!lm_ok)
  {
    swref_free (&ref);
    return;
  }
  g_both_ok++;

  if (msr->formatversion != ref.formatversion)
  { snprintf (d, sizeof (d), "lm=%d ref=%d", msr->formatversion, ref.formatversion); report ("formatversion", &ref, data, size, d); }
  if (msr->reclen != ref.reclen)
  { snprintf (d, sizeof (d), "lm=%d ref=%d", msr->reclen, ref.reclen); report ("reclen", &ref, data, size, d); }
  if (ref.sid_defined && strcmp (msr->sid, ref.sid))
  { snprintf (d, sizeof (d), "lm=%.100s ref=%.100s", msr->sid, ref.sid); report ("sid", &ref, data, size, d); }
  if (msr->starttime != ref.starttime_ns)
  { snprintf (d, sizeof (d), "lm=%lld ref=%lld", (long long)msr->starttime, (long long)ref.starttime_ns); report ("starttime", &ref, data, size, d); }
  if (ref.samprate_defined && !same_rate (msr->samprate, ref.samprate, ref.formatversion == 3))
  { snprintf (d, sizeof (d), "lm=%.17g ref=%.17g", msr->samprate, ref.samprate); report ("samprate", &ref, data, size, d); }
  if (msr->encoding != ref.encoding)
  { snprintf (d, sizeof (d), "lm=%d ref=%d", msr->encoding, ref.encoding); report ("encoding", &ref, data, size, d); }
  if (msr->pubversion != ref.pubversion)
  { snprintf (d, sizeof (d), "lm=%d ref=%d", msr->pubversion, ref.pubversion); report ("pubversion", &ref, data, size, d); }
  if (msr->flags != ref.flags)
  { snprintf (d, sizeof (d), "lm=%d ref=%d", msr->flags, ref.flags); report ("flags", &ref, data, size, d); }
  if (msr->samplecnt != ref.samplecnt)
  { snprintf (d, sizeof (d), "lm=%lld ref=%lld", (long long)msr->samplecnt, (long long)ref.samplecnt); report ("samplecnt", &ref, data, size, d); }
  if (ref.datalength_defined && msr->datalength != ref.datalength)
  { snprintf (d, sizeof (d), "lm=%u ref=%u", msr->datalength, ref.datalength); report ("datalength", &ref, data, size, d); }

  if (ref.datastate == SWREF_DATA_DECODED || ref.datastate == SWREF_DATA_NONE)
  {
    if (msr->numsamples != ref.numsamples)
    { snprintf (d, sizeof (d), "lm=%lld ref=%lld", (long long)msr->numsamples, (long long)ref.numsamples); report ("numsamples", &ref, data, size, d); }
    else if (ref.numsamples > 0)
    {
      if (msr->sampletype != ref.sampletype)
      { snprintf (d, sizeof (d), "lm=%c ref=%c", msr->sampletype ? msr->sampletype : '0', ref.sampletype); report ("sampletype", &ref, data, size, d); }
      else
      {
        size_t sz = ms_samplesize (ref.sampletype);
        const uint8_t *a = (const uint8_t *)msr->datasamples, *b = (const uint8_t *)ref.samples;
        g_compared_samples += (uint64_t)ref.numsamples;
        if (!a || memcmp (a, b, (size_t)ref.numsamples * sz))
        {
          int64_t i = 0;
          while (a && i < ref.numsamples && !memcmp (a + i * sz, b + i * sz, sz))
            i++;
          snprintf (d, sizeof (d), "first difference at sample %lld of %lld", (long long)i, (long long)ref.numsamples);
          report ("samples", &ref, data, size, d);
        }
      }
    }
  }
  if (ref.steim_xn_mismatch)
  { snprintf (d, sizeof (d), "accepted with a reverse-constant mismatch"); report ("info.steim-xn", &ref, data, size, d); }
  swref_free (&ref);
}
