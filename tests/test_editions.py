import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import json

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


if __name__ == '__main__':
    unittest.main()
