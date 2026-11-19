"""Acquire pinned data/notices only; fail closed if upstream content changes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def acquire(destination, url, expected, candidates):
    if destination.exists() and sha(destination) == expected:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name+'.part')
    try:
        local = next((p for p in candidates if p.exists() and sha(p) == expected), None)
        if local:
            shutil.copyfile(local, temporary)
        else:
            if not url.startswith('https://'):
                raise ValueError('Source must use HTTPS')
            request = urllib.request.Request(url, headers={'User-Agent': 'KotobaAtlas-source-builder/2'})
            with urllib.request.urlopen(request, timeout=60) as response, temporary.open('wb') as output:
                size = 0
                while data := response.read(1024*1024):
                    size += len(data)
                    if size > 2_000_000_000:
                        raise ValueError('Source exceeds acquisition limit')
                    output.write(data)
        if sha(temporary) != expected:
            raise ValueError('Pinned source checksum mismatch: '+url)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, default=Path('data/sources-v2.lock.json'))
    parser.add_argument('--cache', type=Path, default=Path('.cache/sources-v2'))
    args = parser.parse_args()
    for source in json.loads(args.lock.read_text())['sources']:
        acquire(args.cache/source['id']/'data', source['url'], source['sha256'],
                [Path('.cache')/source['path'], Path('.cache/omw-data')/source['path']])
        if notice := source.get('licenseFile'):
            acquire(args.cache/source['id']/'LICENSE', notice['url'], notice['sha256'],
                    [Path('.cache/omw-data')/notice['path']])
        print('Verified data and notice:', source['id'], flush=True)


if __name__ == '__main__':
    main()
