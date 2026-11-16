#!/usr/bin/env python3
"""Build a labeled, text-only Yomichan v3 collection; source licences stay separate."""
import argparse
import hashlib
import html
from html.parser import HTMLParser
import itertools
import json
from pathlib import Path
import re
import sqlite3
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in {'br', 'p', 'div', 'li', 'tr', 'td', 'th'}:
            self.parts.append('\n')
        if tag == 'rt':
            self.parts.append('(')

    def handle_endtag(self, tag):
        if tag in {'p', 'div', 'li', 'tr', 'td', 'th'}:
            self.parts.append('\n')
        if tag == 'rt':
            self.parts.append(')')


def plain(value):
    if isinstance(value, str):
        if re.search(r'</?(?:br|div|span|p|li|b|i|a|ul|ol|ruby|rt|table|td|th|tr)\b', value):
            parser = Text()
            parser.feed(value)
            return ''.join(parser.parts)
        return html.unescape(value)
    if isinstance(value, list):
        return ''.join(plain(v) for v in value)
    if isinstance(value, dict):
        if value.get('type') == 'text':
            return plain(value['text'])
        if value.get('type') == 'text':
            return value['text']
        if value.get('tag') == 'br':
            return '\n'
        if value.get('tag') == 'img' or value.get('type') == 'image':
            return value.get('alt', value.get('description', ''))
        if 'content' not in value:
            if value.get('tag'):
                return ''
            raise ValueError('Unknown structured glossary node: ' + repr(value)[:200])
        text = plain(value['content'])
        if value.get('tag') == 'a' and value.get('href'):
            text += ' (' + value['href'] + ')'
        if value.get('tag') == 'rt':
            text = '(' + text + ')'
        if value.get('tag') in {'div', 'li', 'ul', 'ol', 'tr', 'td', 'th', 'summary', 'details'}:
            text = '\n' + text + '\n'
        return text
    raise ValueError(f'Unrecognized glossary value: {type(value)}')


def clean(value):
    text = plain(value)
    return '\n'.join(line.strip() for line in text.splitlines() if line.strip())


def wadoku_rows(path):
    with tarfile.open(path) as tar:
        member = next(m for m in tar.getmembers() if m.name.endswith('/wadokudict'))
        for line in tar.extractfile(member):
            text = line.decode('utf-8-sig').strip()
            if not text:
                continue
            match = re.fullmatch(r'(.+?) \[([^\]]*)\]\s*(.*)', text)
            if not match:
                raise ValueError(f'Unparsed WaDoku entry: {text[:120]}')
            term, reading, gloss = match.groups()
            definitions = [g.strip() for g in gloss.split('/') if g.strip()]
            yield [term, reading, '', '', 0, definitions, -1, '']


def alias_rows():
    for entry in json.loads((ROOT / 'data/aliases.json').read_text()):
        yield [entry['term'], entry['reading'], '', entry['rules'], 0,
               entry['definitions'] + ['Canonical expression: ' + entry['canonical']], -1, '']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    parser.add_argument('--personal', action='store_true', help='Include restricted/unclear sources locally; never publish this build.')
    parser.add_argument('--local-dir', type=Path, help='Optional private dictionary folder; only explicitly listed files are read.')
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    mode = 'personal' if args.personal else 'public'
    database = args.cache / f'{mode}.sqlite'
    # This is a rebuildable cache, never an installed browser dictionary.
    database.unlink(missing_ok=True)
    db = sqlite3.connect(database)
    db.execute('PRAGMA journal_mode=OFF')
    db.execute('PRAGMA synchronous=OFF')
    db.execute('CREATE TABLE definitions(term TEXT, reading TEXT, source INTEGER, gloss TEXT, rules TEXT, score INTEGER, UNIQUE(term,reading,source,gloss))')
    sources = json.loads((ROOT / 'data/sources.json').read_text())
    notices, stats = [], []
    counts = {'word_rows': 0, 'kanji_rows': 0, 'metadata_rows': 0}

    def add(row, source, label):
        assert len(row) == 8 and isinstance(row[0], str) and row[0]
        assert isinstance(row[1], str) and isinstance(row[3], str)
        gloss = '\n'.join(filter(None, (clean(g) for g in row[5])))
        if row[2]:
            gloss = 'Tags: ' + row[2] + '\n' + gloss
        if not gloss:
            gloss = 'Source entry contains only non-text content; see original dictionary.'
        assert isinstance(row[4], (int, float))
        db.execute('INSERT OR IGNORE INTO definitions VALUES(?,?,?,?,?,?)',
                   (row[0], row[1], source, '[' + label + ']\n' + gloss,
                    row[3], int(row[4])))

    for number, spec in enumerate(sources):
        if spec.get('personal_only') and not args.personal:
            continue
        if 'local_file' in spec:
            if not args.local_dir:
                continue
            path = args.local_dir / spec['local_file']
            if not path.exists():
                continue
        else:
            path = args.cache / spec['file']
            if not path.exists():
                partial = path.with_suffix(path.suffix + '.part')
                urllib.request.urlretrieve(spec['download_url'], partial)
                partial.rename(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if spec.get('sha256') and digest != spec['sha256']:
            raise ValueError('Source checksum mismatch: ' + path.name)
        before = db.total_changes
        notice = dict(spec, sha256=digest)
        label = spec['label']
        if spec.get('kind') == 'wadoku':
            for row in wadoku_rows(path):
                add(row, number, label)
                counts['word_rows'] += 1
        else:
            with zipfile.ZipFile(path) as archive:
                assert archive.testzip() is None, 'Source ZIP corrupt: ' + path.name
                notice['original_index'] = json.loads(archive.read('index.json'))
                notice['embedded_notices'] = {}
                for name in archive.namelist():
                    if any(t in name.lower() for t in ['license', 'attribution', 'source.txt']):
                        if archive.getinfo(name).file_size < 2_000_000:
                            notice['embedded_notices'][name] = archive.read(name).decode('utf-8', errors='replace')
                    if re.fullmatch(r'term_bank_\d+\.json', name):
                        for row in json.loads(archive.read(name)):
                            add(row, number, label)
                            counts['word_rows'] += 1
                    elif re.fullmatch(r'kanji_bank_\d+\.json', name):
                        for char, on, kun, tags, meanings, *extra in json.loads(archive.read(name)):
                            add([char, '', '', '', 0, ['On: ' + on, 'Kun: ' + kun] + meanings, -1, ''], number, label)
                            counts['kanji_rows'] += 1
        db.commit()
        notices.append(notice)
        stats.append({'source': label, 'rows_added': db.total_changes - before})
        print(label, stats[-1]['rows_added'], flush=True)

    alias_number = len(sources)
    for row in alias_rows():
        add(row, alias_number, 'DE/EN • verified spelling/phrase supplement')
    # Stylistic ノ between kanji is an orthographic alias, not a new meaning.
    variant = re.compile(r'(?<=[\u3400-\u9fff々])の(?=[\u3400-\u9fff々])')
    original_rows = db.execute("SELECT term,reading,source,gloss,rules,score FROM definitions WHERE term LIKE '%の%'").fetchall()
    generated = 0
    for term, reading, source, gloss, rules, score in original_rows:
        alias = variant.sub('ノ', term)
        if alias != term:
            generated += db.execute('INSERT OR IGNORE INTO definitions VALUES(?,?,?,?,?,?)',
                (alias, reading, source, gloss + '\nOrthographic alias of ' + term + ' (の → ノ between kanji).', rules, score)).rowcount
    db.commit()
    print('Orthographic alias rows:', generated, flush=True)
    # Metadata is rendered as labeled text so Migaku need not understand Yomitan metadata banks.
    for number, spec in enumerate(sources):
        if spec.get('kind') != 'metadata' or (spec.get('personal_only') and not args.personal):
            continue
        path = args.cache / spec['file']
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if not re.fullmatch(r'term_meta_bank_\d+\.json', name):
                    continue
                for term, kind, value in json.loads(archive.read(name)):
                    reading = value.get('reading', '') if isinstance(value, dict) else ''
                    if kind == 'pitch':
                        detail = 'Pitch-accent positions (0 = heiban): ' + ', '.join(str(p['position']) for p in value['pitches'])
                        detail += '\nSource detail: ' + json.dumps(value, ensure_ascii=False)
                    elif kind == 'freq':
                        detail = 'Frequency data: ' + json.dumps(value, ensure_ascii=False)
                    else:
                        raise ValueError('Unknown metadata kind: ' + kind)
                    readings = [reading] if reading else [r[0] for r in db.execute('SELECT DISTINCT reading FROM definitions WHERE term=?', (term,))]
                    for r in readings or ['']:
                        add([term, r, '', '', 0, [detail], -1, ''], number, spec['label'])
                    counts['metadata_rows'] += 1
        db.commit()
        print('Metadata:', spec['label'], counts['metadata_rows'], flush=True)

    # Lexical sorting keeps builds deterministic; source numbers keep German definitions first.
    output = args.output / ('dict-personal.zip' if args.personal else 'dict-master.zip')
    pending = output.with_suffix('.zip.part')
    total, banks, sample_hits = 0, 0, {}
    cursor = db.execute('SELECT term,reading,source,gloss,rules,score FROM definitions ORDER BY term,reading,source,gloss')
    with zipfile.ZipFile(pending, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        batch = []
        for (term, reading), group in itertools.groupby(cursor, key=lambda r: (r[0], r[1])):
            rows = list(group)
            glosses = list(dict.fromkeys(r[3] for r in rows))
            rules = ' '.join(sorted({rule for r in rows for rule in r[4].split()}))
            row = [term, reading, '', rules, max(r[5] for r in rows), glosses, -1, '']
            assert all(isinstance(g, str) and g for g in glosses)
            batch.append(row)
            total += 1
            if term in {'羅睺', '物ノ怪', '鎌かけて', '鎌かける', '鎌を掛ける', '物の怪', '読む', '食べる'}:
                sample_hits.setdefault(term, []).append({'reading': reading, 'rules': rules})
            if len(batch) == 5000:
                banks += 1
                archive.writestr(f'term_bank_{banks}.json', json.dumps(batch, ensure_ascii=False, separators=(',', ':')))
                batch = []
        if batch:
            banks += 1
            archive.writestr(f'term_bank_{banks}.json', json.dumps(batch, ensure_ascii=False, separators=(',', ':')))
        index = {'title': 'dict. Japanese Master' + (' — Personal' if args.personal else ''),
                 'format': 3, 'revision': '2026.11.16.1', 'sequenced': False,
                 'author': 'Somamill; source dictionary contributors',
                 'url': 'https://github.com/Somamill/dict',
                 'description': 'German-first Japanese collection with English backup and Japanese reference material. Text-only Yomichan v3. Source-specific licences apply. Browser imports are not verified.',
                 'attribution': 'See SOURCES.json and NOTICES.txt inside this archive. Each labeled source retains its own licence; no blanket licence is granted over the collection.'}
        archive.writestr('index.json', json.dumps(index, ensure_ascii=False, indent=2))
        archive.writestr('SOURCES.json', json.dumps(notices, ensure_ascii=False, indent=2))
        archive.writestr('NOTICES.txt', (ROOT / 'DATA-LICENSES.md').read_text())
        for licence in (ROOT / 'licenses').glob('*'):
            archive.write(licence, 'licenses/' + licence.name)
        archive.writestr('README.txt', 'Import this ZIP without extracting. Definitions are plain text; pitch/frequency are notes, not native graphs/sort metadata. No audio/images are bundled. Source rules are preserved; parser behavior belongs to the host app. Personal builds must not be uploaded or redistributed.\n')
    assert all(t in sample_hits for t in ['羅睺', '物ノ怪', '鎌かけて', '鎌かける', '鎌を掛ける'])
    with zipfile.ZipFile(pending) as archive:
        assert archive.testzip() is None
    pending.replace(output)
    report = {'mode': mode, 'lookup_entries': total, 'banks': banks, 'bytes': output.stat().st_size,
              'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'sources': stats,
              'input_counts': counts, 'example_hits': sample_hits,
              'browser_import_tested': False, 'native_metadata': False}
    (args.output / f'{mode}-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    db.close()
    print(json.dumps({'output': str(output), 'entries': total, 'bytes': report['bytes']}), flush=True)


if __name__ == '__main__':
    main()
