import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('compare_coverage', Path(__file__).resolve().parents[1] / 'scripts/compare_coverage.py')
coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)


class CoverageTests(unittest.TestCase):
    def test_reordering_is_allowed_but_losing_duplicate_metadata_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            old, new = Path(folder) / 'old.zip', Path(folder) / 'new.zip'
            words = [['語', 'ご', '', '', 0, ['word'], -1, ''], ['言葉', 'ことば', '', '', 0, ['word'], -1, '']]
            meta = ['語', 'freq', 123]
            def write(path, rows, metadata):
                with zipfile.ZipFile(path, 'w') as out:
                    out.writestr('index.json', '{"title":"test"}')
                    out.writestr('term_bank_1.json', json.dumps(rows))
                    out.writestr('term_meta_bank_1.json', json.dumps(metadata))
            write(old, words, [meta, meta])
            write(new, list(reversed(words)), [meta, meta])
            self.assertEqual(coverage.compare(old, new)['retained_lookup_pairs'], 2)
            write(new, words, [meta])
            with self.assertRaisesRegex(AssertionError, 'Lost term_meta'):
                coverage.compare(old, new)
