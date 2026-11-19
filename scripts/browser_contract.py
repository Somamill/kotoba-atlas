"""Export schema-2 Japanese entries into one ordinary Yomichan-v3 ZIP per language."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import zipfile
from adapters import LANGUAGES
from editions import bounded_banks, check_transfer_budget, edition_stem, optimize_archive


def sequence(identity):
    if identity.startswith('jmdict:ja:'):
        return int(identity.rsplit(':', 1)[-1])
    return -int(hashlib.sha256(identity.encode()).hexdigest()[:13], 16)


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
    for identity, rules, term, reading, payload in db.execute('''
        SELECT e.id,e.rules,f.text,f.reading,p.payload FROM selected p
        JOIN entries e ON e.id=p.entry_id JOIN forms f ON f.entry_id=e.id
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
        tags = sorted({tag for sense in senses for tag in sense['tags']})
        classes = sorted({('v5' if r.startswith('v5') else 'vs' if r.startswith('vs') else 'v1' if r.startswith('v1') else r) for r in rules.split()} & {'v1','v5','vs','vk','vz','adj-i'})
        yield [term, reading, ' '.join(tags), ' '.join(classes), 0, list(dict.fromkeys(glosses)), sequence(identity), '']


def export(build, output, revision, language, optimize=True):
    if language not in LANGUAGES:
        raise ValueError('Unsupported definition language')
    db = sqlite3.connect(Path(build).resolve().as_uri()+'?mode=ro', uri=True)
    db.execute('PRAGMA trusted_schema=OFF')
    names = {'en': 'English', 'de': 'German'}
    stem = edition_stem(language, revision) if language in names else 'Kotoba_Atlas_'+language+'_v'+revision.replace('.', '_').replace('-', '_')
    destination = Path(output)/(stem+'.zip')
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.writestr('index.json', json.dumps({'title': 'Kotoba Atlas '+names.get(language, language),
                'format': 3, 'revision': revision, 'sequenced': True, 'sourceLanguage': 'ja', 'targetLanguage': language,
                'author': 'Kotoba Atlas contributors', 'url': 'https://github.com/Somamill/kotoba-atlas',
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
