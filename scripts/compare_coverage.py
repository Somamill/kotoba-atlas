#!/usr/bin/env python3
"""Verify a packaging-only update retains every decoded record and source notice."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import zipfile


def records(archive, family):
    for name in archive.namelist():
        if re.fullmatch(family + r'_bank_\d+\.json', name):
            yield from json.loads(archive.read(name))


def digest(row):
    return hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).digest()


def compare(previous_path, current_path):
    counts = {}
    with zipfile.ZipFile(previous_path) as previous, zipfile.ZipFile(current_path) as current:
        old_index = json.loads(previous.read('index.json'))
        new_index = json.loads(current.read('index.json'))
        for key in ['title', 'sourceLanguage', 'targetLanguage']:
            assert old_index.get(key) == new_index.get(key), 'Changed edition identity: ' + key
        for family in ['term', 'term_meta', 'kanji', 'tag']:
            remaining = Counter(digest(row) for row in records(previous, family))
            count = sum(remaining.values())
            for row in records(current, family):
                key = digest(row)
                assert remaining[key] > 0, 'Changed or extra ' + family + ' record'
                remaining[key] -= 1
                if remaining[key] == 0:
                    del remaining[key]
            assert not remaining, 'Lost ' + family + ' records'
            counts[family] = count
        for name in previous.namelist():
            if name in {'SOURCES.json', 'NOTICES.txt'} or name.startswith('licenses/') and not name.endswith('/'):
                assert previous.read(name) == current.read(name), 'Changed source notice: ' + name
    return {'previous': Path(previous_path).name, 'current': Path(current_path).name,
            'retained_lookup_pairs': counts['term'], 'added_lookup_pairs': 0, 'removed_lookup_pairs': 0,
            'decoded_records_identical_including_duplicates': True, 'records': counts, 'source_notices_retained': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['previous', 'current', 'report']:
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    report = compare(args.previous, args.current)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
