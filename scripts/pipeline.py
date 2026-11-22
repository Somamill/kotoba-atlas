"""Local-only, fail-closed Atlas release pipeline. GitHub Actions stays disabled."""
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from browser_contract import export as browser
from check_contract import check
from contract import sha


def run(*args):
    subprocess.run(args, check=True)


@contextmanager
def stage_release(destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    staging = destination.with_name('.'+destination.name+'.partial')
    staging.mkdir()
    try:
        yield staging
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(destination)
        staging.rename(destination)
    except BaseException:
        shutil.rmtree(staging)
        raise


def build(output, revision):
    run(sys.executable, 'scripts/upstream_check.py', '--report', str(output/'upstream-check.json'))
    run(sys.executable, 'scripts/acquire_sources.py')
    run(sys.executable, 'scripts/release_gate.py', '--report', str(output/'test-gate.json'))
    run(sys.executable, 'scripts/contract.py', '--output', str(output), '--revision', revision)
    for language in ['en', 'de']:
        archive = browser(output/'build.sqlite', output, revision, language)
        run('node', 'scripts/test_yomitan_import.mjs', '.cache/upstream/yomitan', str(archive), str(archive.with_suffix('.yomitan.json')))
        run(sys.executable, 'scripts/test_migaku_import.py', str(archive), '--source', '.cache/upstream/migaku',
            '--database', str(output/('migaku-test-'+language+'.sqlite')), '--report', str(archive.with_suffix('.legacy-migaku.json')))
        (output/('migaku-test-'+language+'.sqlite')).unlink()
    run(sys.executable, 'scripts/consumer_fixtures.py', str(output/'consumer-fixtures'))
    run('node', 'scripts/test_yomitan_import.mjs', '.cache/upstream/yomitan',
        str(output/'consumer-fixtures/Kotoba_Atlas_English_v0_0_0_beta_1.zip'),
        str(output/'yomitan-indexeddb-fixture.json'), 'indexeddb')
    # All deliverable bytes now exist; the reproducible source database is not shipped.
    (output/'build.sqlite').unlink()
    check(output, require_core_binding=True)
    source_files = [Path('data/sources-v2.lock.json'), *sorted(Path('scripts').glob('*.py')), *sorted(Path('scripts').glob('*.mjs'))]
    evidence = {'revision': revision, 'sources': {str(p): sha(p) for p in source_files},
                'tools': {'python': sys.version.split()[0], 'sqlite': sqlite3.sqlite_version,
                          'node': subprocess.check_output(['node', '--version'], text=True).strip()},
                'outputs': {str(p.relative_to(output)): {'bytes': p.stat().st_size, 'sha256': sha(p)}
                            for p in sorted(output.rglob('*')) if p.is_file()},
                'publication': 'not performed; inspect artifact checks and consumer/native evidence before uploading',
                'browserVerification': 'pinned upstream parser and legacy importer; not current live extension certification'}
    (output/'pipeline-evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    with stage_release(args.output) as staging:
        build(staging, args.revision)


if __name__ == '__main__':
    main()
