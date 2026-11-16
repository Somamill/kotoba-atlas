#!/usr/bin/env python3
"""Measure sequential offline ZIP/JSON preparation; this is not a browser benchmark."""
import argparse
import json
from pathlib import Path
import resource
import sys
import time
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('archive', type=Path)
args = parser.parse_args()
start = time.perf_counter()
entries = native_metadata = kanji = 0
with zipfile.ZipFile(args.archive) as archive:
    members = archive.infolist()
    banks = [m for m in members if m.filename.startswith(('term_bank_', 'term_meta_bank_', 'kanji_bank_', 'tag_bank_'))]
    for bank in banks:
        count = len(json.loads(archive.read(bank)))
        if bank.filename.startswith('term_bank_'):
            entries += count
        elif bank.filename.startswith('term_meta_bank_'):
            native_metadata += count
        elif bank.filename.startswith('kanji_bank_'):
            kanji += count
assert entries > 0 and banks, 'The archive has no usable word dictionary banks'
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
if sys.platform != 'darwin':
    peak *= 1024
report = {'archive': args.archive.name, 'entries': entries,
          'compressed_bytes': args.archive.stat().st_size,
          'expanded_bytes': sum(m.file_size for m in members),
          'dictionary_banks': len(banks), 'largest_bank_bytes': max(m.file_size for m in banks),
          'native_metadata_records': native_metadata, 'native_kanji_records': kanji,
          'offline_sequential_parse_seconds': round(time.perf_counter() - start, 3),
          'process_peak_rss_bytes': peak,
          'scope': 'Python sequential decompression and JSON parsing on this machine. Not Migaku/Yomitan import time, lookup latency, or browser memory.'}
args.archive.with_suffix('.benchmark.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
