#!/usr/bin/env python3
"""Validate every bank against pinned upstream Yomitan schemas and check regressions."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

import fastjsonschema

REF = 'ce1b1bffa0e8819716317f3717932a7fe91e8d52'
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    cache = ROOT / '.cache/schemas' / REF
    cache.mkdir(parents=True, exist_ok=True)
    validators = {}
    for kind in ['index', 'term-bank-v3']:
        name = 'dictionary-' + kind + '-schema.json'
        path = cache / name
        if not path.exists():
            urllib.request.urlretrieve('https://raw.githubusercontent.com/yomidevs/yomitan/' + REF + '/ext/data/schemas/' + name, path)
        validators[kind] = fastjsonschema.compile(json.loads(path.read_text()))
    examples = {term: [] for term in ['羅睺', '物ノ怪', '鎌かけて', '鎌かける', '鎌を掛ける', '食べる']}
    entries = banks = 0
    with zipfile.ZipFile(args.archive) as archive:
        assert archive.testzip() is None, 'Corrupt archive'
        validators['index'](json.loads(archive.read('index.json')))
        assert 'licenses/wadoku.txt' in archive.namelist(), 'Missing source licence'
        for name in archive.namelist():
            if not name.startswith('term_bank_'):
                continue
            rows = json.loads(archive.read(name))
            validators['term-bank-v3'](rows)
            for row in rows:
                assert row[0] and row[5] and all(isinstance(g, str) and g for g in row[5])
                if row[0] in examples:
                    examples[row[0]].append({'reading': row[1], 'rules': row[3], 'sources': [g.split('\n', 1)[0] for g in row[5]]})
            entries += len(rows)
            banks += 1
            if banks % 50 == 0:
                print('Validated', banks, 'banks /', entries, 'entries', flush=True)
    assert all(examples.values()), 'Missing regression term'
    assert any('v1' in row['rules'].split() for row in examples['鎌かける']), 'Lost phrase deinflection rule'
    assert any('v1' in row['rules'].split() for row in examples['食べる']), 'Lost source deinflection rule'
    assert any('EN' in s for row in examples['羅睺'] for s in row['sources']), 'Missing English definition'
    report = {'archive': args.archive.name, 'entries': entries, 'banks': banks,
              'sha256': hashlib.sha256(args.archive.read_bytes()).hexdigest(),
              'upstream_schema_ref': REF, 'schema_validation': 'all index and term-bank JSON passed',
              'examples': examples, 'browser_import_tested': False,
              'limitation': 'Schema and lexical tests do not verify host tokenization or browser import.'}
    dest = args.archive.with_suffix('.validation.json')
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('PASS:', entries, 'entries;', banks, 'banks;', dest.name, flush=True)


if __name__ == '__main__':
    main()
