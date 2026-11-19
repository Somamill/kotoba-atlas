import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from acquire_sources import acquire
from upstream_check import check


class AcquisitionTests(unittest.TestCase):
    def test_checksum_failure_preserves_cached_source_and_removes_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'data'; target.write_bytes(b'previous verified bytes')
            expected=hashlib.sha256(b'new expected bytes').hexdigest()
            with patch('urllib.request.urlopen',return_value=io.BytesIO(b'corrupt download')):
                with self.assertRaises(ValueError):acquire(target,'https://example.invalid/source',expected,[])
            self.assertEqual(target.read_bytes(),b'previous verified bytes')
            self.assertFalse(target.with_name('data.part').exists())
            with patch('urllib.request.urlopen',return_value=io.BytesIO(b'new expected bytes')):
                acquire(target,'https://example.invalid/source',expected,[])
            self.assertEqual(target.read_bytes(),b'new expected bytes')

    def test_upstream_check_coalesces_requests_without_changing_reviewed_pins(self):
        with tempfile.TemporaryDirectory() as directory:
            lock=Path(directory)/'sources.json'
            value={'sources':[{'id':name,'kind':'jmdict-json','revision':'reviewed',
                    'url':'https://github.com/scriptin/jmdict-simplified/releases/download/reviewed/'+name+'.zip'} for name in ['words','examples']]}
            original=json.dumps(value);lock.write_text(original)
            with patch('urllib.request.urlopen',return_value=io.BytesIO(b'{"tag_name":"newer"}')) as request:
                result=check(lock)
            self.assertEqual(request.call_count,1)
            self.assertTrue(all(item['differentRevisionAvailable'] for item in result))
            self.assertEqual(lock.read_text(),original)
