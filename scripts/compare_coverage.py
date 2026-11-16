#!/usr/bin/env python3
"""Stream-check that a release retains every old lookup pair and both exports share words."""
import argparse
import hashlib
import json
import re
import zipfile


def word_files(archive):
    return sorted((name for name in archive.namelist() if re.fullmatch(r'term_bank_\d+\.json', name)), key=lambda name: int(re.search(r'\d+', name)[0]))


def keys(archive):
    for name in word_files(archive):
        for row in json.loads(archive.read(name)):
            yield row[0], row[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['previous', 'current', 'migaku', 'report']:
        parser.add_argument(name)
    args = parser.parse_args()
    with zipfile.ZipFile(args.previous) as previous, zipfile.ZipFile(args.current) as current, zipfile.ZipFile(args.migaku) as migaku:
        assert json.loads(previous.read('index.json'))['title'] == json.loads(current.read('index.json'))['title'], 'Changed update identity'
        old = iter(keys(previous))
        sentinel = object()
        expected = next(old, sentinel)
        retained = additions = 0
        for actual in keys(current):
            if expected is not sentinel and expected < actual:
                raise AssertionError('Lost lookup pair: ' + repr(expected))
            if expected == actual:
                retained += 1
                expected = next(old, sentinel)
            else:
                additions += 1
        assert expected is sentinel, 'Old lookup pairs disappeared at the end'
        names = word_files(current)
        assert names == word_files(migaku), 'Migaku export changed word banks'
        for name in names:
            assert hashlib.sha256(current.read(name)).digest() == hashlib.sha256(migaku.read(name)).digest(), name
        report = {'previous': args.previous.split('/')[-1], 'current': args.current.split('/')[-1],
                  'migaku': args.migaku.split('/')[-1], 'retained_lookup_pairs': retained,
                  'added_lookup_pairs': additions, 'removed_lookup_pairs': 0,
                  'word_banks_identical_between_exports': True}
        with open(args.report, 'w') as out:
            json.dump(report, out, ensure_ascii=False, indent=2)
            out.write('\n')
        print(json.dumps(report))


if __name__ == '__main__':
    main()
