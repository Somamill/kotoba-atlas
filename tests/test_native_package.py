import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_package import build
from editions import edition_stem
from prepare_beta import package


class NativePackageTests(unittest.TestCase):
    def test_preserves_native_word_fields_and_duplicate_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source.zip'
            rows=[['片仮名','カタカナ','n','',100,['test definition'],42,'rare']]
            with zipfile.ZipFile(source,'w') as z:
                z.writestr('index.json',json.dumps({'title':'Kotoba Atlas — English','format':3,'revision':'1.0.3','targetLanguage':'en'}))
                z.writestr('term_bank_1.json',json.dumps(rows,ensure_ascii=False))
                z.writestr('term_meta_bank_1.json',json.dumps([['片仮名','freq',3]]*2))
                z.writestr('NOTICES.txt','retained attribution')
            report=build(source,root/'out','1.0.4-beta.1')
            db=sqlite3.connect(next((root/'out').glob('*.sqlite')))
            row=db.execute('SELECT term,reading,tags,rules,score,gloss,sequence,term_tags FROM entries').fetchone()
            recovered=list(row);recovered[5]=json.loads(recovered[5])
            self.assertEqual(recovered,rows[0])
            self.assertEqual(db.execute('SELECT reading_key FROM entries').fetchone()[0],'かたかな')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM metadata').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT content FROM notices').fetchone()[0],b'retained attribution')
            db.close()
            self.assertEqual(report['entries'],1)

    def test_beta_archive_retains_every_non_index_member_and_has_safe_name(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source.zip'
            with zipfile.ZipFile(source,'w') as z:
                z.writestr('index.json',json.dumps({'title':'Kotoba Atlas — English','format':3,'revision':'1.0.3','targetLanguage':'en'}))
                z.writestr('term_bank_1.json','[["語","ご","","",1,["word"],-1,""]]')
            report=package(source,root/'out','1.0.4-beta.1')
            self.assertTrue(report['all_non_index_members_byte_identical'])
            self.assertEqual(edition_stem('en','1.0.4-beta.1'),'Kotoba_Atlas_English_v1_0_4_beta_1')
            with self.assertRaises(ValueError):edition_stem('en','1.0.4-beta;bad')
