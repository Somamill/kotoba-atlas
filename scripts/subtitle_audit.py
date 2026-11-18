#!/usr/bin/env python3
"""Audit local ASS/SRT/VTT subtitles; emit aggregates, never subtitle dialogue."""
import argparse
from collections import Counter
from html.parser import HTMLParser
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import time

from lookup import AtlasLookup, CONTENT_POS, digest

JAPANESE = re.compile(r'[ぁ-ゖァ-ヺ一-鿿]')
TIMING = re.compile(r'\d{1,2}:\d{2}[^\n]*-->')
DRAWING = re.compile(r'\\p[1-9]')
OVERRIDE = re.compile(r'\{[^}]*\}')


class CaptionText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.ruby_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'rt':
            self.ruby_depth += 1
        elif tag == 'br':
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag == 'rt':
            self.ruby_depth = max(0, self.ruby_depth - 1)

    def handle_data(self, text):
        if not self.ruby_depth:
            self.parts.append(text)


def clean_caption(text):
    if DRAWING.search(text):
        return ''
    text = OVERRIDE.sub('', text).replace('\\N', ' ').replace('\\n', ' ').replace('\\h', ' ')
    parser = CaptionText()
    parser.feed(text)
    text = ' '.join(''.join(parser.parts).split())
    # Leading full-width speaker/SDH labels are not dialogue. Internal brackets stay.
    text = re.sub(r'^(?:[（(][^）)]{1,40}[）)]\s*)+', '', text)
    return text.strip()


def decode(data):
    for encoding in (['utf-16'] if data.startswith((b'\xff\xfe', b'\xfe\xff')) else ['utf-8-sig', 'cp932', 'euc_jp']):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError('Unsupported subtitle encoding; no lossy replacement performed.')


def captions(text, extension):
    if extension.lower() in {'.ass', '.ssa'}:
        fields, events = [], False
        for line in text.splitlines():
            if line.strip().startswith('['):
                events = line.strip().lower() == '[events]'
            if not events:
                continue
            if line.lower().startswith('format:'):
                fields = [s.strip().lower() for s in line.partition(':')[2].split(',')]
            elif line.lower().startswith('dialogue:') and 'text' in fields:
                values = line.partition(':')[2].lstrip().split(',', len(fields) - 1)
                if len(values) == len(fields):
                    value = clean_caption(values[fields.index('text')])
                    if value:
                        yield value
    else:
        for block in re.split(r'\n\s*\n', text.replace('\r\n', '\n').replace('\r', '\n')):
            lines = block.splitlines()
            timing = next((i for i, line in enumerate(lines) if TIMING.search(line)), None)
            if timing is not None:
                value = clean_caption(' '.join(lines[timing + 1:]))
                if value:
                    yield value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--index', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.corpus / 'manifest.json').read_text())
    lookup = AtlasLookup(args.index)
    started = time.perf_counter()
    counts, methods, gaps, names = Counter(), Counter(), Counter(), Counter()
    titles, seen = {}, set()
    errors = []
    try:
        for number, row in enumerate(manifest['files'], 1):
            p = args.corpus / row['local_name']
            if not p.resolve().is_relative_to(args.corpus.resolve()):
                raise ValueError('Subtitle manifest path escapes corpus.')
            if digest(p) != row['sha256']:
                raise ValueError('Subtitle hash mismatch.')
            title = titles.setdefault(row['title'], {'anime': row['anime'], 'files': 0, 'unique_cues': 0,
                                                     'content_tokens': 0, 'surface_hits': 0, 'smart_hits': 0})
            title['files'] += 1
            try:
                cues = captions(decode(p.read_bytes()), p.suffix)
                for cue in cues:
                    counts['parsed_cues'] += 1
                    if not JAPANESE.search(cue):
                        counts['non_japanese_cues_skipped'] += 1
                        continue
                    if len(cue) > 2000:
                        counts['oversized_cues_skipped'] += 1
                        continue
                    identity = hashlib.sha256(cue.encode()).digest()
                    if identity in seen:
                        counts['duplicate_cues_skipped'] += 1
                        continue
                    seen.add(identity)
                    counts['unique_cues'] += 1
                    title['unique_cues'] += 1
                    analysis = lookup.analyze(cue)
                    content = {i for i,t in enumerate(analysis['tokens'])
                               if t['pos'][0] in CONTENT_POS and JAPANESE.search(t['surface'])}
                    exact = {i for i in content if any(e['kind'] == 'lexical'
                             for e in lookup.entries(analysis['tokens'][i]['surface']))}
                    smart = set()
                    for match in analysis['matches']:
                        methods[match['method']] += 1
                        if match['entry']['kind'] == 'lexical':
                            smart.update(set(range(match['token_start'], match['token_end'])) & content)
                        if match['token_end'] - match['token_start'] > 1:
                            counts['multi_token_matches'] += 1
                    for key, value in [('content_tokens',len(content)),('surface_hits',len(exact)),('smart_hits',len(smart))]:
                        counts[key] += value
                        title[key] += value
                    for i in content - smart:
                        token = analysis['tokens'][i]
                        target = names if token['pos'][1] == '固有名詞' else gaps
                        target[token['lemma']] += 1
                        counts['unresolved_oov_tokens'] += int(token['oov'])
            except (ValueError, UnicodeError) as error:
                errors.append({'file_sha256': row['sha256'], 'error': str(error)})
            if number % 8 == 0:
                print(json.dumps({'files_processed': number, 'unique_cues': counts['unique_cues']}), flush=True)
        total = counts['content_tokens']
        report = {
            'status': 'measured', 'lookup_index_version': lookup.metadata['analyzer_version'], 'dictionary_sha256': lookup.metadata['archive_sha256'],
            'tokenizer': {n: importlib.metadata.version(n) for n in ['SudachiPy','SudachiDict-core']},
            'counts': dict(counts), 'match_methods': dict(methods),
            'surface_candidate_rate': round(counts['surface_hits']/total,6) if total else None,
            'smart_candidate_rate': round(counts['smart_hits']/total,6) if total else None,
            'elapsed_seconds': round(time.perf_counter()-started,2),
            'titles': titles, 'unresolved_lexical_candidates': gaps.most_common(150),
            'unresolved_proper_names': names.most_common(60), 'errors': errors,
            'scope': 'Surface baseline includes exact headwords and kana readings. Deduplicated Japanese cues. Content POS tokens only. Candidate retrieval, not human-verified senses or comprehension. Names excluded from lexical hits. No subtitle dialogue in report.'}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps({'finished': True, 'counts': report['counts'],
                          'surface_rate': report['surface_candidate_rate'],
                          'smart_rate': report['smart_candidate_rate']}), flush=True)
    finally:
        lookup.close()


if __name__ == '__main__':
    main()
