"""Export schema-2 Japanese entries into one ordinary Yomichan-v3 ZIP per language."""
import argparse
import hashlib
import json
import itertools
from pathlib import Path
import sqlite3
import zipfile
from adapters import LANGUAGES
from editions import bounded_banks, check_transfer_budget, edition_stem, optimize_archive, compact_note
from contract import normalized


def sequence(identity):
    if identity.startswith('jmdict:ja:'):
        return int(identity.rsplit(':', 1)[-1])
    return 1_000_000_000 + int(hashlib.sha256(identity.encode()).hexdigest()[:13], 16)


def metadata_notes(records, reading):
    notes = []
    for mode, payload in records:
        value = json.loads(payload)
        source_reading = value.get('reading', '') if isinstance(value, dict) else ''
        if source_reading and normalized(source_reading) != normalized(reading):
            continue
        if mode == 'pitch':
            notes.append(compact_note('[Pitch • Atlas metadata]\nSource detail: '+payload))
        elif mode == 'freq':
            frequency = value.get('frequency', value) if isinstance(value, dict) else value
            if isinstance(frequency, dict):
                frequency = frequency.get('displayValue', frequency.get('value', frequency))
            notes.append('[Frequency • Atlas metadata]\nReference: '+str(frequency))
        else:
            raise ValueError('Unsupported metadata mode: '+mode)
    return notes


def terms(db, language):
    # Project once per canonical entry; aliases share identity and selected senses.
    db.execute('CREATE TEMP TABLE selected(entry_id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
    db.execute('''INSERT INTO selected SELECT e.id,json_group_array(json(s.payload))
        FROM entries e JOIN senses s ON s.entry_id=e.id
        WHERE e.source_language='ja' AND s.language=? GROUP BY e.id''', (language,))
    if language != 'en':
        db.execute('''INSERT INTO selected SELECT e.id,json_group_array(json(s.payload))
            FROM entries e JOIN senses s ON s.entry_id=e.id
            WHERE e.source_language='ja' AND s.language='en'
            AND NOT EXISTS(SELECT 1 FROM selected p WHERE p.entry_id=e.id) GROUP BY e.id''')
    db.execute('CREATE TEMP TABLE kana_headwords(entry_id TEXT PRIMARY KEY)')
    db.execute("INSERT OR IGNORE INTO kana_headwords SELECT s.entry_id FROM senses s,json_each(s.payload,'$.tags') t WHERE t.value='uk'")
    db.execute('CREATE TEMP TABLE browser_identities(sequence INTEGER PRIMARY KEY,entry_id TEXT UNIQUE)')
    for (identity,) in db.execute('SELECT entry_id FROM selected ORDER BY entry_id'):
        try:
            db.execute('INSERT INTO browser_identities VALUES(?,?)', (sequence(identity), identity))
        except sqlite3.IntegrityError as error:
            raise ValueError('Browser sequence collision; retain separate canonical identities: '+identity) from error
    metadata = itertools.groupby(db.execute('SELECT term,mode,payload FROM metadata ORDER BY term,mode,payload'), key=lambda row: row[0])
    meta_term, meta_records = None, []
    def advance_metadata():
        term, rows = next(metadata, (None, []))
        return term, [(row[1], row[2]) for row in rows]
    meta_term, meta_records = advance_metadata()
    kanji = {}
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='kanji'").fetchone():
        kanji = {term: json.loads(payload) for term, payload in db.execute('SELECT term,payload FROM kanji')}
    for identity, rules, term, reading, payload in db.execute('''
        SELECT e.id,e.rules,f.text,f.reading,p.payload FROM selected p
        JOIN entries e ON e.id=p.entry_id JOIN forms f ON f.entry_id=e.id
        WHERE f.kind!='reading' OR EXISTS(SELECT 1 FROM kana_headwords k WHERE k.entry_id=e.id)
        OR NOT EXISTS(SELECT 1 FROM forms written WHERE written.entry_id=e.id
            AND written.reading=f.reading AND written.kind!='reading' AND written.text!=f.text)
        GROUP BY e.id,f.text,f.reading ORDER BY f.text,f.reading,e.id'''):
        senses = json.loads(payload)
        glosses = []
        for sense in senses:
            label = '[English fallback]\n' if language != 'en' and sense['language'] == 'en' else ''
            glosses.append(label+'; '.join(sense['glosses']))
            for example in sense.get('examples', []):
                if isinstance(example, dict) and example.get('sentences'):
                    texts = [s['text'] for s in example['sentences'] if s.get('lang') in {'jpn', {'en':'eng','de':'ger'}.get(language, language)}]
                    if texts: glosses.append('Example: '+' — '.join(texts))
                elif isinstance(example, str):
                    glosses.append('Example: '+example)
                elif isinstance(example, dict) and isinstance(example.get('text'), str):
                    glosses.append('Example: '+example['text']+((' — '+example['translation']) if isinstance(example.get('translation'), str) else ''))
        while meta_term is not None and meta_term < term:
            meta_term, meta_records = advance_metadata()
        if meta_term == term:
            glosses.extend(metadata_notes(meta_records, reading))
        if term in kanji:
            character = kanji[term]
            glosses.append('[Kanji • Atlas metadata]\n'+'; '.join(character[4])+'\nOn: '+character[1]+'\nKun: '+character[2])
        tags = sorted({tag for sense in senses for tag in sense['tags']})
        classes = sorted({('v5' if r.startswith('v5') else 'vs' if r.startswith('vs') else 'v1' if r.startswith('v1') else 'adj-i' if r == 'adj-ix' else r) for r in rules.split()} & {'v1','v5','vs','vk','vz','adj-i'})
        yield [term, reading, ' '.join(tags), ' '.join(classes), 0, list(dict.fromkeys(glosses)), sequence(identity), '']


def export(build, output, revision, language, optimize=True):
    if language not in LANGUAGES:
        raise ValueError('Unsupported definition language')
    db = sqlite3.connect(Path(build).resolve().as_uri()+'?mode=ro', uri=True)
    db.execute('PRAGMA trusted_schema=OFF')
    db.execute('PRAGMA cache_size=-131072')
    names = {'en': 'English', 'de': 'German'}
    stem = edition_stem(language, revision) if language in names else 'Kotoba_Atlas_'+language+'_v'+revision.replace('.', '_').replace('-', '_')
    destination = Path(output)/(stem+'.zip')
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.writestr('index.json', json.dumps({'title': 'Kotoba Atlas — '+names.get(language, language),
                'format': 3, 'revision': revision, 'sequenced': True, 'sourceLanguage': 'ja', 'targetLanguage': language,
                'author': 'Kotoba Atlas contributors', 'url': 'https://github.com/Somamill/kotoba-atlas',
                'isUpdatable': True,
                'indexUrl': 'https://github.com/Somamill/kotoba-atlas/releases/latest/download/Kotoba-Atlas-'+names.get(language, language)+'-index.json',
                'downloadUrl': 'https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v'+revision+'/'+destination.name,
                'description': 'Japanese lexical entries; primary-language definitions with entry-level English fallback. Source-specific coverage; host features vary.'}, ensure_ascii=False))
            families = [('term_bank', terms(db, language)),
                        ('term_meta_bank', ([term, mode, json.loads(payload)] for term, mode, payload in db.execute('SELECT term,mode,payload FROM metadata ORDER BY term,mode,payload')))]
            tables = {row[0] for row in db.execute('SELECT name FROM sqlite_master')}
            for table, family in [('kanji', 'kanji_bank'), ('tags', 'tag_bank')]:
                if table in tables:
                    families.append((family, (json.loads(row[0]) for row in db.execute('SELECT payload FROM '+table+' ORDER BY 1'))))
            for family, records in families:
                for number, data in enumerate(bounded_banks(records), 1):
                    archive.writestr(f'{family}_{number}.json', data)
            sources = [json.loads(row[0]) for row in db.execute('SELECT payload FROM sources ORDER BY id')]
            archive.writestr('SOURCES.json', json.dumps(sources, ensure_ascii=False, indent=2))
            archive.writestr('SOURCES.txt', '\n\n'.join(json.dumps(value, ensure_ascii=False, sort_keys=True) for value in sources))
            for name, data in db.execute('SELECT name,content FROM notices ORDER BY name'):
                archive.writestr('licenses/'+name.replace('..', '_').lstrip('/'), data)
        with zipfile.ZipFile(destination) as archive:
            (Path(output)/('Kotoba-Atlas-'+names.get(language, language)+'-index.json')).write_bytes(archive.read('index.json'))
        if optimize:
            optimize_archive(destination)
        check_transfer_budget(destination.stat().st_size)
        return destination
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--language', choices=LANGUAGES, required=True)
    args = parser.parse_args()
    print(export(args.build, args.output, args.revision, args.language))
