#!/usr/bin/env python3
"""Replay the pinned public legacy Migaku Anki word importer against real SQLite.

This does not run or certify the current Migaku browser Early Access extension.
The upstream GPL source is supplied separately, never bundled in release ZIPs.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import resource
import sqlite3
import subprocess
import sys
import time
from types import SimpleNamespace
import zipfile

REVISION = '0bc88ae46fbdc1df4d23752b3056cb25a2fd3ca0'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    revision = subprocess.check_output(['git', '-C', str(args.source), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != REVISION:
        raise ValueError('Unexpected upstream source revision; review it before execution')
    if args.database.exists():
        raise FileExistsError('Choose a fresh scratch database; installed dictionaries are never modified')
    namespace = {'json': json, 'zipfile': zipfile, 're': re, 'getFrequencyList': lambda _language: {}}
    source = ast.parse((args.source / 'src/dictionaryManager.py').read_text())
    names = {'importDict', 'natural_sort', 'loadDict', 'getAdjustedTerm', 'getAdjustedPronunciation',
             'getAdjustedDefinition', 'handleYomiDictEntry', 'handleMiDictEntry'}
    functions = [node for node in source.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(functions) == len(names)
    exec(compile(ast.Module(body=functions, type_ignores=[]), '<pinned-migaku-importer>', 'exec'), namespace)
    database_tree = ast.parse((args.source / 'src/dictdb.py').read_text())
    methods = next(node for node in database_tree.body if isinstance(node, ast.ClassDef) and node.name == 'DictDB')
    methods = [node for node in methods.body if isinstance(node, ast.FunctionDef) and node.name in {'createDB', 'importToDict'}]
    exec(compile(ast.Module(body=methods, type_ignores=[]), '<pinned-migaku-database>', 'exec'), namespace)

    class Database:
        def __init__(self):
            self.conn = sqlite3.connect(args.database)
            self.c = self.conn.cursor()
        def getLangId(self, _language):
            return 1
        def addDict(self, name, _language, _header):
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
                raise ValueError('Unsafe legacy SQL dictionary name')
            namespace['createDB'](self, 'l1name' + name)
        def importToDict(self, name, rows):
            namespace['importToDict'](self, name, rows)
        def commitChanges(self):
            self.conn.commit()

    db = Database()
    window = SimpleNamespace(miDictDB=db)
    namespace.update(mw=window, aqt=SimpleNamespace(mw=window))
    with zipfile.ZipFile(args.archive) as archive:
        index = json.loads(archive.read('index.json'))
    name = args.archive.stem
    started = time.perf_counter()
    namespace['importDict']('Japanese', str(args.archive), name)
    table = 'l1name' + name
    count = db.c.execute('SELECT count(*) FROM ' + table).fetchone()[0]
    examples = {}
    for term in ['羅睺', '物ノ怪', '鎌かけて', '鎌かける', 'てぇてぇ', 'ぬまる', '沼る', '推し活', 'ワンチャン']:
        rows = db.c.execute('SELECT pronunciation,pos,definition FROM ' + table + ' WHERE term=?', (term,)).fetchall()
        assert rows, 'Missing lookup after import: ' + term
        examples[term] = [{'reading': row[0], 'pos': row[1], 'definition': row[2][:200]} for row in rows]
    assert any('v1' in row['pos'].split() for row in examples['鎌かける'])
    seconds = time.perf_counter() - started
    report = {'archive': args.archive.name, 'revision': index['revision'], 'upstream_revision': revision,
              'scope': 'Public legacy Anki importer core and actual SQLite table/index/insertion functions; GUI/language registry facade; no external frequency list',
              'entries_imported': count, 'elapsed_seconds': round(seconds, 3),
              'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024),
              'archive_sha256': hashlib.file_digest(args.archive.open('rb'), 'sha256').hexdigest(),
              'regressions': examples, 'current_migaku_browser_tested': False}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['archive', 'entries_imported', 'elapsed_seconds', 'peak_rss_bytes']}), flush=True)
    db.conn.close()


if __name__ == '__main__':
    main()
