"""Package one self-contained, bounded-bank dictionary for each definition language."""
import hashlib
import itertools
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BANK_BYTES = 2 * 1024 * 1024
BANK_ENTRIES = 5000

# Only portable JMdict meanings are recognized; dictionary-specific tags stay in text.
POS_TAGS = {'n': 'noun', 'v1': 'ichidan verb', 'v5': 'godan verb', 'vs': 'suru verb',
            'vk': 'kuru verb', 'vz': 'zuru verb', 'adj-i': 'i-adjective', 'adj-na': 'na-adjective',
            'adj-no': 'no-adjective', 'adv': 'adverb', 'exp': 'expression', 'int': 'interjection',
            'prt': 'particle', 'conj': 'conjunction', 'pn': 'pronoun', 'aux': 'auxiliary',
            'aux-v': 'auxiliary verb', 'aux-adj': 'auxiliary adjective', 'cop': 'copula',
            'ctr': 'counter', 'num': 'number', 'pref': 'prefix', 'suf': 'suffix',
            'vt': 'transitive verb', 'vi': 'intransitive verb', 'sl': 'slang', 'col': 'colloquial',
            'vulg': 'vulgar', 'arch': 'archaic', 'obs': 'obsolete', 'hon': 'honorific',
            'hum': 'humble', 'pol': 'polite', 'derog': 'derogatory', 'joc': 'jocular'}


def merge_glosses(texts):
    """Merge identical lexical bodies, keeping source credit and original tag text."""
    merged, positions = [], {}
    for text in texts:
        header, separator, body = text.partition('\n')
        tags = ''
        if body.startswith('Tags: '):
            tags, _, body = body.partition('\n')
        language = header[1:3] if header.startswith(('[DE •', '[EN •')) else ''
        sense_flags = tuple(sorted(set(tags[6:].split()) - (POS_TAGS.keys() - {'sl', 'col', 'vulg', 'arch'}))) if tags else ()
        key = (language, body, sense_flags) if language and separator else None
        if key is not None and key in positions:
            index = positions[key]
            previous_header, previous_body = merged[index].split('\n', 1)
            labels = list(dict.fromkeys([*previous_header[1:-1].split(' | '), header[1:-1]]))
            if tags and not previous_body.startswith('Tags: '):
                previous_body = tags + '\n' + previous_body
            elif tags and previous_body.startswith('Tags: '):
                previous_tags, _, previous_body = previous_body.partition('\n')
                previous_body = 'Tags: ' + ' '.join(sorted(set(previous_tags[6:].split() + tags[6:].split()))) + '\n' + previous_body
            merged[index] = '[' + ' | '.join(labels) + ']\n' + previous_body
        else:
            if key is not None:
                positions[key] = len(merged)
            merged.append(header + '\n' + (tags + '\n' if tags else '') + body if separator else text)
    return list(dict.fromkeys(merged))


def bounded_banks(records):
    batch, size = [], 0
    for record in records:
        encoded = json.dumps(record, ensure_ascii=False, separators=(',', ':')).encode()
        if batch and (size + len(encoded) + len(batch) + 2 > BANK_BYTES or len(batch) >= BANK_ENTRIES):
            yield b'[' + b','.join(batch) + b']'
            batch, size = [], 0
        if len(encoded) + 2 > BANK_BYTES:
            raise ValueError('One record exceeds the import bank limit')
        batch.append(encoded)
        size += len(encoded)
    if batch:
        yield b'[' + b','.join(batch) + b']'


def select_definitions(rows, language, sources):
    """Choose a primary English source, or German with English coverage fallback."""
    def spec(row):
        return sources[row[2]] if row[2] < len(sources) else {'label': (row[3].split('\n', 1)[0].strip('[]') if row[3].startswith(('[DE •', '[EN •')) else 'Atlas supplement'), 'kind': 'words'}

    meanings = [row for row in rows if spec(row).get('kind') != 'metadata']
    german = [row for row in meanings if spec(row)['label'].startswith('DE •')]
    english = [row for row in meanings if spec(row)['label'].startswith('EN •')]
    if any(spec(row)['label'] == 'EN • Jitendex' for row in english):
        english = [row for row in english if spec(row)['label'] != 'EN • JMdict']
    common = [row for row in meanings if not spec(row)['label'].startswith(('DE •', 'EN •'))]
    selected = common + (german if language == 'de' and german else english)
    if not selected:
        return None
    selected.sort(key=lambda row: row[2])
    glosses = []
    for row in selected:
        text = row[3]
        if row[2] >= len(sources):
            excluded = 'DE:' if language == 'en' else 'EN:'
            text = '\n'.join(line for line in text.splitlines() if not line.startswith(excluded))
        if text not in glosses:
            glosses.append(text)
    glosses = merge_glosses(glosses)
    for row in rows:
        if spec(row).get('kind') == 'metadata':
            glosses.append(compact_note(row[3]))
    rules = ' '.join(sorted({rule for row in rows for rule in row[4].split()}))
    tags = set(rules.split()) & POS_TAGS.keys()
    for row in rows:
        lines = row[3].splitlines()
        if len(lines) > 1 and lines[1].startswith('Tags: '):
            tags.update(set(lines[1][6:].split()) & POS_TAGS.keys())
    labels = [spec(row)['label'] for row in selected]
    lexical = any(label.startswith(('DE •', 'EN •', 'Atlas')) for label in labels)
    score = 100 if lexical else (-1000 if all(label.startswith('Names •') for label in labels) else -100)
    return [rows[0][0], rows[0][1], ' '.join(sorted(tags)), rules, score, list(dict.fromkeys(glosses)), -1, '']


def compact_note(text):
    label = text.split('\n', 1)[0]
    if 'Frequency data: ' in text:
        value = json.loads(text.split('Frequency data: ', 1)[1])
        if isinstance(value, dict):
            value = value.get('frequency', value)
        if isinstance(value, dict):
            value = value.get('displayValue', value.get('value', value))
        return label + '\nRank: ' + str(value) + ' (lower = more common)'
    if 'Source detail: ' in text:
        data = json.loads(text.split('Source detail: ', 1)[1])
        pitches = []
        for pitch in data['pitches']:
            note = str(pitch['position'])
            if pitch.get('devoice'):
                devoice = pitch['devoice']
                note += '; devoiced morae: ' + (', '.join(map(str, devoice)) if isinstance(devoice, list) else str(devoice))
            pitches.append(note)
        description = 'heiban' if pitches == ['0'] else 'downstep mora; 0 = heiban'
        return label + '\nPitch: ' + ' / '.join(pitches) + ' (' + description + ')'
    return text


def package_editions(db, output, sources, notices, cache):
    product = json.loads((ROOT / 'data/product.json').read_text())
    results = []
    for language, english_name in [('en', 'English'), ('de', 'German')]:
        stem = 'Kotoba-Atlas-' + english_name + '-v' + product['version']
        dest = output / (stem + '.zip')
        partial = dest.with_suffix('.zip.part')
        index = {'title': product['name'] + ' — ' + english_name,
                 'format': 3, 'revision': product['version'], 'sequenced': False,
                 'author': 'Somamill; source dictionary contributors',
                 'url': product['repository'], 'sourceLanguage': 'ja', 'targetLanguage': language,
                 'description': 'One self-contained Japanese dictionary with plain word glossaries, native kanji/pitch/frequency banks for supporting importers, and readable reference notes for word-only importers. German uses English fallback for coverage gaps. Runtime support depends on the host.',
                 'frequencyMode': 'rank-based',
                 'attribution': 'Source-specific licences apply. Original source metadata and notices are in SOURCES.json and NOTICES.txt.',
                 'isUpdatable': True,
                 'indexUrl': product['repository'] + '/releases/latest/download/Kotoba-Atlas-' + english_name + '-index.json',
                 'downloadUrl': product['repository'] + '/releases/download/' + product['release_tag'] + '/' + stem + '.zip'}
        total = banks = used_bytes = maximum_bank = 0
        batch = []
        hits = {}
        features = {'names': 0, 'kanji': 0, 'grammar': 0, 'folklore': 0, 'pitch_notes': 0, 'frequency_notes': 0}
        with zipfile.ZipFile(partial, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            def write(name, data):
                info = zipfile.ZipInfo(name, (2026, 11, 16, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data, compresslevel=6)

            write('index.json', json.dumps(index, ensure_ascii=False, indent=2))
            write('tag_bank_1.json', json.dumps([[name, 'register' if name in {'sl', 'col', 'vulg', 'arch'} else 'partOfSpeech', 0, detail, 0] for name, detail in POS_TAGS.items()], ensure_ascii=False))
            tag_bank = 1

            def flush():
                nonlocal batch, used_bytes, banks, maximum_bank
                if batch:
                    banks += 1
                    payload = b'[' + b','.join(batch) + b']'
                    maximum_bank = max(maximum_bank, len(payload))
                    write('term_bank_' + str(banks) + '.json', payload)
                    batch, used_bytes = [], 0

            cursor = db.execute('SELECT term,reading,source,gloss,rules,score FROM definitions ORDER BY term,reading,source,gloss')
            for (term, reading), group in itertools.groupby(cursor, key=lambda row: (row[0], row[1])):
                row = select_definitions(list(group), language, sources)
                if row is None:
                    continue
                encoded = json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode()
                if len(encoded) + 2 > BANK_BYTES:
                    raise ValueError('One word record exceeds the import bank limit: ' + term)
                if batch and (used_bytes + len(encoded) + len(batch) + 2 > BANK_BYTES or len(batch) >= BANK_ENTRIES):
                    flush()
                batch.append(encoded)
                used_bytes += len(encoded)
                total += 1
                for key, label in [('names', '[Names •'), ('kanji', '[Kanji •'), ('grammar', '[JA • NINJAL'),
                                   ('folklore', '[JA • Yokai'), ('pitch_notes', '[Pitch •'), ('frequency_notes', '[Frequency •')]:
                    features[key] += any(gloss.startswith(label) for gloss in row[5])
                if term in {'羅睺', '物ノ怪', '鎌かけて', '鎌かける', '天驅ける', '驅ける', '濕氣る', '湿氣る', '濕気る'}:
                    hits.setdefault(term, []).append(reading)
            flush()
            meta_bank = kanji_bank = native_meta = native_kanji = 0
            for source in sources:
                if source.get('personal_only'):
                    continue
                native_kind = 'meta' if source.get('kind') == 'metadata' else ('kanji' if source.get('file') == 'KANJIDIC_english.zip' else None)
                if native_kind is None:
                    continue
                with zipfile.ZipFile(cache / source['file']) as original:
                    if native_kind == 'kanji':
                        for tag_file in original.namelist():
                            if re.fullmatch(r'tag_bank_\d+\.json', tag_file):
                                tag_bank += 1
                                write(f'tag_bank_{tag_bank}.json', original.read(tag_file))
                    pattern = r'term_meta_bank_\d+\.json' if native_kind == 'meta' else r'kanji_bank_\d+\.json'
                    for name in original.namelist():
                        if not re.fullmatch(pattern, name):
                            continue
                        records = json.loads(original.read(name))
                        # Normalize the source's scalar devoicing annotation to Yomitan's array form.
                        for record in records:
                            if native_kind == 'meta' and record[1] == 'pitch':
                                for pitch in record[2]['pitches']:
                                    if isinstance(pitch.get('devoice'), int):
                                        pitch['devoice'] = [pitch['devoice']]
                        if native_kind == 'meta':
                            native_meta += len(records)
                        else:
                            native_kanji += len(records)
                        for payload in bounded_banks(records):
                            if native_kind == 'meta':
                                meta_bank += 1
                                target = f'term_meta_bank_{meta_bank}.json'
                            else:
                                kanji_bank += 1
                                target = f'kanji_bank_{kanji_bank}.json'
                            write(target, payload)
            write('SOURCES.json', json.dumps(notices, ensure_ascii=False, indent=2))
            write('NOTICES.txt', (ROOT / 'DATA-LICENSES.md').read_text())
            for licence in (ROOT / 'licenses').glob('*'):
                write('licenses/' + licence.name, licence.read_bytes())
            write('README.txt', 'Kotoba Atlas ' + product['version'] + ' — ' + english_name + '\nImport this single ZIP without extracting. Plain word banks include readable reference notes. Native kanji/pitch/frequency banks are also included for supporting importers such as Yomitan. Word-only importers may ignore those extra banks. Audio and images are not bundled. Live import compatibility remains untested.\n')
        assert all(term in hits for term in ['羅睺', '物ノ怪', '鎌かけて', '鎌かける'])
        assert all(features.values()), 'An expected feature layer is empty: ' + str(features)
        partial.replace(dest)
        with zipfile.ZipFile(dest) as archive:
            expanded = sum(member.file_size for member in archive.infolist())
            largest_data_bank = max(member.file_size for member in archive.infolist() if member.filename.startswith(('term_bank_', 'term_meta_bank_', 'kanji_bank_', 'tag_bank_')))
        report = {'name': product['name'], 'version': product['version'], 'language': language,
                  'archive': dest.name, 'lookup_entries': total, 'compressed_bytes': dest.stat().st_size,
                  'expanded_bytes': expanded, 'banks': banks, 'largest_bank_bytes': maximum_bank,
                  'largest_data_bank_bytes': largest_data_bank,
                  'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(), 'features': features,
                  'regression_hits': hits, 'browser_import_tested': False,
                  'format': 'Yomichan v3: plain term banks plus native kanji and term metadata banks',
                  'native_metadata_records': native_meta, 'native_kanji_records': native_kanji,
                  'english_primary': 'Jitendex; JMdict fills missing term/reading pairs; Wiktionary supplements',
                  'german_policy': 'German meanings when present; English fallback for uncovered term/reading pairs',
                  'metadata_only_results_omitted': True}
        (output / (stem + '.report.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        (output / ('Kotoba-Atlas-' + english_name + '-index.json')).write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')
        results.append(report)
        results.append(package_migaku(dest, output, product, language, english_name, report))
        print(json.dumps({'archive': dest.name, 'entries': total, 'bytes': dest.stat().st_size}), flush=True)
    return results


def package_migaku(master, output, product, language, english_name, master_report):
    """One word-only archive for Migaku; reference notes stay in the word entries."""
    stem = 'Kotoba_Atlas_' + english_name + '_Migaku_v' + product['version'].replace('.', '_')
    destination = output / (stem + '.zip')
    pending = destination.with_suffix('.zip.part')
    with zipfile.ZipFile(master) as source, zipfile.ZipFile(pending, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as target:
        index = json.loads(source.read('index.json'))
        index.update(title='Kotoba_Atlas_' + english_name + '_Migaku',
                     indexUrl=product['repository'] + '/releases/latest/download/Kotoba-Atlas-' + english_name + '-Migaku-index.json',
                     downloadUrl=product['repository'] + '/releases/download/' + product['release_tag'] + '/' + stem + '.zip',
                     description='Migaku word-dictionary profile. All word, name, grammar, kanji-reference, pitch and frequency text remains in ordinary Yomichan word banks. Native Yomitan metadata banks are available in the full export. Current Migaku Early Access live import is not certified.')
        def write(name, value):
            info = zipfile.ZipInfo(name, (2026, 11, 16, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            target.writestr(info, value, compresslevel=6)
        write('index.json', json.dumps(index, ensure_ascii=False, indent=2))
        for name in source.namelist():
            if re.fullmatch(r'term_bank_\d+\.json', name) or name.startswith('licenses/') or name == 'NOTICES.txt':
                write(name, source.read(name))
        write('SOURCES.txt', source.read('SOURCES.json'))
        write('README.txt', 'Kotoba Atlas ' + product['version'] + ' — ' + english_name + ' — Migaku\nImport this single ZIP without extracting. Use the filename-derived name or the ASCII index title; older Migaku Anki importers use dictionary names in SQL identifiers. Words, names, grammar, kanji references, pitch and frequency notes are included. Native Yomitan metadata and character banks are omitted from this tool-specific export; install the full export in Yomitan for native features. Current Migaku Early Access live import is not certified. Keep the previous working dictionary until import finishes.\n')
    pending.replace(destination)
    with zipfile.ZipFile(destination) as archive:
        expanded = sum(item.file_size for item in archive.infolist())
    report = {**master_report, 'archive': destination.name, 'profile': 'migaku-word-banks',
              'compressed_bytes': destination.stat().st_size, 'expanded_bytes': expanded,
              'native_metadata_records': 0, 'native_kanji_records': 0,
              'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
              'format': 'Yomichan v3 ordinary word banks; complete text references, no native metadata banks'}
    destination.with_suffix('.report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    (output / ('Kotoba-Atlas-' + english_name + '-Migaku-index.json')).write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')
    return report
