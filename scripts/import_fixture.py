#!/usr/bin/env python3
"""Create a representative test archive; not a replacement dictionary download."""
import argparse
import json
import re
import zipfile

TERMS = {'羅睺', '物ノ怪', '鎌かけて', '鎌かける', '鎌を掛ける', 'ぬまる', '沼る',
         '推し活する', '食べる', '楽しい', 'てぇてぇ', '日本語'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive')
    parser.add_argument('output')
    args = parser.parse_args()
    words, metadata, kanji, tags = [], [], [], []
    with zipfile.ZipFile(args.archive) as source:
        index = json.loads(source.read('index.json'))
        index['title'] += ' Import Test'
        index.pop('isUpdatable', None)
        index.pop('indexUrl', None)
        index.pop('downloadUrl', None)
        for name in source.namelist():
            if not re.fullmatch(r'(term|term_meta|kanji|tag)_bank_\d+\.json', name):
                continue
            rows = json.loads(source.read(name))
            if name.startswith('term_bank_'):
                words.extend(row for row in rows if row[0] in TERMS)
            elif name.startswith('term_meta_bank_'):
                metadata.extend(row for row in rows if row[0] in TERMS)
            elif name.startswith('kanji_bank_'):
                kanji.extend(row for row in rows if row[0] in {'語', '怪', '羅', '睺', '鎌'})
            else:
                tags.extend(rows)
    assert TERMS <= {row[0] for row in words}, TERMS - {row[0] for row in words}
    with zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED) as out:
        out.writestr('index.json', json.dumps(index, ensure_ascii=False))
        for prefix, rows in [('term', words), ('term_meta', metadata), ('kanji', kanji), ('tag', tags)]:
            if rows:
                out.writestr(prefix + '_bank_1.json', json.dumps(rows, ensure_ascii=False))
    print(json.dumps({'words': len(words), 'metadata': len(metadata), 'kanji': len(kanji), 'tags': len(tags)}))


if __name__ == '__main__':
    main()
