/*
 * swref: an independent reference decoder for miniSEED 2.4 and miniSEED 3 records,
 * written from the format specifications only:
 *   - SEED Reference Manual, version 2.4 (FDSN): chapter 3 (BTIME), chapter 8 (fixed section
 *     of data header, blockettes 100, 1000, 1001) and appendix B (Steim1 and Steim2).
 *   - FDSN miniSEED 3: record definition, data encodings, appendix C (mapping from 2.4).
 *   - FDSN Source Identifiers 1.0: mapping of SEED 2.4 codes.
 *
 * Where a specification leaves a choice open, the choice is marked "SPEC-OPEN" in swref.c and
 * the matching value is not compared (its *_defined flag is 0).
 *
 * Copyright 2026 ParalleX Labs Inc. Licensed under the Apache License, Version 2.0.
 */
#ifndef SWREF_H
#define SWREF_H

#include <stddef.h>
#include <stdint.h>

#define SWREF_SIDMAX 256

typedef enum {
  SWREF_OK = 0,
  SWREF_REJECT_HEADER = 1, /* not a record, or a header field outside its specified range */
  SWREF_REJECT_LENGTH = 2, /* record length unknown, out of range or longer than the buffer */
  SWREF_REJECT_DATA = 3    /* header accepted, payload could not be decoded */
} swref_status;

typedef enum {
  SWREF_DATA_NONE = 0,        /* no samples (header-only record or zero samples) */
  SWREF_DATA_DECODED = 1,     /* samples decoded */
  SWREF_DATA_UNSUPPORTED = 2  /* encoding not decoded by this reference (legacy, opaque, Steim3) */
} swref_datastate;

typedef struct {
  swref_status status;
  const char *reason; /* static text; set when status != SWREF_OK */

  int formatversion; /* 2 or 3 */
  int32_t reclen;    /* bytes */

  char sid[SWREF_SIDMAX + 1];
  int sid_defined; /* 1 when the specifications fully define the identifier for this record */

  int64_t starttime_ns; /* nanoseconds since 1970-01-01T00:00:00 UTC, leap seconds not counted */
  double samprate;      /* as defined for miniSEED 3 field 6: rate (Hz) if > 0, period (s) if < 0 */
  int samprate_defined;
  int encoding;   /* -1 when no encoding is given (miniSEED 2 record without blockette 1000) */
  int pubversion; /* miniSEED 3 field 9; for 2.4, the optional appendix C mapping R1 D2 Q3 M4 */
  int flags;      /* miniSEED 3 field 3; for 2.4, mapped per appendix C */
  int64_t samplecnt;
  uint32_t datalength; /* payload bytes */
  int datalength_defined;

  swref_datastate datastate;
  char sampletype; /* 'i', 'f', 'd', 't' or 0 */
  int64_t numsamples;
  void *samples; /* malloc'd; int32_t, float, double or char */
  int steim_xn_mismatch; /* 1 when the last decoded Steim sample differs from the reverse constant */
  uint32_t features;     /* SWREF_F_* bits describing what the record used (for triage only) */
} swref_record;

#define SWREF_F_B1001 0x01     /* 2.4: blockette 1001 present */
#define SWREF_F_B100 0x02      /* 2.4: blockette 100 present */
#define SWREF_F_TCORR 0x04     /* 2.4: a non-zero time correction was added */
#define SWREF_F_LEAPSEC 0x08   /* second field is 60 */
#define SWREF_F_LEHEADER 0x10  /* 2.4: header read little endian */
#define SWREF_F_LEDATA 0x20    /* 2.4: blockette 1000 word order little endian */

/* Decode the record at the start of buf. Never reads past buf[len-1]. Returns rec->status. */
swref_status swref_parse (const uint8_t *buf, size_t len, swref_record *rec);

/* Release the sample buffer. */
void swref_free (swref_record *rec);

#endif
