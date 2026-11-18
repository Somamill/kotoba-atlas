#!/usr/bin/env python3
"""Build checksum-verified native SQLite packages from an unchanged Atlas ZIP."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import unicodedata
import zipfile
from editions import edition_stem


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def kana(text):
    return ''.join(chr(ord(c)-0x60) if 'ァ'<=c<='ヶ' else c
                   for c in unicodedata.normalize('NFKC',text))


def create_schema(db):
    db.executescript("""
    PRAGMA journal_mode=OFF;
    PRAGMA synchronous=OFF;
    PRAGMA cache_size=-65536;
    PRAGMA user_version=1;
    CREATE TABLE entries(id INTEGER PRIMARY KEY,term TEXT,reading TEXT,reading_key TEXT,tags TEXT,rules TEXT,score INTEGER,kind TEXT,rank INTEGER,gloss TEXT,sequence INTEGER,term_tags TEXT);
    CREATE TABLE kanji(term TEXT PRIMARY KEY,payload TEXT);
    CREATE TABLE metadata(term TEXT,mode TEXT,payload TEXT);
    CREATE TABLE tags(name TEXT,payload TEXT);
    CREATE TABLE notices(name TEXT PRIMARY KEY,content BLOB);
    CREATE TABLE about(key TEXT PRIMARY KEY,value TEXT);
    CREATE VIRTUAL TABLE search USING fts5(term,reading,meaning,content='',tokenize='unicode61 remove_diacritics 2');
    """)


def finish(db, version, language, source_sha, starter=False):
    db.executescript("""
    CREATE INDEX entry_terms ON entries(term,kind,score DESC);
    CREATE INDEX entry_readings ON entries(reading_key,kind,score DESC);
    CREATE INDEX metadata_terms ON metadata(term,mode);
    """)
    for k,v in [('version',version),('language',language),('source_sha256',source_sha),
                ('schema','1'),('starter',str(starter).lower())]:
        db.execute('INSERT INTO about VALUES(?,?)',(k,v))
    db.execute('ANALYZE')
    db.commit()
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'


def build(source, output, version, starter_output=None):
    with zipfile.ZipFile(source) as z:
        index=json.loads(z.read('index.json'));language=index['targetLanguage']
        stem=edition_stem(language,version)
        output.mkdir(parents=True,exist_ok=True);target=output/(stem+'.sqlite')
        temporary=target.with_suffix('.part');temporary.unlink(missing_ok=True)
        db=sqlite3.connect(temporary)
        create_schema(db);entry_count=0
        for n in z.namelist():
            if re.fullmatch(r'term_bank_\d+\.json',n):
                values=[]
                for r in json.loads(z.read(n)):
                    lexical=[g for g in r[5] if not g.startswith(('[Pitch •','[Frequency •','[Kanji •'))]
                    kind='name' if lexical and all(g.startswith('[Names •') for g in lexical) else ('lexical' if lexical else 'reference')
                    rank=2147483647
                    for g in r[5]:
                        if g.startswith('[Frequency •'):
                            ranks=re.findall(r'Rank: (\d+)(?!\d)',g)
                            if ranks:rank=min(rank,*map(int,ranks))
                    entry_count+=1
                    values.append((entry_count,r[0],r[1],kana(r[1]),r[2],r[3],r[4],kind,rank,json.dumps(r[5],ensure_ascii=False,separators=(',',':')),r[6],r[7]))
                db.executemany('INSERT INTO entries VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',values)
                db.executemany('INSERT INTO search(rowid,term,reading,meaning) VALUES(?,?,?,?)',
                               [(v[0],v[1],v[2],v[9]) for v in values if v[7]=='lexical'])
            elif re.fullmatch(r'kanji_bank_\d+\.json',n):
                db.executemany('INSERT OR REPLACE INTO kanji VALUES(?,?)',[(r[0],json.dumps(r,ensure_ascii=False)) for r in json.loads(z.read(n))])
            elif re.fullmatch(r'term_meta_bank_\d+\.json',n):
                db.executemany('INSERT INTO metadata VALUES(?,?,?)',[(r[0],r[1],json.dumps(r[2],ensure_ascii=False)) for r in json.loads(z.read(n))])
            elif re.fullmatch(r'tag_bank_\d+\.json',n):
                db.executemany('INSERT INTO tags VALUES(?,?)',[(r[0],json.dumps(r,ensure_ascii=False)) for r in json.loads(z.read(n))])
            elif n.endswith(('.txt','.md')) or n=='SOURCES.json' or n.startswith(('LICENSE','licenses/')):
                db.execute('INSERT OR REPLACE INTO notices VALUES(?,?)',(n,z.read(n)))
        source_sha=sha(source);finish(db,version,language,source_sha)
        if starter_output:
            starter_output.mkdir(parents=True,exist_ok=True)
            seed_path=starter_output/('Starter-'+language+'.sqlite');seed_path.unlink(missing_ok=True)
            seed=sqlite3.connect(seed_path);create_schema(seed)
            # Real frequent release entries, plus explicit regression examples; never mock definitions.
            entries=db.execute("""SELECT * FROM entries WHERE kind='lexical'
             ORDER BY CASE WHEN term IN ('物ノ怪','羅睺','鎌かける','鎌かけて','沼る','推し活する','食べる','楽しい','木漏れ日','日本語','学校','勉強','読書') THEN 0 ELSE 1 END,rank,id LIMIT 2000""").fetchall()
            seed.executemany('INSERT INTO entries VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',entries)
            seed.executemany('INSERT INTO search(rowid,term,reading,meaning) VALUES(?,?,?,?)',[(e[0],e[1],e[2],e[9]) for e in entries])
            for table in ['kanji','notices']:
                rows=db.execute('SELECT * FROM '+table).fetchall()
                seed.executemany('INSERT INTO '+table+' VALUES('+','.join('?' for _ in rows[0])+')',rows) if rows else None
            finish(seed,version,language,source_sha,True);seed.close()
        db.close();temporary.replace(target)
    compressed=target.with_suffix('.sqlite.gz')
    with target.open('rb') as src, compressed.open('wb') as dst:
        with gzip.GzipFile(fileobj=dst,mode='wb',compresslevel=6,mtime=0) as gz:
            while chunk:=src.read(1024*1024):gz.write(chunk)
    result={'id':language,'name':'Deutsch' if language=='de' else 'English','version':version,
            'url':'https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v'+version+'/'+compressed.name,
            'sha256':sha(compressed),'expandedSHA256':sha(target),
            'compressedBytes':compressed.stat().st_size,'expandedBytes':target.stat().st_size,'entries':entry_count}
    (output/(stem+'.native.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--version',required=True);p.add_argument('--starter-output',type=Path)
    a=p.parse_args();build(a.source,a.output,a.version,a.starter_output)
