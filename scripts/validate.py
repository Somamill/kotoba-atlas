#!/usr/bin/env python3
"""Validate every bank against pinned upstream Yomitan schemas and check regressions."""
import argparse
import hashlib
import json
import os
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
    for kind in ['index', 'term-bank-v3', 'term-meta-bank-v3', 'kanji-bank-v3', 'tag-bank-v3']:
        name = 'dictionary-' + kind + '-schema.json'
        path = cache / name
        if not path.exists():
            data = urllib.request.urlopen('https://raw.githubusercontent.com/yomidevs/yomitan/' + REF + '/ext/data/schemas/' + name).read()
            json.loads(data)
            temporary = path.with_suffix('.' + str(os.getpid()) + '.tmp')
            temporary.write_bytes(data)
            temporary.replace(path)
        validators[kind] = fastjsonschema.compile(json.loads(path.read_text()))
    examples = {term: [] for term in ['羅睺', '物ノ怪', '鎌かけて', '鎌かける', '鎌を掛ける', '食べる',
                                    '天驅ける', '驅ける', '濕氣る', '湿氣る', '濕気る']}
    with zipfile.ZipFile(args.archive) as archive:
        edition_index = json.loads(archive.read('index.json'))
    edition = edition_index.get('targetLanguage')
    edition_archive = edition_index['title'].startswith('Kotoba Atlas')
    entries = banks = 0
    with zipfile.ZipFile(args.archive) as archive:
        assert archive.testzip() is None, 'Corrupt archive'
        validators['index'](json.loads(archive.read('index.json')))
        assert 'licenses/wadoku.txt' in archive.namelist(), 'Missing source licence'
        for name in archive.namelist():
            if edition_archive and name.startswith(('term_bank_', 'term_meta_bank_', 'kanji_bank_', 'tag_bank_')):
                assert archive.getinfo(name).file_size <= 2 * 1024 * 1024, 'Oversized dictionary bank: ' + name
            if name.startswith('term_meta_bank_'):
                validators['term-meta-bank-v3'](json.loads(archive.read(name)))
            elif name.startswith('kanji_bank_'):
                validators['kanji-bank-v3'](json.loads(archive.read(name)))
            elif name.startswith('tag_bank_'):
                validators['tag-bank-v3'](json.loads(archive.read(name)))
            if not name.startswith('term_bank_'):
                continue
            rows = json.loads(archive.read(name))
            validators['term-bank-v3'](rows)
            if edition_archive:
                assert archive.getinfo(name).file_size <= 2 * 1024 * 1024, 'Oversized import bank'
            for row in rows:
                assert row[0] and row[5] and all(isinstance(g, str) and g for g in row[5])
                if row[0] in examples:
                    examples[row[0]].append({'reading': row[1], 'rules': row[3], 'sources': [g.split('\n', 1)[0] for g in row[5]]})
                if edition_archive:
                    labels = [g.split('\n', 1)[0] for g in row[5]]
                    assert any(not s.startswith(('[Pitch •', '[Frequency •')) for s in labels), 'Metadata-only search result'
                    has_de = any(s.startswith('[DE •') for s in labels)
                    has_en = any(s.startswith('[EN •') for s in labels)
                    if edition == 'en':
                        assert not has_de, 'German definition in English edition'
                    if edition == 'de' and has_de:
                        assert not has_en, 'Redundant English fallback beside German definition'
                    assert not ('[EN • Jitendex]' in labels and '[EN • JMdict]' in labels), 'Overlapping core dictionaries'
            entries += len(rows)
            banks += 1
            if banks % 50 == 0:
                print('Validated', banks, 'banks /', entries, 'entries', flush=True)
    assert all(examples.values()), 'Missing regression term'
    assert any('v1' in row['rules'].split() for row in examples['鎌かける']), 'Lost phrase deinflection rule'
    assert any('v1' in row['rules'].split() for row in examples['食べる']), 'Lost source deinflection rule'
    for term, rule in [('天驅ける', 'v1'), ('驅ける', 'v1'), ('濕氣る', 'v5'), ('湿氣る', 'v5'), ('濕気る', 'v5')]:
        assert any(rule in row['rules'].split() for row in examples[term]), 'Lost alternate-spelling verb rule: ' + term
    assert any('EN' in s for row in examples['羅睺'] for s in row['sources']), 'Missing English definition'
    report = {'archive': args.archive.name, 'entries': entries, 'banks': banks,
              'sha256': hashlib.sha256(args.archive.read_bytes()).hexdigest(),
              'upstream_schema_ref': REF, 'schema_validation': 'all index and term-bank JSON passed',
              'examples': examples, 'browser_import_tested': False,
              'edition': edition, 'edition_policy_validation': edition_archive,
              'limitation': 'Schema and lexical tests do not verify host tokenization or browser import.'}
    dest = args.archive.with_suffix('.validation.json')
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('PASS:', entries, 'entries;', banks, 'banks;', dest.name, flush=True)


if __name__ == '__main__':
    main()
