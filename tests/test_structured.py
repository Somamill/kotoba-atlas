import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from structured import definition_text, extract, present

SOURCE = {'id': 'jitendex', 'namespace': 'jmdict', 'license': 'CC-BY-SA-4.0'}


class StructuredTests(unittest.TestCase):
    def setUp(self):
        self.row = json.loads((Path(__file__).parent/'fixtures/jitendex-2238120.json').read_text())

    def test_issue_5_only_current_sense_becomes_definition(self):
        result = extract(self.row, SOURCE, 'en')
        self.assertEqual(result['id'], 'jmdict:ja:2238120')
        self.assertEqual(result['senses'][0]['glosses'], [
            'easy to get into (e.g. of music, etc.)',
            'easily getting into (a certain mood, etc.)'])
        self.assertEqual(result['crossReferences'][0]['term'], '乗り')
        self.assertEqual(result['crossReferences'][0]['reading'], 'のり')
        self.assertTrue(result['forms'])
        self.assertEqual(result['sourceRecords'][0]['record'], self.row)
        self.assertEqual(set(result['senses'][0]['tags']), {'exp', 'adj-ix', 'uk'})
        clean = definition_text(self.row, SOURCE, 'en')
        for pollution in ['expadjectivekana', 'See also', 'forms', 'enthusiasm', '?query=', 'JMdict']:
            self.assertNotIn(pollution, clean)

    def test_primary_definitions_suppress_english_without_deleting_it(self):
        entry = extract(self.row, SOURCE, 'en')
        german = copy.deepcopy(entry['senses'][0])
        german.update(id='de-sense', language='de', glosses=['sich leicht mitreißen lassend'])
        entry['senses'].append(german)
        self.assertEqual(present(entry, 'de')['senses'], [german])
        self.assertFalse(present(entry, 'de')['fallback'])
        self.assertEqual(len(entry['senses']), 2)
        self.assertTrue(present(entry, 'ar')['fallback'])
        self.assertEqual(len(present(entry, 'ar')['senses']), 1)
        self.assertFalse(present(entry, 'en')['fallback'])

    def test_identity_and_original_record_are_preserved(self):
        original = copy.deepcopy(self.row)
        first = extract(self.row, SOURCE, 'en')
        second = extract(copy.deepcopy(self.row), SOURCE, 'en')
        self.assertEqual(first['senses'][0]['id'], second['senses'][0]['id'])
        self.assertEqual(self.row, original)
        alternate = copy.deepcopy(self.row); alternate[0] = 'のりの良い'
        self.assertEqual(extract(alternate, SOURCE, 'en')['id'], first['id'])
        homograph = copy.deepcopy(self.row); homograph[6] = 9999999
        self.assertNotEqual(extract(homograph, SOURCE, 'en')['id'], first['id'])

    def test_unknown_structure_never_becomes_a_definition(self):
        row = ['字', 'じ', '', '', 0, [{'type': 'structured-content', 'content':
            {'tag': 'div', 'content': 'forms and metadata only'}}], -1, '']
        self.assertEqual(extract(row, {'id': 'unknown'}, 'en')['senses'], [])


if __name__ == '__main__':
    unittest.main()
