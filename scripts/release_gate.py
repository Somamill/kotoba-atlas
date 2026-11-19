"""Local producer gate: required tokenizer dependencies and zero skipped tests."""
import argparse
from importlib.metadata import version
import json
from pathlib import Path
import sys
import unittest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    expected = {'SudachiPy': '0.6.11', 'SudachiDict-core': '20250129', 'ijson': '3.4.0.post0'}
    actual = {name: version(name) for name in expected}
    if actual != expected:
        raise RuntimeError('Release analysis dependencies do not match requirements-analysis.txt')
    from sudachipy import dictionary
    dictionary.Dictionary().create().tokenize('日本語')
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover('tests'))
    report = {'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'skipped': [(test.id(), reason) for test, reason in result.skipped],
              'dependencies': actual, 'passed': result.wasSuccessful() and not result.skipped}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    if not report['passed']:
        raise SystemExit('Release gate failed; skipped lookup/tokenizer tests are not accepted.')


if __name__ == '__main__':
    main()
