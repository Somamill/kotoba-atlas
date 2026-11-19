"""Semantic extraction for Yomitan records; display text never includes linked senses."""
import hashlib
import html
import json
import re
from urllib.parse import parse_qs, urlparse


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def children(node):
    if isinstance(node, list):
        return node
    if isinstance(node, dict):
        content = node.get('content', node.get('text', []))
        return content if isinstance(content, list) else [content]
    return []


def walk(node):
    yield node
    for child in children(node):
        yield from walk(child)


def role(node):
    return node.get('data', {}).get('content') if isinstance(node, dict) else None


def text(node):
    """Read one already-selected semantic field, omitting ruby pronunciation."""
    if isinstance(node, str):
        return html.unescape(node)
    if isinstance(node, dict):
        if node.get('tag') == 'rt':
            return ''
        if node.get('tag') == 'br':
            return '\n'
        if node.get('type') == 'image' or node.get('tag') == 'img':
            return node.get('alt', node.get('description', ''))
    return ''.join(text(child) for child in children(node))


def unique(values):
    seen = set()
    result = []
    for value in values:
        key = json.dumps(value, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def extract(row, source, definition_language, source_language='ja'):
    """Keep source identity, semantic sections and the unmodified original record."""
    assert len(row) == 8 and isinstance(row[5], list)
    nodes = list(walk(row[5]))
    attributions = [n for n in nodes if role(n) == 'attribution']
    links = [n['href'] for a in attributions for n in walk(a)
             if isinstance(n, dict) and n.get('tag') == 'a' and n.get('href')]
    origin = next((parse_qs(urlparse(link).query).get('q', [None])[0]
                   for link in links if 'edrdg.org' in urlparse(link).netloc
                   and parse_qs(urlparse(link).query).get('svc') == ['jmdict']), None)
    namespace = source.get('namespace', source['id'])
    if namespace in {'jmdict', 'jitendex'} and row[6] > 0:
        origin = str(row[6])
    entry_id = ('jmdict:'+source_language+':'+origin if origin else
                namespace+':'+source_language+':record:'+digest(row))
    source_record_id = source['id']+':'+digest(row)
    base_tags = row[2].split()
    senses = []

    def add_sense(glosses, tags, original, restrictions=None):
        glosses = unique([g.strip() for g in glosses if g.strip()])
        if not glosses:
            return
        semantic = {'language': definition_language, 'glosses': glosses,
                    'tags': sorted(set(tags)), 'restrictions': restrictions or {}}
        senses.append({'id': entry_id+':sense:'+digest(semantic), **semantic,
                       'sourceRecords': [source_record_id], 'content': original})

    groups = [n for n in nodes if role(n) == 'sense-group']
    if groups:
        for group in groups:
            inherited = base_tags + [n['data']['code'] for n in children(group)
                if isinstance(n, dict) and n.get('data', {}).get('code')]
            for sense in [n for n in walk(group) if role(n) == 'sense']:
                glossaries = [n for n in walk(sense) if role(n) == 'glossary']
                glosses = [text(item) for glossary in glossaries for item in children(glossary)]
                glosses += [text(n) for n in walk(sense) if role(n) == 'info-gloss-content']
                sense_tags = inherited + [n['data']['code'] for n in walk(sense)
                    if isinstance(n, dict) and n.get('data', {}).get('code')]
                add_sense(glosses, sense_tags, sense)
    elif all(isinstance(value, str) for value in row[5]):
        # Legacy records have no reliable sense boundaries: retain that fact.
        add_sense(row[5], base_tags, row[5], {'sourceSenseBoundaries': 'unavailable'})
    else:
        # Unknown structured formats remain lossless; never call page text a definition.
        for glossary in [n for n in nodes if role(n) == 'glossary']:
            add_sense([text(n) for n in children(glossary)], base_tags, glossary)

    refs = []
    redirects = []
    for node in nodes:
        if role(node) not in {'xref', 'redirect-glossary'}:
            continue
        for link in walk(node):
            if isinstance(link, dict) and link.get('tag') == 'a' and link.get('href'):
                query = parse_qs(urlparse(link['href']).query)
                reference = {'term': query.get('query', [text(link)])[0],
                             'reading': query.get('primary_reading', [None])[0],
                             'url': link['href'], 'content': node}
                (redirects if role(node) == 'redirect-glossary' else refs).append(reference)
    return {'id': entry_id, 'sourceLanguage': source_language,
            'identityBasis': 'source-id' if origin else 'content-addressed-record',
            'headwords': [{'text': row[0], 'reading': row[1] or None}],
            'inflections': row[3].split(), 'senses': unique(senses),
            'crossReferences': unique(refs),
            'redirects': unique(redirects),
            'forms': [n for n in nodes if role(n) == 'forms'],
            'examples': [n for n in nodes if role(n) in {'example', 'examples', 'example-sentence'}],
            'sourceRecords': [{'id': source_record_id, 'source': source['id'],
                               'sequence': row[6], 'attribution': attributions,
                               'urls': links, 'record': row}],
            'sources': [source]}


def definition_text(row, source, language):
    """Compatibility export: lexical glosses only, with real sense boundaries."""
    record = extract(row, source, language)
    return '\n'.join('; '.join(sense['glosses']) for sense in record['senses'])


def present(entry, primary_language):
    """Entry-level fallback; retain underlying senses without an extra visible entry."""
    primary = [s for s in entry['senses'] if s['language'] == primary_language and s['glosses']]
    selected = primary or [s for s in entry['senses'] if s['language'] == 'en' and s['glosses']]
    return {'entryId': entry['id'], 'sourceLanguage': entry['sourceLanguage'],
            'headwords': entry['headwords'], 'senses': selected,
            'definitionLanguage': primary_language if primary else ('en' if selected else None),
            'fallback': not primary and bool(selected) and primary_language != 'en'}
