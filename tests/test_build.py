import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', ROOT / 'scripts/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class BuildTests(unittest.TestCase):
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
