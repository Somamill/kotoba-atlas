"""Local-only, fail-closed Atlas release pipeline. GitHub Actions stays disabled."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from browser_contract import export as browser
from check_contract import check


def run(*args):
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    run(sys.executable, 'scripts/upstream_check.py', '--report', str(args.output/'upstream-check.json'))
    run(sys.executable, 'scripts/acquire_sources.py')
    run(sys.executable, 'scripts/release_gate.py', '--report', str(args.output/'test-gate.json'))
    run(sys.executable, 'scripts/contract.py', '--output', str(args.output), '--revision', args.revision)
    for language in ['en', 'de']:
        archive = browser(args.output/'build.sqlite', args.output, args.revision, language)
        run('node', 'scripts/test_yomitan_import.mjs', '.cache/upstream/yomitan', str(archive), str(archive.with_suffix('.yomitan.json')))
        run(sys.executable, 'scripts/test_migaku_import.py', str(archive), '--source', '.cache/upstream/migaku',
            '--database', str(args.output/('migaku-test-'+language+'.sqlite')), '--report', str(archive.with_suffix('.legacy-migaku.json')))
        (args.output/('migaku-test-'+language+'.sqlite')).unlink()
    run(sys.executable, 'scripts/consumer_fixtures.py', str(args.output/'consumer-fixtures'))
    run('node', 'scripts/test_yomitan_import.mjs', '.cache/upstream/yomitan',
        str(args.output/'consumer-fixtures/Kotoba_Atlas_English_v0_0_0_beta_1.zip'),
        str(args.output/'yomitan-indexeddb-fixture.json'), 'indexeddb')
    # All deliverable bytes now exist; the reproducible source database is not shipped.
    (args.output/'build.sqlite').unlink()
    check(args.output)
    source_files = [Path('data/sources-v2.lock.json'), *sorted(Path('scripts').glob('*.py')), *sorted(Path('scripts').glob('*.mjs'))]
    evidence = {'revision': args.revision, 'sources': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
                'publication': 'not performed; inspect artifact checks and consumer/native evidence before uploading',
                'browserVerification': 'pinned upstream parser and legacy importer; not current live extension certification'}
    (args.output/'pipeline-evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')


if __name__ == '__main__':
    main()
