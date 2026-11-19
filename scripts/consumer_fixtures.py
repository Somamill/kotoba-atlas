"""Generate identical, small release-format fixtures for producer/native/web consumers."""
import argparse
import base64
import gzip
import json
import re
import sqlite3
from pathlib import Path
import tempfile
import zipfile
from adapters import fiction, jmdict, jmnedict
from contract import Builder, add_aliases, add_usage, export
from browser_contract import export as export_browser


def write_sql_fixtures(output):
    # Text fixtures keep generated databases out of consumers that prohibit them.
    senses = {}
    files = list(Path(output).glob('atlas-*.sqlite'))
    for file in files:
        if file.stem == 'atlas-core':
            continue
        with sqlite3.connect(file) as db:
            senses.update((identity, json.loads(payload)) for identity, payload in db.execute('SELECT id,payload FROM senses'))
    for file in files:
        with sqlite3.connect(file) as db:
            lines = [line for line in db.iterdump()
                if not re.match(r"^(?:CREATE TABLE|INSERT INTO) [\"']?reverse_search(?:[\"'_])", line)
                and 'writable_schema' not in line and 'sqlite_master' not in line and 'sqlite_stat1' not in line]
            if file.stem == 'atlas-core':
                lines.insert(-1, "CREATE VIRTUAL TABLE reverse_search USING fts5(gloss,content='',tokenize='unicode61 remove_diacritics 2');")
                for rowid, identity in db.execute('SELECT id,sense_id FROM reverse_keys'):
                    sense = senses[identity]
                    text = '\n'.join(dict.fromkeys(sense['glosses']+sense.get('equivalents', [])))
                    quoted = db.execute('SELECT quote(?)', (text,)).fetchone()[0]
                    lines.insert(-1, f'INSERT INTO reverse_search(rowid,gloss) VALUES({rowid},{quoted});')
            file.with_suffix('.sql').write_text('\n'.join(lines)+'\n')


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
        for fixture, adapter, source_id, license in [
                ('jmdict-examples-consumer-words.json', jmdict, 'jmdict-examples-fixture', 'CC-BY-SA-4.0; examples CC-BY-2.0-FR'),
                ('jmnedict-consumer-words.json', jmnedict, 'jmnedict-fixture', 'CC-BY-SA-4.0')]:
            with zipfile.ZipFile(archive, 'w') as zipped:
                zipped.writestr('words.json', (Path('tests/fixtures')/fixture).read_bytes())
            for record in adapter(archive, {'id': source_id, 'license': license,
                    'revision': '3.6.2+20261116213322', 'attribution': 'EDRDG / scriptin; Tatoeba contributors for examples'}):
                builder.add(record)
        metadata = json.loads(Path('tests/fixtures/atlas-metadata.json').read_text())
        builder.db.executemany('INSERT INTO metadata VALUES(?,?,?,?)', metadata['metadata'])
        builder.db.executemany('INSERT OR IGNORE INTO sources VALUES(?,?)', metadata['sources'])
        builder.db.execute('CREATE TABLE kanji(term TEXT PRIMARY KEY,payload TEXT NOT NULL)')
        builder.db.executemany('INSERT INTO kanji VALUES(?,?)', metadata['kanji'])
        builder.db.executemany('INSERT INTO notices VALUES(?,?)', [(name, base64.b64decode(content)) for name, content in metadata['notices']])
        for record in fiction('data/fictional-entities.json'):
            builder.add(record)
        add_aliases(builder, 'data/aliases.json')
        add_usage(builder, 'data/usage-notes.json')
        builder.finish(); builder.close()
        manifest = export(root/'build.sqlite', root/'release', '0.0.0-fixture.1')
        export_browser(root/'build.sqlite', output, '0.0.0-beta.1', 'en', optimize=False)
        for package in manifest['packages']:
            if package['role'] == 'source-records':
                continue
            target = 'atlas-core.sqlite' if package['role'] == 'core' else 'atlas-'+package['language']+'.sqlite'
            (output/target).write_bytes(gzip.decompress((root/'release'/package['file']).read_bytes()))
        (output/'atlas-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
        write_sql_fixtures(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    build(parser.parse_args().output)
