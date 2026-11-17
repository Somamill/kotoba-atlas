import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import json
import tempfile
import zipfile

spec = importlib.util.spec_from_file_location('editions', Path(__file__).resolve().parents[1] / 'scripts/editions.py')
editions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(editions)


class EditionTests(unittest.TestCase):
    def test_native_bank_chunking_preserves_records_and_caps_allocations(self):
        records = [[str(i), 'freq', i] for i in range(12)]
        with patch.object(editions, 'BANK_BYTES', 80), patch.object(editions, 'BANK_ENTRIES', 3):
            banks = list(editions.bounded_banks(records))
        self.assertEqual([record for bank in banks for record in json.loads(bank)], records)
        self.assertTrue(all(len(bank) <= 80 and len(json.loads(bank)) <= 3 for bank in banks))

    def setUp(self):
        self.sources = [
            {'label': 'DE • WaDoku', 'kind': 'words'},
            {'label': 'EN • Jitendex', 'kind': 'words'},
            {'label': 'EN • JMdict', 'kind': 'words'},
            {'label': 'Names • JMnedict', 'kind': 'words'},
            {'label': 'Pitch • WaDoku', 'kind': 'metadata'}]
        self.rows = [('語', 'ご', 0, '[DE • WaDoku]\nWort', '', 0),
                     ('語', 'ご', 1, '[EN • Jitendex]\nword', 'v1', 0),
                     ('語', 'ご', 2, '[EN • JMdict]\nword', 'v5', 0)]

    def test_english_drops_german_and_duplicate_core_but_keeps_rules(self):
        row = editions.select_definitions(self.rows, 'en', self.sources)
        self.assertEqual(row[5], ['[EN • Jitendex]\nword'])
        self.assertEqual(set(row[3].split()), {'v1', 'v5'})

    def test_german_prefers_german_and_falls_back_to_english(self):
        row = editions.select_definitions(self.rows, 'de', self.sources)
        self.assertEqual(row[5], ['[DE • WaDoku]\nWort'])
        fallback = editions.select_definitions(self.rows[1:], 'de', self.sources)
        self.assertEqual(fallback[5], ['[EN • Jitendex]\nword'])

    def test_metadata_does_not_create_a_fake_definition(self):
        row = ('語', 'ご', 4, '[Pitch • WaDoku]\nPitch data', '', 0)
        self.assertIsNone(editions.select_definitions([row], 'en', self.sources))

    def test_names_rank_below_vocabulary(self):
        row = ('語', 'ご', 3, '[Names • JMnedict]\nname', '', 0)
        self.assertLess(editions.select_definitions([row], 'en', self.sources)[4],
                        editions.select_definitions(self.rows, 'en', self.sources)[4])

    def test_pitch_devoice_can_be_scalar_or_list(self):
        for value in [2, [2, 3]]:
            text = '[Pitch • WaDoku]\nSource detail: ' + __import__('json').dumps({'pitches': [{'position': 1, 'devoice': value}]})
            note = editions.compact_note(text)
            self.assertIn('devoiced morae: 2', note)


    def test_duplicate_meanings_keep_source_credit_and_pos(self):
        values = ['[DE • WaDoku]\nJapanisch\njapanische Sprache', '[DE • JMdict]\nTags: n\nJapanisch\njapanische Sprache']
        merged = editions.merge_glosses(values)
        self.assertEqual(len(merged), 1)
        self.assertIn('WaDoku | DE • JMdict', merged[0])
        self.assertIn('Tags: n', merged[0])
        self.assertEqual(merged[0].count('Japanisch'), 1)

    def test_register_differences_are_not_erased_by_deduplication(self):
        values = ['[EN • A]\nTags: arch n\nold meaning', '[EN • B]\nTags: n\nold meaning']
        self.assertEqual(len(editions.merge_glosses(values)), 2)

    def test_native_part_of_speech_tags_survive(self):
        rows = [('語', 'ご', 0, '[DE • WaDoku]\nTags: n\nWort', '', 0)]
        self.assertEqual(editions.select_definitions(rows, 'de', self.sources)[2], 'n')

    def test_curated_language_selection_has_no_cross_language_leakage(self):
        rows = [('語', 'ご', len(self.sources), '[DE • Atlas usage]\nWort', '', 0),
                ('語', 'ご', len(self.sources) + 1, '[EN • Atlas usage]\nword', '', 0)]
        self.assertEqual(editions.select_definitions(rows, 'en', self.sources)[5], ['[EN • Atlas usage]\nword'])
        self.assertEqual(editions.select_definitions(rows, 'de', self.sources)[5], ['[DE • Atlas usage]\nWort'])

    def test_phrase_supplements_remain_lexical_and_language_filtered(self):
        rows = [('鎌かける', 'かまかける', len(self.sources), '[DE/EN • supplement]\nDE: Fangfrage\nEN: trick question', 'v1', 0)]
        row = editions.select_definitions(rows, 'en', self.sources)
        self.assertGreaterEqual(row[4], 0)
        self.assertNotIn('DE:', row[5][0])
        self.assertIn('EN: trick question', row[5][0])

    def test_v102_fails_chrome_base64_budget(self):
        with self.assertRaisesRegex(ValueError, 'Base64'):
            editions.check_transfer_budget(61191287)
        encoded = editions.check_transfer_budget(50255640)
        self.assertLess(encoded + editions.MIGAKU_ENVELOPE_BYTES, editions.MIGAKU_MESSAGE_BYTES)

    def test_optimizer_preserves_complete_unicode_records_and_notices(self):
        words = [['物ノ怪', 'もののけ', 'n', '', 100, ['Dämon; böser Geist'], -1, ''],
                 ['羅睺', 'らごう', 'n', '', 100, ['mythological spirit'], -1, '']]
        metadata = [['物ノ怪', 'freq', {'reading': 'もののけ', 'frequency': 123}]]
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'test.zip'
            with zipfile.ZipFile(archive, 'w') as out:
                out.writestr('index.json', '{"format":3,"revision":"test","title":"test"}')
                out.writestr('term_bank_1.json', json.dumps(words, ensure_ascii=False))
                out.writestr('term_meta_bank_1.json', json.dumps(metadata, ensure_ascii=False))
                out.writestr('licenses/notice.txt', 'source credit')
            report = editions.optimize_archive(archive)
            with zipfile.ZipFile(archive) as out:
                self.assertEqual(sorted(json.loads(out.read('term_bank_1.json'))), sorted(words))
                self.assertEqual(json.loads(out.read('term_meta_bank_1.json')), metadata)
                self.assertEqual(out.read('licenses/notice.txt'), b'source credit')
            self.assertEqual(report['optimized_word_records'], 2)
            self.assertEqual(report['optimized_metadata_records'], 1)

    def test_optimizer_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as out:
                out.writestr('../outside.txt', 'invalid')
            with self.assertRaisesRegex(ValueError, 'Unsafe archive path'):
                editions.optimize_archive(archive)


if __name__ == '__main__':
    unittest.main()
