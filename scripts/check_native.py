#!/usr/bin/env python3
"""Assert full field parity between a release ZIP and its native SQLite package."""
import argparse,json,sqlite3,zipfile,re

def check(archive,database):
    db=sqlite3.connect('file:'+str(database.resolve())+'?mode=ro',uri=True)
    families={
      'term':('SELECT term,reading,tags,rules,score,gloss,sequence,term_tags FROM entries ORDER BY id',5),
      'term_meta':('SELECT term,mode,payload FROM metadata ORDER BY rowid',2),
      'kanji':('SELECT payload FROM kanji ORDER BY rowid',0),
      'tag':('SELECT payload FROM tags ORDER BY rowid',0)}
    cursors={k:db.execute(v[0]) for k,v in families.items()};counts={k:0 for k in families}
    with zipfile.ZipFile(archive) as z:
      for n in z.namelist():
        match=re.fullmatch(r'(term|term_meta|kanji|tag)_bank_\d+\.json',n)
        if match:
          kind=match[1];expected=json.loads(z.read(n))
          actual=cursors[kind].fetchmany(len(expected))
          assert len(actual)==len(expected),(kind,'missing rows')
          for a,e in zip(actual,expected):
            a=list(a);pos=families[kind][1];a[pos]=json.loads(a[pos])
            if kind in {'kanji','tag'}:a=a[0]
            assert a==e,(kind,counts[kind])
            counts[kind]+=1
        elif n.endswith(('.txt','.md')) or n=='SOURCES.json' or n.startswith(('LICENSE','licenses/')):
          row=db.execute('SELECT content FROM notices WHERE name=?',(n,)).fetchone()
          assert row and row[0]==z.read(n),('notice',n)
    for kind,cursor in cursors.items():assert cursor.fetchone() is None,('extra rows',kind)
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    db.close()
    return {'all_source_fields_retained':True,'counts':counts}
if __name__=='__main__':
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);p.add_argument('database',type=Path)
    a=p.parse_args();print(json.dumps(check(a.archive,a.database)))
