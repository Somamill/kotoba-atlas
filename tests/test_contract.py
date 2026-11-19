import copy
import gzip
import fastjsonschema
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from adapters import fiction, jmdict, jmnedict, omw
from contract import Builder, export, normalized, sha
from structured import present
from contract_lookup import AtlasIndex, language_candidates
from consumer_fixtures import build as build_fixtures
from browser_contract import export as export_browser


class ContractTests(unittest.TestCase):
    def test_real_issue_5_survives_final_package_and_reverse_lookup(self):
        fixture = json.loads((Path(__file__).parent/'fixtures/jmdict-2238120.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root/'source.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr('jmdict.json', json.dumps({'words': [fixture]}))
            spec = {'id': 'jmdict-simplified', 'license': 'CC-BY-SA-4.0'}
            record = next(jmdict(archive, spec))
            builder = Builder(root/'build.sqlite', '1.1.0-beta.1')
            builder.add(record); builder.finish(); builder.close()
            manifest = export(root/'build.sqlite', root/'release', '1.1.0-beta.1')
            browser = export_browser(root/'build.sqlite', root/'browser', '1.1.0-beta.1', 'de', optimize=False)
            with zipfile.ZipFile(browser) as archive:
                rows = [row for name in archive.namelist() if name.startswith('term_bank_') for row in json.loads(archive.read(name))]
                selected = next(row for row in rows if row[0] == 'ノリのいい')
                self.assertEqual(selected[6], 2238120)
                self.assertEqual(selected[5], ['[English fallback]\neasy to get into (e.g. of music, etc.); easily getting into (a certain mood, etc.)'])
                self.assertTrue(all(len(row) == 8 and all(isinstance(g, str) for g in row[5]) for row in rows))

            core = None; packs = {}
            for descriptor in manifest['packages']:
                target = root/descriptor['file'].removesuffix('.gz')
                target.write_bytes(gzip.decompress((root/'release'/descriptor['file']).read_bytes()))
                if descriptor['role'] == 'core': core = target
                elif descriptor['role'] == 'language': packs[descriptor['language']] = target
            index = AtlasIndex(core, packs)
            try:
                result = index.search('ノリのいい', 'de')
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]['entryId'], 'jmdict:ja:2238120')
                self.assertTrue(result[0]['fallback'])
                self.assertEqual(result[0]['senses'][0]['glosses'],
                    ['easy to get into (e.g. of music, etc.)', 'easily getting into (a certain mood, etc.)'])
                self.assertEqual(index.search('mood', 'en')[0]['entryId'], result[0]['entryId'])
                self.assertFalse(index.search('mood', 'en')[0]['fallback'])
                with self.assertRaises(sqlite3.OperationalError):
                    index.db.execute('DELETE FROM entries')
            finally:
                index.close()

    def test_shared_consumer_regressions_and_primary_language_projection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build_fixtures(root)
            index = AtlasIndex(root/'atlas-core.sqlite', {language: root/('atlas-'+language+'.sqlite') for language in ['en', 'de']})
            try:
                cases = [('物ノ怪', 'jmdict:ja:1502400'), ('鎌かけてる', 'jmdict:ja:1852260'),
                         ('沼ってる', 'jmdict:ja:2854926'), ('羅睺', 'jmdict:ja:2854053')]
                for query, identity in cases:
                    results = index.search(query, 'de')
                    self.assertEqual([r['entryId'] for r in results].count(identity), 1, query)
                result = index.search('沼ってる', 'de')[0]
                self.assertEqual(result['entryId'], 'jmdict:ja:2854926')
                self.assertFalse(result['fallback'])
                self.assertTrue(all(s['language'] == 'de' for s in result['senses']))
                self.assertEqual(index.search('Dämon', 'de')[0]['entryId'], 'jmdict:ja:1502400')
                self.assertEqual(index.search('ワンチャン', 'de')[0]['entryId'], 'jmdict:ja:2831313')
                self.assertTrue({'jmdict:ja:2794860','jmdict:ja:2831313'} <= {r['entryId'] for r in index.search('ワンチャン', 'de')})
            finally:
                index.close()

    def test_real_names_keep_reading_lookup_without_redundant_browser_rows(self):
        fixture = json.loads((Path(__file__).parent/'fixtures/jmnedict-consumer-words.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root/'names.zip'
            with zipfile.ZipFile(archive, 'w') as zipped:
                zipped.writestr('names.json', json.dumps(fixture))
            builder = Builder(root/'build.sqlite', '1.1.0-beta.1')
            records = list(jmnedict(archive, {'id': 'jmnedict-fixture', 'license': 'CC-BY-SA-4.0'}))
            for record in records:
                builder.add(record)
            builder.finish(); builder.close()
            browser = export_browser(root/'build.sqlite', root/'browser', '1.1.0-beta.1', 'en', optimize=False)
            with zipfile.ZipFile(browser) as zipped:
                rows = [row for name in zipped.namelist() if name.startswith('term_bank_') for row in json.loads(zipped.read(name))]
            for record in records:
                written = [f for f in record['headwords'] if f['kind'] != 'reading']
                for form in written or record['headwords']:
                    self.assertTrue(any(row[0] == form['text'] and row[1] == form['reading'] for row in rows))
                if written:
                    for form in written:
                        self.assertFalse(any(row[0] == form['reading'] and row[0] != form['text'] for row in rows))

    def test_real_example_enrichment_keeps_sense_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            builder = Builder(root/'build.sqlite', '1.1.0-beta.1')
            counts = []
            for fixture, source in [('jmdict-consumer-words.json', 'words'), ('jmdict-examples-consumer-words.json', 'examples')]:
                archive = root/(source+'.zip')
                with zipfile.ZipFile(archive, 'w') as zipped:
                    zipped.writestr('words.json', (Path(__file__).parent/'fixtures'/fixture).read_bytes())
                for record in jmdict(archive, {'id': source, 'license': 'CC-BY-SA-4.0; examples CC-BY-2.0-FR'}):
                    builder.add(record)
                counts.append(builder.db.execute('SELECT count(*) FROM senses').fetchone()[0])
            self.assertEqual(counts[0], counts[1])
            self.assertGreater(sum(len(json.loads(row[0]).get('examples', [])) for row in builder.db.execute('SELECT payload FROM senses')), 0)
            builder.finish(); builder.close()

    def test_script_candidates_do_not_force_ambiguous_language(self):
        self.assertEqual({x['language'] for x in language_candidates('日本')}, {'ja', 'zh'})
        self.assertTrue({'en', 'de', 'fr', 'id'} <= {x['language'] for x in language_candidates('Bank')})
        self.assertEqual(language_candidates('اللغة')[0]['language'], 'ar')

    def test_wordnet_file_language_does_not_override_gloss_language(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'ja').write_text('00001740-n\tjpn:lemma\t実体\n00001740-n\tjpn:def\t0\t実在するもの\n00001740-n\teng:def\t0\tthat which exists\n')
            (root/'en').write_text('00001740-n\tlemma\tentity\n')
            (root/'ar').write_text('00001740-n\tarb:lemma\tكيان\n')
            specs = [dict(id='test-'+lang, language=lang, path=lang, license='test fixture') for lang in ['ja', 'en', 'ar']]
            records = list(omw(specs, root))
            entry = next(r for r in records if r['sourceLanguage'] == 'ja')
            self.assertEqual(present(entry, 'ja')['senses'][0]['glosses'], ['実在するもの'])
            self.assertEqual(present(entry, 'ar')['senses'][0]['glosses'], ['كيان'])
            self.assertFalse(present(entry, 'ar')['fallback'])
            self.assertEqual(present(entry, 'de')['definitionLanguage'], 'en')
            self.assertTrue(present(entry, 'de')['fallback'])
            self.assertEqual({r['sourceLanguage'] for r in records}, {'en', 'ja'})

    def test_download_packages_retain_structure_ids_and_core_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = next(fiction(Path(__file__).resolve().parents[1]/'data/fictional-entities.json'))
            builder = Builder(root/'build.sqlite', '1.1.0-beta.1')
            builder.add(record); builder.add(copy.deepcopy(record))
            self.assertEqual(builder.db.execute('SELECT COUNT(*) FROM entries').fetchone()[0], 1)
            self.assertEqual(builder.db.execute('SELECT COUNT(*) FROM senses').fetchone()[0], 2)
            builder.finish(); builder.close()
            manifest = export(root/'build.sqlite', root/'release', '1.1.0-beta.1')
            self.assertEqual(len(manifest['packages']), 4)
            validator = fastjsonschema.compile(json.loads((Path(__file__).resolve().parents[1]/'schemas/consumer-manifest-v2.schema.json').read_text()))
            validator(manifest)
            invalid = copy.deepcopy(manifest); invalid['packages'][0]['file'] = '../bad.sqlite.gz'
            with self.assertRaises(fastjsonschema.JsonSchemaException): validator(invalid)
            for package in manifest['packages']:
                compressed = root/'release'/package['file']
                self.assertEqual(sha(compressed), package['sha256'])
                raw = root/package['id'].replace(':', '-')
                raw.write_bytes(gzip.decompress(compressed.read_bytes()))
                self.assertEqual(sha(raw), package['uncompressedSha256'])
                with sqlite3.connect(raw) as database:
                    self.assertEqual(database.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                    if package['language'] == 'en':
                        sense = json.loads(database.execute('SELECT payload FROM senses').fetchone()[0])
                        self.assertEqual(sense['restrictions']['work'], 'BLACK TORCH')
                        self.assertEqual(sense['kind'], 'factual-identification')
                    if package['role'] == 'core':
                        ids = database.execute('SELECT DISTINCT entry_id FROM forms WHERE text IN (?,?)',
                                               ('隠密局', '公儀隠密局')).fetchall()
                        self.assertEqual(ids, [(record['id'],)])
                        self.assertEqual(database.execute("SELECT COUNT(*) FROM sqlite_master WHERE name IN ('source_records','entry_source_records')").fetchone()[0], 0)
                        self.assertEqual(database.execute('SELECT COUNT(*) FROM sqlite_master WHERE name=?', ('senses',)).fetchone()[0], 0)
                    if package['role'] == 'source-records':
                        original = json.loads(database.execute('SELECT payload FROM source_records').fetchone()[0])
                        self.assertIsNone(original['record']['reading'])
                        self.assertTrue(json.loads(database.execute('SELECT payload FROM sources').fetchone()[0])['license'])
                        self.assertEqual(database.execute('SELECT entry_id FROM entry_source_records').fetchone()[0], record['id'])

    def test_normalization_does_not_merge_lexical_identities(self):
        self.assertEqual(normalized(' ｶﾀｶﾅ '), 'かたかな')
        self.assertEqual(normalized('Straße'), normalized('STRASSE'))
        record = next(fiction(Path(__file__).resolve().parents[1]/'data/fictional-entities.json'))
        with tempfile.TemporaryDirectory() as directory:
            builder = Builder(Path(directory)/'build.sqlite', 'test')
            builder.add(record)
            other = copy.deepcopy(record)
            other['id'] += ':homograph'
            for sense in other['senses']:
                sense['id'] += ':homograph'
            builder.add(other)
            self.assertEqual(builder.db.execute('SELECT COUNT(*) FROM entries').fetchone()[0], 2)
            builder.close()


if __name__ == '__main__':
    unittest.main()
