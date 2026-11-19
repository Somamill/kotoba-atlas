import importlib.util
from pathlib import Path
import unittest
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', ROOT / 'scripts/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class BuildTests(unittest.TestCase):
    def test_redirect_copies_only_verified_target_definitions(self):
        db = sqlite3.connect(':memory:')
        db.execute('CREATE TABLE definitions(term TEXT, reading TEXT, source INTEGER, gloss TEXT, rules TEXT, score INTEGER, UNIQUE(term,reading,source,gloss))')
        db.execute('CREATE TABLE structured_redirects(term TEXT, reading TEXT, source INTEGER, target TEXT, target_reading TEXT, rules TEXT, score INTEGER)')
        build.store(db, ('労働相', 'ろうどうしょう', 0, 'Minister of Labour', 'n', 0))
        db.execute('INSERT INTO structured_redirects VALUES(?,?,?,?,?,?,?)',
                   ('勞働相', '', 0, '労働相', 'ろうどうしょう', '', -101))
        build.resolve_redirects(db)
        self.assertEqual(db.execute('SELECT reading,gloss FROM definitions WHERE term=?', ('勞働相',)).fetchone(),
                         ('ろうどうしょう', 'Minister of Labour'))
        db.execute('INSERT INTO structured_redirects VALUES(?,?,?,?,?,?,?)',
                   ('欠', '', 0, 'missing', None, '', 0))
        with self.assertRaisesRegex(ValueError, 'Unresolved structured redirects'):
            build.resolve_redirects(db)
    def test_duplicate_gloss_keeps_all_verb_rules(self):
        db = sqlite3.connect(':memory:')
        db.execute('CREATE TABLE definitions(term TEXT, reading TEXT, source INTEGER, gloss TEXT, rules TEXT, score INTEGER, UNIQUE(term,reading,source,gloss))')
        build.store(db, ('濕氣る', '', 0, 'same meaning', 'v1', -2))
        build.store(db, ('濕氣る', '', 0, 'same meaning', 'v5', 0))
        rows = db.execute('SELECT rules,score FROM definitions').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0][0].split()), {'v1', 'v5'})
        self.assertEqual(rows[0][1], 0)
        db.close()

    def test_rich_text_preserves_boundaries_and_links(self):
        text = build.clean({'type': 'structured-content', 'content': [
            {'tag': 'div', 'content': 'one'}, {'tag': 'div', 'content': [
                'two ', {'tag': 'a', 'href': 'https://example.org', 'content': 'source'}]}]})
        self.assertEqual(text, 'one\ntwo source (https://example.org)')

    def test_html_and_plain_japanese(self):
        self.assertEqual(build.clean('<p>物の怪</p><p>spirit &amp; ghost</p>'), '物の怪\nspirit & ghost')
        self.assertEqual(build.clean('1 < 2'), '1 < 2')
        self.assertEqual(build.clean({'tag': 'th'}), '')
        self.assertEqual(build.clean({'type': 'text', 'text': 'ghost'}), 'ghost')

    def test_aliases_are_explicit_and_keep_deinflection_rules(self):
        aliases = {r[0]: r for r in build.alias_rows()}
        self.assertEqual(aliases['物ノ怪'][1], 'もののけ')
        self.assertEqual(aliases['鎌かける'][3], 'v1')
        self.assertEqual(aliases['鎌かけて'][3], '')
        self.assertTrue(any('Canonical expression: 鎌を掛ける' == g for g in aliases['鎌かけて'][5]))


if __name__ == '__main__':
    unittest.main()
