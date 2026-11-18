#!/usr/bin/env python3
"""Retag unchanged full dictionary banks for a beta; keep Chrome transport guard."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
from editions import edition_stem, check_transfer_budget

def package(source, output, version):
    if '-beta.' not in version:
        raise ValueError('This packaging path is for prereleases only.')
    compressor=shutil.which('7zz') or shutil.which('7z')
    if not compressor:raise RuntimeError('7-Zip is required.')
    with zipfile.ZipFile(source) as z:
        index=json.loads(z.read('index.json'))
    stem=edition_stem(index['targetLanguage'],version)
    output.mkdir(parents=True,exist_ok=True)
    target=output/(stem+'.zip')
    with tempfile.TemporaryDirectory(prefix='atlas-beta-') as temp:
        temp=Path(temp);candidate=temp/target.name;shutil.copy2(source,candidate)
        index['revision']=version
        index['downloadUrl']='https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v'+version+'/'+target.name
        # A beta must not move the stable update channel.
        index_name='Kotoba-Atlas-'+('German' if index['targetLanguage']=='de' else 'English')+'-index.json'
        index['indexUrl']='https://github.com/Somamill/kotoba-atlas/releases/download/atlas-v'+version+'/'+index_name
        (temp/'index.json').write_text(json.dumps(index,ensure_ascii=False,separators=(',',':')))
        subprocess.run([compressor,'u','-tzip','-mm=Deflate','-mx=9','-mtc=off','-mta=off',str(candidate),'index.json'],
                       cwd=temp,stdout=subprocess.DEVNULL,check=True,timeout=60)
        encoded=check_transfer_budget(candidate.stat().st_size)
        with zipfile.ZipFile(source) as old,zipfile.ZipFile(candidate) as new:
            assert set(old.namelist())==set(new.namelist())
            assert len(new.namelist())==len(set(new.namelist()))
            for n in old.namelist():
                if n!='index.json':assert old.read(n)==new.read(n),n
            assert new.testzip() is None
        shutil.copy2(candidate,target)
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    (output/index_name).write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
    report={'archive':target.name,'version':version,'all_non_index_members_byte_identical':True,
            'compressed_bytes':target.stat().st_size,'base64_bytes':encoded,'sha256':digest}
    (output/(stem+'.beta.json')).write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--version',required=True)
    a=p.parse_args();print(json.dumps(package(a.source,a.output,a.version)))
