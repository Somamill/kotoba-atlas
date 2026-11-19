"""Generate identical, small release-format fixtures for producer/native/web consumers."""
import argparse
import gzip
import json
from pathlib import Path
import tempfile
import zipfile
from adapters import fiction, jmdict
from contract import Builder, add_aliases, add_usage, export


def build(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        archive = root/'jmdict.zip'
        with zipfile.ZipFile(archive, 'w') as zipped:
            zipped.writestr('jmdict.json', Path('tests/fixtures/jmdict-consumer-words.json').read_bytes())
        builder = Builder(root/'build.sqlite', '0.0.0-fixture.1')
        for record in jmdict(archive, {'id': 'jmdict-fixture', 'license': 'CC-BY-SA-4.0',
                'revision': '3.6.2+20261116213322', 'attribution': 'JMdict contributors / EDRDG; scriptin JSON conversion'}):
            builder.add(record)
        for record in fiction('data/fictional-entities.json'):
            builder.add(record)
        add_aliases(builder, 'data/aliases.json')
        add_usage(builder, 'data/usage-notes.json')
        builder.finish(); builder.close()
        manifest = export(root/'build.sqlite', root/'release', '0.0.0-fixture.1')
        for package in manifest['packages']:
            if package['role'] == 'source-records':
                continue
            target = 'atlas-core.sqlite' if package['role'] == 'core' else 'atlas-'+package['language']+'.sqlite'
            (output/target).write_bytes(gzip.decompress((root/'release'/package['file']).read_bytes()))
        (output/'atlas-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    build(parser.parse_args().output)
