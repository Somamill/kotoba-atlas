#!/usr/bin/env python3
"""Explainable Japanese phrase lookup against a released Atlas ZIP, entirely local."""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import unicodedata
import zipfile

ANALYZER_VERSION = 3
CONTENT_POS = {'名詞', '動詞', '形容詞', '形状詞', '副詞', '感動詞'}
# Bounded colloquial reversals; candidates must carry the source verb class.
CONTRACTIONS = (
    ('ってる', ('う','つ','る'), 'v5'), ('ってた', ('う','つ','る'), 'v5'),
    ('んでる', ('む','ぶ','ぬ'), 'v5'), ('んでた', ('む','ぶ','ぬ'), 'v5'),
    ('いてる', ('く',), 'v5'), ('いでる', ('ぐ',), 'v5'),
    ('してる', ('す',), 'v5'), ('してる', ('する',), 'vs'),
    ('てる', ('る',), 'v1'), ('でる', ('る',), 'v1'),
    ('ちゃった', ('る',), 'v1'), ('っちゃった', ('う','つ','る'), 'v5'),
)
REFERENCE_PREFIXES = ('[Pitch •', '[Frequency •', '[Kanji •')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def kana(text):
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c
                   for c in unicodedata.normalize('NFKC', text))


def build_index(archive, destination):
    """Build atomically; never modify the dictionary ZIP or an existing valid index."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=destination.name + '-', suffix='.part', dir=destination.parent, delete=False) as stream:
        temporary = Path(stream.name)
    db = sqlite3.connect(temporary)
    try:
        db.execute('PRAGMA journal_mode=OFF')
        db.execute('PRAGMA synchronous=OFF')
        db.execute('CREATE TABLE entries(term TEXT, reading TEXT, rules TEXT, tags TEXT, kind TEXT, score INTEGER, bank TEXT, position INTEGER)')
        db.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT)')
        count = 0
        with zipfile.ZipFile(archive) as source:
            for name in source.namelist():
                if not re.fullmatch(r'term_bank_\d+\.json', name):
                    continue
                batch = []
                for position, row in enumerate(json.loads(source.read(name))):
                    lexical = [g for g in row[5] if not g.startswith(REFERENCE_PREFIXES)]
                    if not lexical:
                        continue
                    kind = 'name' if all(g.startswith('[Names •') for g in lexical) else 'lexical'
                    batch.append((row[0], kana(row[1]), row[3], row[2], kind, row[4], name, position))
                db.executemany('INSERT INTO entries VALUES(?,?,?,?,?,?,?,?)', batch)
                count += len(batch)
        db.execute('CREATE INDEX terms ON entries(term)')
        db.execute('CREATE INDEX readings ON entries(reading)')
        db.execute('INSERT INTO metadata VALUES(?,?)', ('archive_sha256', digest(archive)))
        db.execute('INSERT INTO metadata VALUES(?,?)', ('analyzer_version', str(ANALYZER_VERSION)))
        db.commit()
    except BaseException:
        db.close()
        temporary.unlink(missing_ok=True)
        raise
    db.close()
    temporary.replace(destination)
    return count


class AtlasLookup:
    def __init__(self, index):
        self.db = sqlite3.connect(Path(index).resolve().as_uri() + '?mode=ro', uri=True)
        self.db.row_factory = sqlite3.Row
        self.metadata = dict(self.db.execute('SELECT key,value FROM metadata').fetchall())
        if self.metadata.get('analyzer_version') != str(ANALYZER_VERSION):
            raise ValueError('Lookup index version changed; rebuild the local index.')
        from sudachipy import dictionary, tokenizer
        self.tokenizer = dictionary.Dictionary().create()
        self.mode = tokenizer.Tokenizer.SplitMode.A

    @lru_cache(maxsize=60000)
    def entries(self, term):
        reading = kana(term)
        if re.fullmatch(r'[ぁ-ゖーゝゞ]+', reading):
            return [dict(r) for r in self.db.execute(
                "SELECT * FROM entries WHERE term=? OR reading=? ORDER BY kind='lexical' DESC, term=? DESC, score DESC, reading LIMIT 8",
                (term, reading, term))]
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM entries WHERE term=? ORDER BY kind='lexical' DESC, score DESC, reading LIMIT 8",
            (term,))]

    def tokens(self, text):
        return [{'surface': m.surface(), 'lemma': m.dictionary_form(),
                 'normalized': m.normalized_form(), 'reading': kana(m.reading_form()),
                 'pos': list(m.part_of_speech()), 'start': m.begin(), 'end': m.end(),
                 'oov': m.is_oov()} for m in self.tokenizer.tokenize(text, self.mode)]

    def analyze(self, text):
        if len(text) > 2000:
            raise ValueError('Analyze at most 2,000 characters per cue.')
        tokens = self.tokens(text)
        # A bounded token lattice keeps original offsets and cannot cross punctuation.
        best = [(0, []) for _ in range(len(tokens) + 1)]
        for start in range(len(tokens) - 1, -1, -1):
            first = tokens[start]
            best[start] = best[start + 1]
            if first['pos'][0] in {'補助記号', '記号', '空白'}:
                continue
            for end in range(start + 1, min(len(tokens), start + 8) + 1):
                last = tokens[end - 1]
                if last['pos'][0] in {'補助記号', '記号', '空白'}:
                    break
                surface = text[first['start']:last['end']]
                if len(surface) > 32:
                    break
                prefix = text[first['start']:last['start']]
                forms = [(surface, 'exact', 0),
                         (unicodedata.normalize('NFKC', surface), 'width-normalized', 2),
                         (prefix + last['lemma'], 'dictionary-form', 4),
                         (prefix + last['normalized'], 'analyzer-normalized', 8)]
                required_classes = {}
                for suffix, endings, rule in CONTRACTIONS:
                    if surface.endswith(suffix) and len(surface) > len(suffix):
                        for ending in endings:
                            term = surface[:-len(suffix)] + ending
                            forms.append((term, 'source-checked-contraction', 2))
                            required_classes.setdefault(term, set()).add(rule)
                seen = set()
                for term, method, penalty in forms:
                    if term in seen:
                        continue
                    seen.add(term)
                    matches = self.entries(term)
                    if not matches:
                        continue
                    if method == 'source-checked-contraction':
                        matches = [r for r in matches if any(
                            rule in r['rules'].split() for rule in required_classes[term])]
                        if not matches:
                            continue
                    reading = ''.join(t['reading'] for t in tokens[start:end])
                    last_content = next((t for t in reversed(tokens[start:end])
                                         if t['pos'][0] in CONTENT_POS), last)
                    def mismatch(row):
                        rules = row['rules'].split()
                        if last_content['pos'][0] == '動詞' and not any(r.startswith('v') for r in rules):
                            return 35
                        if last_content['pos'][0] == '形容詞' and 'adj-i' not in rules:
                            return 35
                        return 0
                    entry = min(matches, key=lambda r: (
                        r['kind'] != 'lexical', mismatch(r), r['reading'] != reading, -r['score']))
                    reading_penalty = 8 if entry['term'] != term else 0
                    content = sum(t['pos'][0] in CONTENT_POS for t in tokens[start:end])
                    value = (100 * content + len(surface) * 3 + 4 * (end-start-1)
                             if entry['kind'] == 'lexical' else 1) - penalty - reading_penalty - mismatch(entry)
                    score = value + best[end][0] - 1
                    if score > best[start][0]:
                        item = {'surface': surface, 'start': first['start'], 'end': last['end'],
                                'token_start': start, 'token_end': end,
                                'method': method + ('+reading' if entry['term'] != term else ''),
                                'entry': entry, 'alternatives': [
                                    {'term': r['term'], 'reading': r['reading'], 'kind': r['kind']}
                                    for r in matches if r != entry][:4]}
                        best[start] = (score, [item] + best[end][1])
        return {'tokens': tokens, 'matches': best[0][1]}

    def close(self):
        self.entries.cache_clear()
        self.db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', type=Path, required=True)
    parser.add_argument('--archive', type=Path, help='Required when building; optional to return original definitions.')
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--text')
    parser.add_argument('--check-regressions', type=Path, help='Synthetic text/headword fixture; exits nonzero for a missed headword.')
    args = parser.parse_args()
    if args.build:
        if not args.archive:
            parser.error('--build requires --archive')
        print(json.dumps({'indexed_entries': build_index(args.archive, args.index)}))
    if args.check_regressions:
        lookup = AtlasLookup(args.index)
        try:
            cases = json.loads(args.check_regressions.read_text())
            for case in cases:
                result = lookup.analyze(case['text'])
                if not any(m['entry']['term'] == case['expected_headword'] for m in result['matches']):
                    raise AssertionError('Missing expected headword: ' + case['expected_headword'])
            print(json.dumps({'real_archive_regressions_passed': len(cases)}))
        finally:
            lookup.close()
    if args.text:
        lookup = AtlasLookup(args.index)
        try:
            result = lookup.analyze(args.text)
            if args.archive:
                if digest(args.archive) != lookup.metadata['archive_sha256']:
                    raise ValueError('Archive does not match this index; rebuild the index.')
                with zipfile.ZipFile(args.archive) as source:
                    banks = {}
                    for match in result['matches']:
                        entry = match['entry']
                        if entry['bank'] not in banks:
                            banks[entry['bank']] = json.loads(source.read(entry['bank']))
                        match['definitions'] = banks[entry['bank']][entry['position']][5]
            print(json.dumps(result, ensure_ascii=False, indent=2))
        finally:
            lookup.close()


if __name__ == '__main__':
    main()
