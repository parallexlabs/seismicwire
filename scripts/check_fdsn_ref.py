#!/usr/bin/env python3
"""Compare the reference decoder with the FDSN miniSEED 3 reference data set (record + JSON pairs).

usage: check_fdsn_ref.py REF_DUMP DIR
"""
import json, os, struct, subprocess, sys, datetime

def hz(v):
    # miniSEED 3 field 6: positive rate in Hz, or negative period in seconds
    return v if v > 0 else (-1.0 / v if v < 0 else 0.0)

def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]

def iso_ns(s):
    # "2022-06-05T20:32:38.123456789Z" -> epoch nanoseconds
    main, frac = s.rstrip('Z').split('.') if '.' in s else (s.rstrip('Z'), '0')
    dt = datetime.datetime.strptime(main, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=datetime.timezone.utc)
    return int(dt.timestamp()) * 10**9 + int((frac + '000000000')[:9])

dump, d = sys.argv[1], sys.argv[2]
bad = 0
for fn in sorted(os.listdir(d)):
    if not fn.endswith('.mseed3'):
        continue
    exp = json.load(open(os.path.join(d, fn[:-7] + '.json')))[0]
    got = json.loads(subprocess.run([dump, os.path.join(d, fn)], capture_output=True, text=True).stdout)
    checks = [
        ('status', got['status'], 0),
        ('sid', got['sid'], exp['SID']),
        ('reclen', got['reclen'], exp['RecordLength']),
        ('formatversion', got['formatversion'], exp['FormatVersion']),
        ('flags', got['flags'], exp['Flags']['RawUInt8']),
        ('starttime', got['starttime_ns'], iso_ns(exp['StartTime'])),
        ('encoding', got['encoding'], exp['EncodingFormat']),
        ('samprate', hz(got['samprate']), exp['SampleRate']),
        ('samplecnt', got['samplecnt'], exp['SampleCount']),
        ('pubversion', got['pubversion'], exp['PublicationVersion']),
        ('datalength', got['datalength'], exp['DataLength']),
    ]
    if 'Data' in exp and exp['EncodingFormat'] == 4:  # float32: compare after rounding both to float32
        checks.append(('samples', [f32(x) for x in got['samples']], [f32(x) for x in exp['Data']]))
    elif 'Data' in exp and exp['EncodingFormat'] != 0:
        checks.append(('samples', got['samples'], exp['Data']))
    if exp['EncodingFormat'] == 0 and 'Data' in exp:
        t = ''.join(exp['Data']) if isinstance(exp['Data'], list) else exp['Data']
        checks.append(('text_bytes', got['text_len'], len(t.encode('utf-8'))))  # sample count is in bytes
    fails = [(k, g if k != 'samples' else '...', e if k != 'samples' else '...') for k, g, e in checks if g != e]
    bad += bool(fails)
    print('%-48s %s' % (fn, 'PASS' if not fails else 'FAIL %s' % fails))
print('files with a failure:', bad)
sys.exit(1 if bad else 0)
