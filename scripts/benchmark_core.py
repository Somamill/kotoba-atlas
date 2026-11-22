"""Measure two schema-2 release directories or generated consumer-fixture directories."""
import argparse
from contextlib import closing
from itertools import zip_longest
import json
from pathlib import Path
import platform
import resource
import shutil
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time

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
    'swiftPitch': (
        "SELECT DISTINCT m.mode,m.payload FROM forms f JOIN metadata m ON m.term=f.text WHERE f.entry_id=? AND f.reading=?",
        ('jmdict:ja:1579110', 'きょう')),
}
WORKLOAD = [
    ('きょう', 'en'), ('こんにち', 'en'), ('今日', 'en'), ('nowadays', 'en'),
    ('AND', 'en'), ('and', 'en'), ('Boolean', 'en'), ('はし', 'en'),
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
    return {
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
        if baseline != after.execute(objects).fetchall():
            raise ValueError(f'SQLite objects changed: {left.name}')
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
    descriptors = [{p['id']: p for p in json.loads((root/manifest_name).read_text())['packages']}
                   for root in (before, after)]
    if descriptors[0].keys() != descriptors[1].keys():
        raise ValueError('Package coverage changed')
    selected = {'core', 'language:en', 'language:de', 'language:ja'}
    indexes = [{}, {}]
    results = {}
    for package_id, first in descriptors[0].items():
        second = descriptors[1][package_id]
        paths = []
        measurements = []
        for i, (root, package) in enumerate(zip((before, after), (first, second))):
            language = package['language']
            raw = scratch/f'{i}-{package_id.replace(":", "-")}.sqlite'
            start = time.monotonic()
            if fixtures:
                if package_id == 'source-records':
                    continue
                raw = root/('atlas-'+(language or 'core')+'.sqlite')
                if sha(raw) != package['uncompressedSha256']:
                    raise ValueError('Fixture hash mismatch')
            else:
                unpack(root/package['file'], raw, package)
            measurements.append({'descriptor': package, 'verifyAndExpandSeconds': time.monotonic()-start})
            paths.append(raw)
            if package_id in selected:
                indexes[i][language or 'core'] = raw
        if paths:
            results[package_id] = {'before': measurements[0], 'after': measurements[1],
                                   'identicalRows': compare_rows(*paths)}
            if package_id not in selected and not fixtures:
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
    if fixtures:
        copy = scratch/'analyze-only.sqlite'
        shutil.copyfile(baseline_core, copy)
        baseline_core = copy
    with closing(sqlite3.connect(baseline_core)) as db:
        start = time.monotonic()
        db.execute('ANALYZE')
        db.commit()
        analysis_seconds = time.monotonic()-start
    with closing(open_db(baseline_core)) as db:
        analyze_only = profile(db, samples)
    differences = [query for query, left, right in zip(WORKLOAD, *projections) if left != right]
    return {'packages': results, 'before': profiles[0], 'after': profiles[1],
            'lookupDifferences': differences, 'analyzeOnly': analyze_only, 'analyzeSeconds': analysis_seconds}


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
