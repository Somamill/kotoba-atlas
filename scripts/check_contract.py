"""Validate release bytes, expanded indexes and real lookups before publication."""
import argparse
from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import fastjsonschema
from contract import sha
from contract_lookup import AtlasIndex


def check(directory):
    root = Path(directory)
    manifest = json.loads((root/'consumer-manifest.json').read_text())
    fastjsonschema.compile(json.loads((Path(__file__).resolve().parents[1]/'schemas/consumer-manifest-v2.schema.json').read_text()))(manifest)
    if manifest['schemaVersion'] != 2:
        raise ValueError('Unsupported manifest schema')
    core = None; packs = {}; descriptors = {}
    for descriptor in manifest['packages']:
        compressed = root/descriptor['file']
        if compressed.name != descriptor['file'] or descriptor['file'] in descriptors:
            raise ValueError('Unsafe or duplicate package filename')
        if compressed.stat().st_size != descriptor['compressedBytes'] or sha(compressed) != descriptor['sha256']:
            raise ValueError('Invalid compressed release package')
        digest = hashlib.sha256(); size = 0
        with gzip.open(compressed, 'rb') as stream:
            while chunk := stream.read(1024*1024):
                size += len(chunk)
                if size > descriptor['uncompressedBytes']:
                    raise ValueError('Expanded package exceeds manifest size')
                digest.update(chunk)
        if size != descriptor['uncompressedBytes'] or digest.hexdigest() != descriptor['uncompressedSha256']:
            raise ValueError('Invalid expanded release package')
        raw = root/descriptor['file'].removesuffix('.gz')
        if sha(raw) != descriptor['uncompressedSha256']:
            raise ValueError('Test index differs from downloadable index')
        with closing(sqlite3.connect(raw.resolve().as_uri()+'?mode=ro', uri=True)) as db:
            db.execute('PRAGMA cache_size=-131072')
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Invalid SQLite package')
            about = dict(db.execute('SELECT key,value FROM about'))
            if about.get('schema') != '2' or about.get('revision') != manifest['dictionaryRevision']:
                raise ValueError('Unsupported package generation')
            if descriptor['role'] == 'language':
                if about['language'] != descriptor['language']:
                    raise ValueError('Language metadata mismatch')
                for sense_id, payload in db.execute('SELECT id,payload FROM senses'):
                    sense = json.loads(payload)
                    if sense['id'] != sense_id or sense['language'] != descriptor['language'] or not sense['glosses'] or not sense['sourceRecords']:
                        raise ValueError('Malformed structured sense')
        if descriptor['role'] == 'core': core = raw
        elif descriptor['role'] == 'language': packs[descriptor['language']] = raw
        descriptors[descriptor['file']] = descriptor
    if set(packs) != {'en','zh','es','ar','id','pt','fr','ja','ru','de'} or core is None:
        raise ValueError('Missing requested primary-language pack')
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
    finally:
        index.close()
    report = {'passed': True, 'revision': manifest['dictionaryRevision'], 'packages': len(descriptors), 'lookups': lookups}
    (root/'artifact-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    print(json.dumps(check(parser.parse_args().directory), ensure_ascii=False))
