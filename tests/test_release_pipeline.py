import copy
import gzip
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from check_contract import validate_descriptors, unpack
from contract import LANGUAGES, package, sha
from pipeline import stage_release


class PipelineTests(unittest.TestCase):
    def test_partial_directory_is_unpublishable_and_owned_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)/'release'
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                with stage_release(destination) as stage:
                    (stage/'consumer-manifest.json').touch()
                    self.assertFalse(destination.exists())
                    with self.assertRaises(FileExistsError):
                        with stage_release(destination):
                            self.fail('Concurrent publisher entered staging')
                    raise RuntimeError('interrupted')
            self.assertFalse(stage.exists())
            with stage_release(destination) as stage:
                (stage/'pipeline-evidence.json').touch()
            self.assertTrue((destination/'pipeline-evidence.json').is_file())
            with self.assertRaises(FileExistsError):
                with stage_release(destination):
                    self.fail('Existing release was replaced')

    def test_descriptor_rejects_duplicate_incomplete_or_mixed_generation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = {'dictionaryRevision': '1.0.0', 'packages': []}
            for role, language in [('core', None), ('source-records', None), *(('language', code) for code in LANGUAGES)]:
                raw = root/f'{role}-{language}.sqlite'
                raw.write_bytes(str(raw.name).encode())
                descriptor = package(raw, role, '1.0.0', language)
                if role != 'core':
                    descriptor['coreSha256'] = manifest['packages'][0]['uncompressedSha256']
                manifest['packages'].append(descriptor)
            validate_descriptors(manifest, require_core_binding=True)
            for field, value in [('coreSha256', '0'*64), ('dictionaryRevision', '1.0.1'), ('id', 'core')]:
                mixed = copy.deepcopy(manifest)
                mixed['packages'][1][field] = value
                with self.assertRaises(ValueError):
                    validate_descriptors(mixed, require_core_binding=True)
            manifest['packages'].pop()
            with self.assertRaisesRegex(ValueError, 'Missing'):
                validate_descriptors(manifest, require_core_binding=True)

    def test_unpack_rejects_corruption_and_bounded_expansion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root/'core.sqlite'
            raw.write_bytes(b'release fixture')
            descriptor = package(raw, 'core', '1.0.0')
            compressed = root/descriptor['file']
            with self.assertRaisesRegex(ValueError, 'exceeds manifest size'):
                unpack(compressed, root/'bounded.sqlite', dict(descriptor, uncompressedBytes=1))
            compressed.write_bytes(gzip.compress(b'bad'))
            with self.assertRaisesRegex(ValueError, 'Invalid compressed'):
                unpack(compressed, root/'invalid.sqlite', descriptor)
            with self.assertRaisesRegex(ValueError, 'Invalid expanded'):
                unpack(compressed, root/'corrupt.sqlite',
                       dict(descriptor, compressedBytes=compressed.stat().st_size,
                            sha256=sha(compressed), uncompressedBytes=3))
