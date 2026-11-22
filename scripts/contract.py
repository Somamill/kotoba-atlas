"""Atlas schema 2: one indexed lexical core plus independently installed language packs."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import zipfile
from adapters import LANGUAGES, fiction, jmdict, jmnedict, omw
from structured import unique, normalized
from structured import digest
from structured import extract


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))



def sha(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


LOOKUP_INDEXES = '''
    CREATE INDEX form_lookup ON forms(normalized,entry_id);
    CREATE INDEX spelling_lookup ON forms(text,reading,entry_id);
    CREATE INDEX reading_lookup ON forms(reading_key,entry_id);
    CREATE INDEX metadata_lookup ON metadata(term,mode);
'''


def schema(db, lookup_indexes=True):
    db.executescript('''
    PRAGMA page_size=4096;
    PRAGMA journal_mode=DELETE;
    PRAGMA cache_size=-131072;
    CREATE TABLE about(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE entries(id TEXT PRIMARY KEY,source_language TEXT NOT NULL,kind TEXT NOT NULL,rules TEXT NOT NULL);
    CREATE TABLE forms(entry_id TEXT NOT NULL,text TEXT NOT NULL,reading TEXT NOT NULL,
                       normalized TEXT NOT NULL,reading_key TEXT NOT NULL,kind TEXT NOT NULL,
                       payload TEXT NOT NULL,PRIMARY KEY(entry_id,text,reading,kind));
    CREATE TABLE sources(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
    CREATE TABLE source_records(id TEXT PRIMARY KEY,source_id TEXT NOT NULL,payload TEXT NOT NULL);
    CREATE TABLE entry_source_records(entry_id TEXT NOT NULL,record_id TEXT NOT NULL,PRIMARY KEY(entry_id,record_id));
    CREATE TABLE metadata(term TEXT NOT NULL,mode TEXT NOT NULL,payload TEXT NOT NULL,source_id TEXT NOT NULL);
    CREATE TABLE notices(name TEXT PRIMARY KEY,content BLOB NOT NULL);
    CREATE TABLE senses(id TEXT PRIMARY KEY,entry_id TEXT NOT NULL,language TEXT NOT NULL,payload TEXT NOT NULL);
    CREATE INDEX entry_senses ON senses(entry_id,language);
    ''')
    if lookup_indexes:
        db.executescript(LOOKUP_INDEXES)


class Builder:
    def __init__(self, path, revision):
        self.path = Path(path)
        self.db = sqlite3.connect(path)
        schema(self.db)
        self.db.executemany('INSERT INTO about VALUES(?,?)',
                           [('schema', '2'), ('format', 'atlas-build'), ('revision', revision)])

    def add(self, record):
        entry_id = record['id']
        language = record['sourceLanguage']
        if language not in LANGUAGES or not record['headwords']:
            raise ValueError('Invalid lexical source language or missing headwords')
        self.db.execute('INSERT OR IGNORE INTO entries VALUES(?,?,?,?)',
                        (entry_id, language, record.get('kind', 'lexical'), ' '.join(record.get('inflections', []))))
        if self.db.execute('SELECT source_language FROM entries WHERE id=?', (entry_id,)).fetchone()[0] != language:
            raise ValueError('Canonical identity changed source language')
        for form in record['headwords']:
            term, reading = form['text'], form.get('reading') or ''
            if not term.strip():
                raise ValueError('Empty headword')
            self.db.execute('INSERT OR IGNORE INTO forms VALUES(?,?,?,?,?,?,?)',
                (entry_id, term, reading, normalized(term), normalized(reading),
                 form.get('kind', 'headword'), encoded(form)))
        for source in record['sources']:
            if not source.get('license'):
                raise ValueError('Missing source licence: '+source['id'])
            self.db.execute('INSERT OR IGNORE INTO sources VALUES(?,?)', (source['id'], encoded(source)))
        for source in record['sourceRecords']:
            self.db.execute('INSERT OR IGNORE INTO source_records VALUES(?,?,?)',
                            (source['id'], source['source'], encoded(source)))
            self.db.execute('INSERT OR IGNORE INTO entry_source_records VALUES(?,?)', (entry_id, source['id']))
        for sense in record['senses']:
            if sense['language'] not in LANGUAGES or not sense['glosses'] or not sense['sourceRecords']:
                raise ValueError('Invalid sense')
            self.db.execute('INSERT OR IGNORE INTO senses VALUES(?,?,?,?)',
                            (sense['id'], entry_id, sense['language'], encoded(sense)))
            stored = self.db.execute('SELECT entry_id,language,payload FROM senses WHERE id=?', (sense['id'],)).fetchone()
            if stored != (entry_id, sense['language'], encoded(sense)):
                previous = json.loads(stored[2])
                semantic = lambda value: {k: v for k, v in value.items() if k not in {'examples', 'sourceRecords', 'order'}}
                if stored[:2] != (entry_id, sense['language']) or semantic(previous) != semantic(sense):
                    raise ValueError('Conflicting stable sense identity: '+sense['id'])
                previous['examples'] = unique(previous.get('examples', [])+sense.get('examples', []))
                previous['sourceRecords'] = unique(previous['sourceRecords']+sense['sourceRecords'])
                self.db.execute('UPDATE senses SET payload=? WHERE id=?', (encoded(previous), sense['id']))

    def finish(self):
        # Checkpoints are intermediate only; export still requires every validation below.
        self.db.commit()
        assert self.db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not self.db.execute('SELECT id FROM senses WHERE entry_id NOT IN (SELECT id FROM entries) LIMIT 1').fetchone()
        self.db.execute('ANALYZE')
        self.db.commit()

    def close(self):
        self.db.close()


def package(path, role, revision, language=None):
    compressed = path.with_suffix(path.suffix+'.gz')
    with path.open('rb') as source, compressed.open('wb') as destination:
        with gzip.GzipFile(filename='', fileobj=destination, mode='wb', mtime=0, compresslevel=6) as output:
            shutil.copyfileobj(source, output, 1024*1024)
    return {'id': role+(':'+language if language else ''), 'role': role, 'language': language,
            'format': 'atlas-sqlite-v2+gzip', 'schemaVersion': 2, 'dictionaryRevision': revision,
            'file': compressed.name, 'sha256': sha(compressed), 'uncompressedSha256': sha(path),
            'url': 'https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v'+revision+'/'+compressed.name,
            'compressedBytes': compressed.stat().st_size, 'uncompressedBytes': path.stat().st_size,
            'compatibility': {'requiredSchema': 2, 'requiredCapabilities': ['shared-core', 'entry-language-fallback', 'form-restrictions']}}


def add_aliases(builder, path):
    source = {'id': 'atlas-spelling-aliases', 'license': 'CC-BY-SA-4.0',
              'attribution': 'Kotoba Atlas contributors; existing documented spelling/phrase aliases.'}
    for alias in json.loads(Path(path).read_text()):
        targets = builder.db.execute('SELECT DISTINCT entry_id FROM forms WHERE text=?', (alias['canonical'],)).fetchall()
        if not targets:
            raise ValueError('Alias has no verified canonical target: '+alias['term'])
        record_id = source['id']+':'+digest(alias)
        for (entry_id,) in targets:
            builder.add({'id': entry_id, 'sourceLanguage': 'ja', 'headwords': [
                {'text': alias['term'], 'reading': alias['reading'], 'kind': 'alias',
                 'canonicalSpelling': alias['canonical'], 'sourceRecord': record_id}],
                'sources': [source], 'sourceRecords': [{'id': record_id, 'source': source['id'], 'record': alias}],
                'senses': [], 'inflections': []})


def add_source_redirects(builder, path, spec):
    resolved, unresolved = 0, []
    source = {k: v for k, v in spec.items() if k not in {'path', 'kind'}}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.startswith('term_bank_') or not name.endswith('.json'):
                continue
            for row in json.loads(archive.read(name)):
                if row[6] >= 0:
                    continue
                record = extract(row, dict(source, namespace='jmdict'), 'en')
                for redirect in record['redirects']:
                    targets = builder.db.execute('''SELECT DISTINCT entry_id FROM forms
                        WHERE text=? AND (? IS NULL OR reading=?) AND entry_id LIKE 'jmdict:ja:%' ''',
                        (redirect['term'], redirect['reading'], redirect['reading'])).fetchall()
                    if not targets:
                        unresolved.append({'term': row[0], 'target': redirect['term'], 'reading': redirect['reading']})
                    for (entry_id,) in targets:
                        raw = record['sourceRecords'][0]
                        builder.add({'id': entry_id, 'sourceLanguage': 'ja', 'inflections': [],
                            'headwords': [{'text': row[0], 'reading': row[1] or redirect['reading'],
                                'kind': 'alias', 'sourceRecord': raw['id'], 'canonicalSpelling': redirect['term']}],
                            'sources': [source], 'sourceRecords': [raw], 'senses': []})
                        resolved += 1
    return {'resolved': resolved, 'unresolved': unresolved}


def add_usage(builder, path):
    source = {'id': 'atlas-usage', 'license': 'CC-BY-SA-4.0',
              'attribution': 'Original usage annotations/examples and German adaptations by Kotoba Atlas contributors.'}
    identities = json.loads((Path(__file__).resolve().parents[1]/'data/usage-identities.json').read_text())
    for item in json.loads(Path(path).read_text()):
        entry_id = identities.get(item['term'], 'atlas:ja:usage:'+digest([item['term'], item['reading']]))
        if item['term'] in identities and not builder.db.execute('SELECT 1 FROM entries WHERE id=?', (entry_id,)).fetchone():
            raise ValueError('Curated usage identity missing from source: '+entry_id)
        record_id = source['id']+':'+digest(item)
        senses = []
        for language in ['en', 'de']:
            senses.append({'id': entry_id+':sense:'+language+':'+digest(item[language]),
                'language': language, 'kind': 'editorial-usage', 'glosses': [item[language]],
                'tags': item['tags'].split(), 'restrictions': {}, 'sourceRecords': [record_id],
                'register': item['register_'+language],
                'examples': [{'text': item['example']['ja'], 'translation': item['example'][language],
                              'translationLanguage': language}], 'references': item['sources']})
        for sense in senses:
            sense['id'] = entry_id+':usage:'+sense['language']+':'+digest({k:v for k,v in sense.items() if k not in {'id','sourceRecords'}})
        builder.add({'id': entry_id, 'sourceLanguage': 'ja', 'headwords': [
            {'text': item['term'], 'reading': item['reading'], 'kind': 'headword'}],
            'sources': [source], 'sourceRecords': [{'id': record_id, 'source': source['id'], 'record': item}],
            'inflections': item['rules'].split(), 'senses': senses})


def add_legacy_metadata(builder, compressed, spec):
    temporary = Path(compressed).with_suffix('.sqlite.part')
    try:
        with gzip.open(compressed, 'rb') as source, temporary.open('wb') as target:
            total = 0
            while chunk := source.read(1024*1024):
                total += len(chunk)
                if total > spec['uncompressedBytes']:
                    raise ValueError('Metadata package exceeds its size limit')
                target.write(chunk)
        if total != spec['uncompressedBytes'] or sha(temporary) != spec['uncompressedSha256']:
            raise ValueError('Metadata source expansion failed integrity checks')
        original = sqlite3.connect(temporary.resolve().as_uri()+'?mode=ro', uri=True)
        try:
            builder.db.execute('INSERT INTO sources VALUES(?,?)', (spec['id'], encoded(spec)))
            builder.db.executemany('INSERT INTO metadata VALUES(?,?,?,?)',
                ((*row, spec['id']) for row in original.execute('SELECT term,mode,payload FROM metadata')))
            builder.db.execute('CREATE TABLE kanji(term TEXT PRIMARY KEY,payload TEXT NOT NULL)')
            builder.db.executemany('INSERT INTO kanji VALUES(?,?)', original.execute('SELECT term,payload FROM kanji'))
            builder.db.execute('CREATE TABLE tags(name TEXT PRIMARY KEY,payload TEXT NOT NULL)')
            builder.db.executemany('INSERT INTO tags VALUES(?,?)', original.execute('SELECT name,payload FROM tags'))
            builder.db.executemany('INSERT OR IGNORE INTO notices VALUES(?,?)',
                ((spec['id']+'/'+name, data) for name, data in original.execute('SELECT name,content FROM notices')))
        finally:
            original.close()
    finally:
        temporary.unlink(missing_ok=True)


def language_coverage(source):
    """One corpus pass per count, separating Japanese from auxiliary headwords."""
    result = {language: {} for language in LANGUAGES}
    for language, origin, entries, senses, examples in source.execute("""
        SELECT s.language,e.source_language,count(DISTINCT e.id),count(*),
            sum(json_array_length(s.payload,'$.examples'))
        FROM senses s JOIN entries e ON e.id=s.entry_id GROUP BY s.language,e.source_language"""):
        result[language][origin] = {'sourceLanguage': origin, 'primaryLanguageEntries': entries,
            'primaryLanguageSenses': senses, 'exampleReferences': examples or 0, 'senseKinds': {}}
    for language, origin, kind, count in source.execute("""
        SELECT s.language,e.source_language,json_extract(s.payload,'$.kind'),count(*)
        FROM senses s JOIN entries e ON e.id=s.entry_id
        GROUP BY s.language,e.source_language,json_extract(s.payload,'$.kind')"""):
        result[language][origin]['senseKinds'][kind] = count
    return {language: list(origins.values()) for language, origins in result.items()}


def export(build_path, output, revision):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(build_path)
    source.execute('PRAGMA cache_size=-262144')
    stem = 'Kotoba_Atlas_'+revision.replace('.', '_').replace('-', '_')
    core = output/(stem+'_Core.sqlite')
    if core.exists():
        raise FileExistsError(core)
    destination = sqlite3.connect(core)
    schema(destination, lookup_indexes=False)
    destination.executescript('DROP TABLE senses; DROP TABLE source_records; DROP TABLE entry_source_records;')
    destination.execute('ATTACH DATABASE ? AS original', (str(Path(build_path).resolve()),))
    for table in ['about', 'entries', 'forms', 'sources', 'metadata', 'notices']:
        destination.execute('INSERT INTO '+table+' SELECT * FROM original.'+table)
    tables = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table, key in [('kanji', 'term'), ('tags', 'name')]:
        if table in tables:
            destination.execute('CREATE TABLE '+table+'('+key+' TEXT PRIMARY KEY,payload TEXT NOT NULL)')
            destination.execute('INSERT INTO '+table+' SELECT * FROM original.'+table)
    destination.commit()
    destination.execute('DETACH DATABASE original')
    destination.executescript(LOOKUP_INDEXES)
    destination.executescript('''
        CREATE TABLE reverse_keys(id INTEGER PRIMARY KEY,entry_id TEXT NOT NULL,sense_id TEXT NOT NULL,language TEXT NOT NULL,form_hint TEXT NOT NULL);
        CREATE VIRTUAL TABLE reverse_search USING fts5(gloss,content='',tokenize='unicode61 remove_diacritics 2');''')
    for sense_id, entry_id, language, payload in source.execute('SELECT id,entry_id,language,payload FROM senses ORDER BY id'):
        sense = json.loads(payload)
        restrictions = sense.get('restrictions') or {}
        hint = {key: values for key, values in restrictions.items() if key in {'spellings', 'readings'} and values and '*' not in values}
        cursor = destination.execute('INSERT INTO reverse_keys(entry_id,sense_id,language,form_hint) VALUES(?,?,?,?)',
                                     (entry_id, sense_id, language, encoded(hint)))
        destination.execute('INSERT INTO reverse_search(rowid,gloss) VALUES(?,?)',
                            (cursor.lastrowid, '\n'.join(unique(sense['glosses']+sense.get('equivalents', [])))))
    destination.execute("UPDATE about SET value='atlas-core' WHERE key='format'")
    destination.execute("INSERT INTO about VALUES('capabilities',?)", (encoded(['shared-core', 'entry-language-fallback', 'form-restrictions']),))
    destination.execute('ANALYZE')
    destination.commit(); destination.close()
    packages = [package(core, 'core', revision)]
    core.unlink()
    originals = output/(stem+'_Source_Records.sqlite')
    if originals.exists():
        raise FileExistsError(originals)
    archive = sqlite3.connect(originals)
    archive.executescript('''CREATE TABLE about(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE source_records(id TEXT PRIMARY KEY,source_id TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE entry_source_records(entry_id TEXT NOT NULL,record_id TEXT NOT NULL,PRIMARY KEY(entry_id,record_id));
        CREATE TABLE sources(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
        CREATE TABLE notices(name TEXT PRIMARY KEY,content BLOB NOT NULL);''')
    archive.executemany('INSERT INTO entry_source_records VALUES(?,?)',
        source.execute('SELECT entry_id,record_id FROM entry_source_records ORDER BY entry_id,record_id'))
    archive.executemany('INSERT INTO sources VALUES(?,?)', source.execute('SELECT id,payload FROM sources ORDER BY id'))
    archive.executemany('INSERT INTO notices VALUES(?,?)', source.execute('SELECT name,content FROM notices ORDER BY name'))
    archive.executemany('INSERT INTO source_records VALUES(?,?,?)',
                        source.execute('SELECT id,source_id,payload FROM source_records ORDER BY id'))
    archive.executemany('INSERT INTO about VALUES(?,?)', [('schema', '2'), ('format', 'atlas-source-records'),
        ('revision', revision), ('core_sha256', packages[0]['uncompressedSha256'])])
    archive.commit(); archive.close()
    provenance_package = package(originals, 'source-records', revision)
    originals.unlink()
    provenance_package.update(optionalForLookup=True, coreSha256=packages[0]['uncompressedSha256'])
    packages.append(provenance_package)
    capabilities = []
    coverage = language_coverage(source)
    record_sources = {identity: sys.intern(origin) for identity, origin in source.execute('SELECT id,source_id FROM source_records')}
    for language in LANGUAGES:
        rows = source.execute('SELECT id,entry_id,payload FROM senses WHERE language=? ORDER BY id', (language,))
        pack = output/(stem+'_'+language+'.sqlite')
        if pack.exists():
            raise FileExistsError(pack)
        target = sqlite3.connect(pack)
        target.executescript('''CREATE TABLE about(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE senses(id TEXT PRIMARY KEY,entry_id TEXT NOT NULL,payload TEXT NOT NULL);
            CREATE INDEX entry_senses ON senses(entry_id);''')
        count = 0
        kinds = {}
        package_sources = set()
        for sense_id, entry_id, payload in rows:
            sense = json.loads(payload)
            target.execute('INSERT INTO senses VALUES(?,?,?)', (sense_id, entry_id, payload))
            package_sources.update(record_sources[identity] for identity in sense['sourceRecords'])
            count += 1; kinds[sense['kind']] = kinds.get(sense['kind'], 0)+1
        target.executemany('INSERT INTO about VALUES(?,?)', [('schema', '2'), ('format', 'atlas-language'),
            ('language', language), ('revision', revision), ('core_sha256', packages[0]['uncompressedSha256'])])
        target.execute('ANALYZE'); target.commit()
        assert target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        entries = target.execute('SELECT COUNT(DISTINCT entry_id) FROM senses').fetchone()[0]
        target.close()
        if count:
            descriptor = package(pack, 'language', revision, language)
            pack.unlink()
            descriptor.update(senses=count, entries=entries, senseKinds=kinds,
                              coreSha256=packages[0]['uncompressedSha256'])
            descriptor['sourceIds'] = sorted(package_sources)
            packages.append(descriptor)
        else:
            pack.unlink()
        capabilities.append({'language': language, 'primaryLanguageEntries': entries,
            'primaryLanguageSenses': count, 'senseKinds': kinds,
            'bySourceLanguage': coverage[language],
            'definitions': 'available' if kinds.get('definition') else 'unavailable',
            'translationEquivalents': bool(kinds.get('translation-equivalent')),
            'reverseLookup': bool(count), 'englishFallback': language != 'en',
            'coverage': 'partial; exact counts, not universal language coverage'})
    packages[0]['sourceIds'] = [r[0] for r in source.execute('SELECT id FROM sources ORDER BY id')]
    manifest = {'schemaVersion': 2, 'dictionaryRevision': revision,
        'channel': 'beta' if '-beta.' in revision else 'stable',
        'queryLanguages': list(LANGUAGES),
        'normalization': 'nfkc-casefold-kana-v1',
        'sourceLanguages': [r[0] for r in source.execute('SELECT DISTINCT source_language FROM entries ORDER BY source_language')],
        'fallback': {'language': 'en', 'scope': 'entry', 'primaryPresent': 'primary-only',
                     'primaryMissing': 'english-once-with-fallback-label'},
        'entryCountsBySourceLanguage': dict(source.execute('SELECT source_language,count(*) FROM entries GROUP BY source_language')),
        'packages': packages, 'capabilities': capabilities,
        'sources': [json.loads(r[0]) for r in source.execute('SELECT payload FROM sources ORDER BY id')]}
    (output/'consumer-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    source.close()
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, default=Path('data/sources-v2.lock.json'))
    parser.add_argument('--cache', type=Path, default=Path('.cache/sources-v2'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    specs = json.loads(args.sources.read_text())['sources']
    args.output.mkdir(parents=True, exist_ok=True)
    intermediate = args.output/'build.sqlite'
    if intermediate.exists():
        raise FileExistsError(intermediate)
    builder = Builder(intermediate, args.revision)
    try:
        for spec in specs:
            path = args.cache/spec['id']/'data'
            if sha(path) != spec['sha256']:
                raise ValueError('Source integrity failed: '+spec['id'])
            license_path = args.cache/spec['id']/'LICENSE'
            if spec.get('licenseFile'):
                if sha(license_path) != spec['licenseFile']['sha256']:
                    raise ValueError('Source licence integrity failed: '+spec['id'])
                builder.db.execute('INSERT INTO notices VALUES(?,?)',
                                   (spec['id']+'/LICENSE', license_path.read_bytes()))
            if spec['kind'] in {'jmdict-json', 'jmnedict-json'}:
                count = 0
                adapter = jmnedict if spec['kind'] == 'jmnedict-json' else jmdict
                for record in adapter(path, spec):
                    builder.add(record); count += 1
                builder.db.commit(); print(spec['id'], count, flush=True)
            elif spec['kind'] == 'atlas-v1-metadata':
                add_legacy_metadata(builder, path, spec)
                builder.db.commit()
                print("Metadata copied", flush=True)
        wordnets = [s for s in specs if s['kind'] == 'omw-tab']
        redirects = {}
        for spec in specs:
            if spec['kind'] == 'yomitan-redirects':
                redirects[spec['id']] = add_source_redirects(builder, args.cache/spec['id']/'data', spec)
                builder.db.commit()
                print('Redirects', spec['id'], redirects[spec['id']]['resolved'], flush=True)
        (args.output/'redirect-coverage.json').write_text(json.dumps(redirects, ensure_ascii=False, indent=2)+'\n')
        # Each pinned source has its own directory; adapter paths are local data files.
        local_specs = [dict(s, path=str((args.cache/s['id']/'data').resolve())) for s in wordnets]
        count = 0
        for record in omw(local_specs, Path('/')):
            builder.add(record); count += 1
            if count % 1000 == 0:
                builder.db.commit()
        print('WordNet entries', count, flush=True)
        for record in fiction('data/fictional-entities.json'):
            builder.add(record)
        add_aliases(builder, 'data/aliases.json')
        add_usage(builder, 'data/usage-notes.json')
        builder.finish()
    finally:
        builder.close()
    result = export(intermediate, args.output, args.revision)
    print(encoded({'packages': len(result['packages']), 'capabilities': result['capabilities']}))


if __name__ == '__main__':
    main()
