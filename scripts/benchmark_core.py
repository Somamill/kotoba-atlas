"""Measure two schema-2 release directories or generated consumer-fixture directories."""
import argparse
from contextlib import closing
import gzip
import hashlib
from itertools import zip_longest
import json
from pathlib import Path
import platform
import resource
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
import zipfile

from check_contract import unpack
from contract import sha
from contract_lookup import AtlasIndex, normalized

# Direct SQL from dict. Core/AtlasContract.swift. Keep bindings representative and case intact.
SQL = {
    'swiftForms': (
        "SELECT e.rowid,f.text,e.rules,EXISTS(SELECT 1 FROM json_each(f.payload,'$.tags') WHERE value IN ('sk','ik','ok','rk','sK','iK','oK','rK')) FROM forms f JOIN entries e ON e.id=f.entry_id WHERE (f.normalized=? OR f.reading_key=?) AND (f.kind!='alias' OR NOT EXISTS(SELECT 1 FROM forms original WHERE original.entry_id=f.entry_id AND original.text=f.text AND original.reading=f.reading AND original.kind!='alias')) LIMIT 240",
        (normalized('きょう'), normalized('きょう'))),
    'swiftPrefix': (
        "SELECT e.rowid FROM forms f JOIN entries e ON e.id=f.entry_id WHERE f.normalized>=? AND f.normalized<? LIMIT 80",
        ('食', '食\U0010ffff')),
    'swiftReverse': (
        "SELECT e.rowid,e.id,r.sense_id,r.language,form_hint FROM reverse_keys r JOIN entries e ON e.id=r.entry_id WHERE r.id IN (SELECT rowid FROM reverse_search WHERE reverse_search MATCH ? ORDER BY rank LIMIT 240)",
        ('"nowadays"',)),
    'swiftHeadwords': (
        "SELECT payload FROM forms WHERE entry_id=? ORDER BY CASE kind WHEN 'headword' THEN 0 WHEN 'reading' THEN 1 ELSE 2 END,json_extract(payload,'$.common') DESC,COALESCE((SELECT json_extract(r.payload,'$.common') FROM forms r WHERE r.entry_id=forms.entry_id AND r.text=forms.reading AND r.kind='reading' LIMIT 1),0) DESC,text,reading",
        ('jmdict:ja:1579110',)),
    'swiftPitch': (
        "SELECT DISTINCT m.mode,m.payload FROM forms f JOIN metadata m ON m.term=f.text WHERE f.entry_id=? AND f.reading=?",
        ('jmdict:ja:1579110', 'きょう')),
}
WORKLOAD = [
    ('きょう', 'en'), ('こんにち', 'en'), ('今日', 'en'), ('nowadays', 'en'),
    ('AND', 'en'), ('and', 'en'), ('Boolean', 'en'), ('はし', 'en'), ('ワンチャン', 'en'),
    ('鎌かけてる', 'de'), ('Dämon', 'de'), ('物ノ怪', 'de'), ('ノリのいい', 'de'),
    ('沼ってる', 'de'), ('隠密局', 'de'), ('実体', 'ja'),
]


def timed(call, samples):
    durations = []
    for _ in range(samples):
        start = time.perf_counter_ns()
        call()
        durations.append((time.perf_counter_ns()-start)/1e6)
    return {'medianMs': statistics.median(durations), 'maxMs': max(durations),
            'samplesMs': durations}


def profile(db, samples):
    entry_bytes, sense_bytes, hint_bytes = db.execute('''
        SELECT sum(length(CAST(entry_id AS BLOB))),sum(length(CAST(sense_id AS BLOB))),
               sum(length(CAST(form_hint AS BLOB))) FROM reverse_keys
    ''').fetchone()
    return {
        'reverseKeyPayloadBytes': {'entryId': entry_bytes, 'senseId': sense_bytes, 'formHint': hint_bytes},
        'stats': db.execute("SELECT count(*) FROM sqlite_schema WHERE name='sqlite_stat1'").fetchone()[0] == 1,
        'dbstat': {name: {'bytes': size, 'unusedBytes': unused}
                   for name, size, unused in db.execute(
                       'SELECT name,sum(pgsize),sum(unused) FROM dbstat GROUP BY name ORDER BY name')},
        'queries': {name: {'sql': sql, 'bindings': args,
                           'plan': [row[3] for row in db.execute('EXPLAIN QUERY PLAN '+sql, args)],
                           **timed(lambda: db.execute(sql, args).fetchall(), samples)}
                    for name, (sql, args) in SQL.items()},
    }


def open_db(path):
    return sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)


def compare_rows(left, right):
    """Check every user table and FTS shadow table, retaining rowid as a lookup tie-breaker."""
    with closing(open_db(left)) as before, closing(open_db(right)) as after:
        objects = "SELECT name,type,sql FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
        baseline = before.execute(objects).fetchall()
        revised = after.execute(objects).fetchall()
        if baseline != revised:
            expected = [(name, kind, sql.replace('forms(text,reading,entry_id)', 'forms(text)')
                         if name == 'spelling_lookup' else sql) for name, kind, sql in baseline]
            if expected != revised:
                raise ValueError(f'Consumer SQLite objects changed unexpectedly: {left.name}')
        rows = {}
        for name, kind, definition in baseline:
            if kind != 'table' or definition.startswith('CREATE VIRTUAL TABLE'):
                continue
            if 'WITHOUT ROWID' in definition.upper():
                keys = sorted((row[5], row[0]+1) for row in before.execute(f'PRAGMA table_info("{name}")') if row[5])
                query = f'SELECT * FROM "{name}" ORDER BY '+','.join(str(column) for _, column in keys)
            else:
                query = f'SELECT rowid,* FROM "{name}"'
                if name == 'about':
                    query += " WHERE key!='core_sha256'"
                query += ' ORDER BY rowid'
            count = 0
            for first, second in zip_longest(before.execute(query), after.execute(query)):
                if first != second:
                    raise ValueError(f'Data changed: {left.name}/{name} row {count+1}')
                count += 1
            rows[name] = count
        return rows


def compare(before, after, scratch, samples):
    fixtures = (before/'atlas-manifest.json').is_file()
    manifest_name = 'atlas-manifest.json' if fixtures else 'consumer-manifest.json'
    manifests = [json.loads((root/manifest_name).read_text()) for root in (before, after)]
    descriptors = [{p['id']: p for p in manifest.pop('packages')} for manifest in manifests]
    if descriptors[0].keys() != descriptors[1].keys() or manifests[0] != manifests[1]:
        raise ValueError('Package coverage or consumer metadata changed')
    selected = {'core', 'language:en', 'language:de', 'language:ja'}
    indexes = [{}, {}]
    results = {}
    for package_id, first in descriptors[0].items():
        second = descriptors[1][package_id]
        byte_fields = {'sha256', 'uncompressedSha256', 'compressedBytes', 'uncompressedBytes', 'coreSha256'}
        if {k: v for k, v in first.items() if k not in byte_fields} != {k: v for k, v in second.items() if k not in byte_fields}:
            raise ValueError(f'Package metadata changed: {package_id}')
        if fixtures and package_id == 'source-records':
            continue
        paths = []
        measurements = []
        for i, (root, package) in enumerate(zip((before, after), (first, second))):
            language = package['language']
            raw = scratch/f'{i}-{package_id.replace(":", "-")}.sqlite'
            compressed = root/package['file']
            if fixtures:
                compressed = raw.with_suffix('.sqlite.gz')
                fixture = root/('atlas-'+(language or 'core')+'.sqlite')
                with compressed.open('xb') as stream, gzip.GzipFile(filename='', mode='wb', fileobj=stream, compresslevel=6, mtime=0) as archive:
                    archive.write(fixture.read_bytes())
            start = time.monotonic()
            unpack(compressed, raw, package)
            measurements.append({'descriptor': package, 'verifyAndExpandSeconds': time.monotonic()-start})
            paths.append(raw)
            if package_id in selected:
                indexes[i][language or 'core'] = raw
        results[package_id] = {'before': measurements[0], 'after': measurements[1],
                               'identicalRows': compare_rows(*paths)}
        if package_id not in selected:
            for path in paths:
                path.unlink()
    baseline_core = indexes[0]['core']
    profiles = []
    projections = []
    for index in indexes:
        core = index.pop('core')
        atlas = AtlasIndex(core, index)
        try:
            projections.append([atlas.search(query, language) for query, language in WORKLOAD])
            profiles.append({'sql': profile(atlas.db, samples),
                             'lookup': [{'query': query, 'language': language,
                                         **timed(lambda: atlas.search(query, language), samples)}
                                        for query, language in WORKLOAD]})
        finally:
            atlas.close()
    with closing(sqlite3.connect(baseline_core)) as db:
        start = time.monotonic()
        db.execute('ANALYZE')
        db.commit()
        analysis_seconds = time.monotonic()-start
    with closing(open_db(baseline_core)) as db:
        analyze_only = profile(db, samples)
    differences = [query for query, left, right in zip(WORKLOAD, *projections) if left != right]
    browser = None
    for root in (before, after):
        hashes = {}
        for path in sorted(root.glob('Kotoba_Atlas_*.zip')):
            with zipfile.ZipFile(path) as archive:
                members = {}
                for member in archive.infolist():
                    if member.filename in members:
                        raise ValueError('Duplicate browser member: '+member.filename)
                    with archive.open(member) as stream:
                        members[member.filename] = hashlib.file_digest(stream, 'sha256').hexdigest()
                hashes[path.name] = members
        if browser is not None and browser != hashes:
            raise ValueError('Browser export data changed')
        browser = hashes
    return {'packages': results, 'before': profiles[0], 'after': profiles[1],
            'lookupDifferences': differences, 'browserZipMembers': {name: len(members) for name, members in browser.items()}, 'analyzeOnly': analyze_only, 'analyzeSeconds': analysis_seconds}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=15)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error('samples must be positive')
    with tempfile.TemporaryDirectory(prefix='atlas-benchmark-') as temporary:
        result = compare(args.before, args.after, Path(temporary), args.samples)
    result.update(machine=platform.machine(), platform=platform.platform(), python=platform.python_version(),
                  sqlite=sqlite3.sqlite_version, peakRSS=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  peakRSSUnit='bytes' if sys.platform == 'darwin' else 'KiB',
                  sourceLockSHA256=sha('data/sources-v2.lock.json'),
                  commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip())
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    if result['lookupDifferences']:
        raise SystemExit('Lookup projections differ; inspect report')


if __name__ == '__main__':
    main()
