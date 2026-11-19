"""Report newer upstream revisions without changing reviewed pins or executing downloads."""
import argparse
import json
from pathlib import Path
import urllib.request


def check(lock):
    checks = {}; result = []
    for source in json.loads(Path(lock).read_text())['sources']:
        url = source['url'].split('/')
        if source['kind'] not in {'omw-tab', 'jmdict-json', 'jmnedict-json'}:
            continue
        repository = '/'.join(url[3:5])
        api = 'https://api.github.com/repos/'+repository+('/commits?per_page=1' if source['kind']=='omw-tab' else '/releases/latest')
        if api not in checks:
            request = urllib.request.Request(api, headers={'Accept':'application/vnd.github+json','User-Agent':'KotobaAtlas-local-upstream-check'})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise ValueError('Upstream response exceeds size limit')
            value = json.loads(data)
            checks[api] = value[0]['sha'] if isinstance(value, list) else value['tag_name']
        result.append({'source':source['id'], 'pinned':source['revision'], 'latest':checks[api],
                       'differentRevisionAvailable':source['revision']!=checks[api], 'endpoint':api})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock',type=Path,default=Path('data/sources-v2.lock.json'))
    parser.add_argument('--report',type=Path,required=True)
    args = parser.parse_args()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(check(args.lock),indent=2)+'\n')
