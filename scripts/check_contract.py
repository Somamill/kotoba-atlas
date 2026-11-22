"""Validate release bytes, expanded indexes and real lookups before publication."""
import argparse
from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import fastjsonschema
from contract import LANGUAGES, sha
from contract_lookup import AtlasIndex


def unpack(compressed, raw, descriptor):
    if compressed.stat().st_size != descriptor['compressedBytes'] or sha(compressed) != descriptor['sha256']:
        raise ValueError('Invalid compressed release package')
    digest = hashlib.sha256(); size = 0
    with gzip.open(compressed, 'rb') as stream, raw.open('xb') as output:
        while chunk := stream.read(1024*1024):
            size += len(chunk)
            if size > descriptor['uncompressedBytes']:
                raise ValueError('Expanded package exceeds manifest size')
            digest.update(chunk); output.write(chunk)
    if size != descriptor['uncompressedBytes'] or digest.hexdigest() != descriptor['uncompressedSha256']:
        raise ValueError('Invalid expanded release package')


def validate_descriptors(manifest, require_core_binding):
    packages = {}
    files = set()
    revision = manifest['dictionaryRevision']
    for descriptor in manifest['packages']:
        role, language = descriptor['role'], descriptor['language']
        identity = role+(':'+language if role == 'language' and language else '')
        filename = descriptor['file']
        url = 'https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v'+revision+'/'+filename
        if (identity != descriptor['id'] or identity in packages or filename in files
                or Path(filename).name != filename or (role == 'language') != (language is not None)
                or descriptor['dictionaryRevision'] != revision or descriptor['url'] != url):
            raise ValueError('Unsafe, duplicate or inconsistent package descriptor')
        packages[identity] = descriptor
        files.add(filename)
    if set(packages) != {'core', 'source-records', *('language:'+language for language in LANGUAGES)}:
        raise ValueError('Missing or unexpected release package')
    core_hash = packages['core']['uncompressedSha256']
    for identity, descriptor in packages.items():
        if identity != 'core' and (require_core_binding or 'coreSha256' in descriptor):
            if descriptor.get('coreSha256') != core_hash:
                raise ValueError('Manifest package does not match lexical core')
    return packages


def check(directory, require_core_binding=False):
    with tempfile.TemporaryDirectory(prefix='atlas-verified-indexes-') as temporary:
        return check_indexes(Path(directory), Path(temporary), require_core_binding)


def check_indexes(root, temporary, require_core_binding=False):
    manifest = json.loads((root/'consumer-manifest.json').read_text())
    fastjsonschema.compile(json.loads((Path(__file__).resolve().parents[1]/'schemas/consumer-manifest-v2.schema.json').read_text()))(manifest)
    if manifest['schemaVersion'] != 2:
        raise ValueError('Unsupported manifest schema')
    descriptors = validate_descriptors(manifest, require_core_binding)
    core = None
    packs = {}
    for descriptor in descriptors.values():
        raw = temporary/descriptor['file'].removesuffix('.gz')
        unpack(root/descriptor['file'], raw, descriptor)
        with closing(sqlite3.connect(raw.resolve().as_uri()+'?mode=ro', uri=True)) as db:
            db.execute('PRAGMA cache_size=-131072')
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Invalid SQLite package')
            about = dict(db.execute('SELECT key,value FROM about'))
            if about.get('schema') != '2' or about.get('revision') != manifest['dictionaryRevision'] or about.get('format') != {'core':'atlas-core','language':'atlas-language','source-records':'atlas-source-records'}[descriptor['role']]:
                raise ValueError('Unsupported package generation')
            if descriptor['role'] != 'core' and about.get('core_sha256') != descriptors['core']['uncompressedSha256']:
                raise ValueError('Package does not match lexical core')
            if descriptor['role'] == 'language':
                if about['language'] != descriptor['language']:
                    raise ValueError('Language metadata mismatch')
                for sense_id, payload in db.execute('SELECT id,payload FROM senses'):
                    sense = json.loads(payload)
                    if sense['id'] != sense_id or sense['language'] != descriptor['language'] or not sense['glosses'] or not sense['sourceRecords']:
                        raise ValueError('Malformed structured sense')
                    restrictions = sense.get('restrictions') or {}
                    for key in ['spellings', 'readings']:
                        values = restrictions.get(key, [])
                        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                            raise ValueError('Malformed source form restrictions')

        if descriptor['role'] == 'source-records': raw.unlink()
        if descriptor['role'] == 'core': core = raw
        elif descriptor['role'] == 'language': packs[descriptor['language']] = raw
    lookups = []
    index = AtlasIndex(core, packs)
    try:
        for query, identity in [('ノリのいい','jmdict:ja:2238120'),('物ノ怪','jmdict:ja:1502400'),
                ('鎌かけてる','jmdict:ja:1852260'),('沼ってる','jmdict:ja:2854926'),('羅睺','jmdict:ja:2854053'),
                ('隠密局','atlas:ja:fiction:black-torch:kougi-onmitsu-kyoku')]:
            results = index.search(query, 'de')
            matches = [entry for entry in results if entry['entryId'] == identity]
            if len(matches) != 1:
                raise ValueError('Required lookup missing/duplicated: '+query)
            lookups.append({'query': query, 'entryId': identity, 'definitionLanguage': matches[0]['definitionLanguage']})
        clean = next(e for e in index.search('ノリのいい','de') if e['entryId']=='jmdict:ja:2238120')
        if clean['senses'][0]['glosses'] != ['easy to get into (e.g. of music, etc.)', 'easily getting into (a certain mood, etc.)'] or not clean['fallback']:
            raise ValueError('Issue #5 package regression')
        if not any(e['entryId']=='jmdict:ja:1502400' for e in index.search('Dämon','de')):
            raise ValueError('German reverse lookup failed')
        primary = next(e for e in index.search('沼ってる','de') if e['entryId']=='jmdict:ja:2854926')
        if primary['fallback'] or any(s['language'] != 'de' for s in primary['senses']):
            raise ValueError('Primary-present fallback suppression failed')
        japanese = index.search('実体','ja')
        if not any(any(s['kind']=='definition' and s['language']=='ja' for s in e['senses']) for e in japanese):
            raise ValueError('No actual Japanese definition')
        def meanings(query, identity):
            return [gloss for entry in index.search(query, 'en') if entry['entryId'] == identity for sense in entry['senses'] for gloss in sense['glosses']]
        today = 'jmdict:ja:1579110'
        if ('these days' in meanings('きょう', today)
                or 'these days' not in meanings('こんにち', today)
                or 'these days' not in meanings('今日', today)):
            raise ValueError('Reading-scoped senses changed')
        reverse = next(entry for entry in index.search('nowadays', 'en') if entry['entryId'] == today)
        if reverse['matchedForm']['reading'] != 'こんにち':
            raise ValueError('Reverse lookup lost matched reading')
        conjunction = 'jmdict:ja:1020470'
        if ('AND (Boolean operator)' in meanings('&', conjunction)
                or 'AND (Boolean operator)' in meanings('and', conjunction)
                or 'AND (Boolean operator)' not in meanings('AND', conjunction)
                or 'AND (Boolean operator)' not in meanings('Boolean', conjunction)):
            raise ValueError('Spelling-scoped senses changed')
    finally:
        index.close()
    report = {'passed': True, 'revision': manifest['dictionaryRevision'], 'packages': len(descriptors), 'lookups': lookups}
    (root/'artifact-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    print(json.dumps(check(parser.parse_args().directory), ensure_ascii=False))
