#!/usr/bin/env python3
"""Download a bounded, resumable Jimaku sample for local-only coverage analysis."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://jimaku.cc'
MAX_FILE_BYTES = 2 * 1024 * 1024


def safe_url(path):
    url = urllib.parse.urljoin(ORIGIN, path)
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != 'jimaku.cc' or parsed.username or parsed.fragment:
        raise ValueError('Refusing to send credentials outside Jimaku HTTPS.')
    return url


class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Jimaku:
    def __init__(self, key):
        self.key = key
        self.opener = urllib.request.build_opener(SameOriginRedirect())

    def get(self, path, limit=MAX_FILE_BYTES):
        url = safe_url(path)
        for attempt in range(3):
            request = urllib.request.Request(url, headers={
                'Authorization': self.key,
                'User-Agent': 'KotobaAtlas-SubtitleAudit/0.1 (local dictionary coverage research)'})
            try:
                with self.opener.open(request, timeout=30) as response:
                    if int(response.headers.get('Content-Length', '0')) > limit:
                        raise ValueError('Response exceeds download size bound.')
                    body = response.read(limit + 1)
                    if len(body) > limit:
                        raise ValueError('Response exceeds download size bound.')
                    wait = float(response.headers.get('x-ratelimit-reset-after', '0'))
                    if int(response.headers.get('x-ratelimit-remaining', '2')) <= 1:
                        if wait > 55:
                            raise RuntimeError('Rate limit requires a longer wait; resume later.')
                        time.sleep(max(0, wait) + 0.1)
                time.sleep(0.3)
                return body
            except urllib.error.HTTPError as error:
                if error.code != 429 or attempt == 2:
                    raise RuntimeError('Jimaku HTTP status ' + str(error.code)) from None
                wait = float(error.headers.get('x-ratelimit-reset-after', '5'))
                if wait > 55:
                    raise RuntimeError('Rate limit requires a longer wait; resume later.') from None
                time.sleep(max(0, wait) + 0.2)
        raise RuntimeError('Jimaku request retries exhausted.')

    def json(self, path):
        return json.loads(self.get(path, limit=8 * 1024 * 1024))



def save_manifest(path, manifest):
    temporary = path.with_suffix('.part')
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    temporary.chmod(0o600)
    temporary.replace(path)


def select_files(files, per_title):
    eligible = sorted((f for f in files if Path(f['name']).suffix.lower() in {'.srt', '.ass', '.ssa', '.vtt'}
                       and f['size'] <= MAX_FILE_BYTES
                       and not re.search(r'(?:[. _-])(?:en|eng|english)(?:[. _-])', f['name'], re.I)),
                      key=lambda f: f['name'])
    # Prefer one cut per episode; ambiguous filenames remain separate and cue deduplication handles overlap.
    selected, episodes = [], set()
    for f in eligible:
        match = re.search(r'(?:^|[ _.-])(?:S\d{1,2}E|EP?\s*)?(\d{2,3})(?:[ _.-]|$)', f['name'], re.I)
        episode = match.group(1) if match else f['name']
        if episode not in episodes:
            selected.append(f)
            episodes.add(episode)
        if len(selected) == per_title:
            break
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--titles', type=Path, default=ROOT / 'data/corpus-titles.json')
    parser.add_argument('--per-title', type=int, default=8)
    parser.add_argument('--max-bytes', type=int, default=80 * 1024 * 1024)
    args = parser.parse_args()
    if not 1 <= args.per_title <= 20 or not 0 < args.max_bytes <= 200 * 1024 * 1024:
        parser.error('Use 1–20 files per title and at most 200 MiB.')
    key = os.environ.get('JIMAKU_API_KEY') or (Path.home() / '.config/kotoba-atlas/jimaku-api-key').read_text().strip()
    if not key or '\n' in key or key.startswith('{\\rtf'):
        parser.error('Key must be one plain-text line; never commit it.')
    args.output.mkdir(parents=True, exist_ok=True)
    args.output.chmod(0o700)
    manifest_path = args.output / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        'source': ORIGIN, 'raw_subtitles_local_only': True, 'files': [], 'skipped': []}
    total = sum(f['bytes'] for f in manifest['files'])
    known = {f['url']: f for f in manifest['files']}
    client = Jimaku(key)
    for title in json.loads(args.titles.read_text()):
        try:
            query = urllib.parse.urlencode({'query': title['name'], 'anime': str(title['anime']).lower()})
            entries = client.json('/api/entries/search?' + query)
            entry = next((e for e in entries if e['name'].casefold() == title['name'].casefold()), None)
            if entry is None:
                manifest['skipped'].append({'title': title['name'], 'reason': 'No exact title match'})
                continue
            files = client.json('/api/entries/' + str(entry['id']) + '/files')
            chosen = select_files(files, args.per_title)
            for f in chosen:
                url = safe_url(f['url'])
                previous = known.get(url)
                if previous:
                    p = args.output / previous['local_name']
                    if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == previous['sha256']:
                        continue
                    raise ValueError('Cached subtitle is missing or has changed; inspect before resuming.')
                if total + f['size'] > args.max_bytes:
                    raise ValueError('Total download bound reached.')
                content = client.get(url)
                if total + len(content) > args.max_bytes:
                    raise ValueError('Total actual download bound reached.')
                local = str(entry['id']) + '-' + hashlib.sha256(url.encode()).hexdigest()[:16] + Path(f['name']).suffix.lower()
                p = args.output / local
                p.write_bytes(content)
                p.chmod(0o600)
                row = {'title': entry['name'], 'entry_id': entry['id'], 'anime': title['anime'],
                       'url': url, 'original_name': f['name'], 'local_name': local,
                       'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
                manifest['files'].append(row)
                known[url] = row
                total += len(content)
                save_manifest(manifest_path, manifest)
            print(json.dumps({'title': entry['name'], 'files_selected': len(chosen), 'downloaded_total': len(manifest['files'])}), flush=True)
        except (RuntimeError, ValueError, OSError) as error:
            manifest['skipped'].append({'title': title['name'], 'reason': type(error).__name__ + ': ' + str(error)})
            print(json.dumps({'title': title['name'], 'status': 'skipped', 'reason': str(error)}), flush=True)
        save_manifest(manifest_path, manifest)
    print(json.dumps({'downloaded_files': len(manifest['files']), 'downloaded_bytes': total}))


if __name__ == '__main__':
    main()
