"""Licensed source adapters for the Atlas consumer contract, without HTML flattening."""
from collections import defaultdict
import json
from pathlib import Path
import zipfile
import ijson
from structured import digest, unique

LANGUAGES = ('en', 'zh', 'es', 'ar', 'id', 'pt', 'fr', 'ja', 'ru', 'de')
ISO3 = {'eng': 'en', 'ger': 'de', 'deu': 'de', 'fre': 'fr', 'fra': 'fr',
        'spa': 'es', 'rus': 'ru', 'por': 'pt', 'jpn': 'ja', 'ara': 'ar',
        'arb': 'ar', 'ind': 'id', 'zho': 'zh', 'cmn': 'zh'}


def source_info(spec):
    return {k: v for k, v in spec.items() if k not in {'path', 'kind'}}


def words(path):
    # Streaming keeps the full names/examples snapshots out of build memory.
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if n.endswith('.json')]
        if len(names) != 1:
            raise ValueError('Expected one source JSON document')
        with archive.open(names[0]) as stream:
            yield from ijson.items(stream, 'words.item')


def jmdict(path, spec):
    for word in words(path):
        entry_id = 'jmdict:ja:'+word['id']
        source_record_id = spec['id']+':'+word['id']+':'+digest(word)
        forms = []
        for kana in word['kana']:
            forms.append({'text': kana['text'], 'reading': kana['text'], 'kind': 'reading',
                          'tags': kana['tags'], 'common': kana['common']})
            for kanji in word['kanji']:
                if '*' in kana['appliesToKanji'] or kanji['text'] in kana['appliesToKanji']:
                    forms.append({'text': kanji['text'], 'reading': kana['text'], 'kind': 'headword',
                                  'tags': kanji['tags'], 'common': kanji['common']})
        senses = []
        for sense in word['sense']:
            by_language = defaultdict(list)
            for gloss in sense['gloss']:
                language = ISO3.get(gloss['lang'], gloss['lang'])
                if language in LANGUAGES and gloss['text'].strip():
                    by_language[language].append(gloss)
            restrictions = {'spellings': sense['appliesToKanji'], 'readings': sense['appliesToKana']}
            semantic_id = entry_id+':sense:'+digest({k: v for k, v in sense.items() if k != 'examples'})
            for language, glosses in by_language.items():
                senses.append({'id': semantic_id+':'+language, 'semanticId': semantic_id,
                    'language': language, 'kind': 'definition',
                    'glosses': unique([g['text'] for g in glosses]),
                    'glossDetails': glosses, 'tags': sense['partOfSpeech']+sense['misc'],
                    'restrictions': restrictions, 'sourceRecords': [source_record_id],
                    'examples': sense.get('examples', []), 'crossReferences': sense['related'],
                    'antonyms': sense['antonym'], 'fields': sense['field'],
                    'dialects': sense['dialect'], 'notes': sense['info'],
                    'etymology': sense['languageSource']})
        yield {'id': entry_id, 'sourceLanguage': 'ja', 'identityBasis': 'source-id',
            'headwords': unique(forms), 'senses': unique(senses),
            'inflections': sorted({tag for s in word['sense'] for tag in s['partOfSpeech']}),
            'sources': [source_info(spec)],
            'sourceRecords': [{'id': source_record_id, 'source': spec['id'], 'record': word}]}


def jmnedict(path, spec):
    for word in words(path):
        entry_id = 'jmnedict:ja:'+word['id']
        record_id = spec['id']+':'+word['id']+':'+digest(word)
        forms = []
        for kana in word['kana']:
            forms.append({'text': kana['text'], 'reading': kana['text'], 'kind': 'reading', 'tags': kana['tags']})
            for kanji in word['kanji']:
                if '*' in kana['appliesToKanji'] or kanji['text'] in kana['appliesToKanji']:
                    forms.append({'text': kanji['text'], 'reading': kana['text'], 'kind': 'headword', 'tags': kanji['tags']})
        senses = []
        for translation in word['translation']:
            grouped = defaultdict(list)
            for value in translation['translation']:
                language = ISO3.get(value['lang'], value['lang'])
                if language in LANGUAGES:
                    grouped[language].append(value['text'])
            semantic_id = entry_id+':sense:'+digest(translation)
            for language, values in grouped.items():
                senses.append({'id': semantic_id+':'+language, 'semanticId': semantic_id,
                    'language': language, 'kind': 'proper-name-translation', 'glosses': unique(values),
                    'tags': translation['type'], 'restrictions': {},
                    'crossReferences': translation['related'], 'sourceRecords': [record_id]})
        yield {'id': entry_id, 'sourceLanguage': 'ja', 'kind': 'name',
            'identityBasis': 'source-id', 'headwords': unique(forms), 'inflections': [],
            'senses': senses, 'sources': [source_info(spec)],
            'sourceRecords': [{'id': record_id, 'source': spec['id'], 'record': word}]}


def omw(sources, directory, source_languages=('ja', 'en')):
    """Use upstream synset alignment, never inferred text similarity, for translations."""
    synsets = defaultdict(lambda: defaultdict(lambda: {'lemmas': [], 'definitions': [], 'examples': []}))
    provenance = {}
    for spec in sources:
        provenance[spec['id']] = source_info(spec)
        for line in (Path(directory)/spec['path']).read_text().splitlines():
            if not line or line.startswith('#'):
                continue
            fields = line.split('\t')
            if len(fields) < 3:
                raise ValueError('Malformed WordNet row: '+repr(fields))
            synset, kind = fields[:2]
            # A Japanese WordNet file also contains English glosses and examples.
            prefix = kind.split(':')[0] if ':' in kind else spec['language']
            language = ISO3.get(prefix, prefix)
            if language not in LANGUAGES:
                continue
            data = synsets[synset][language]
            if kind == 'lemma' or kind.endswith(':lemma'):
                data['lemmas'].append(fields[2])
            elif kind.endswith(':def'):
                data['definitions'].append(fields[-1])
            elif kind.endswith(':exe'):
                data['examples'].append(fields[-1])
            data.setdefault('rows', []).append({'source': spec['id'], 'line': line})
    entries = {}
    for synset, translations in synsets.items():
        for source_language in source_languages:
            if source_language not in translations:
                continue
            for lemma in unique(translations[source_language]['lemmas']):
                entry_id = 'omw:'+source_language+':'+digest([lemma, synset[-1]])
                entry = entries.setdefault(entry_id, {'id': entry_id, 'sourceLanguage': source_language,
                    'identityBasis': 'upstream-lemma-and-pos',
                    'headwords': [{'text': lemma, 'reading': None, 'kind': 'headword'}],
                    'inflections': [], 'senses': [], 'sources': [], 'sourceRecords': []})
                for target, data in translations.items():
                    glosses = unique(data['definitions'] or data['lemmas'])
                    if not glosses:
                        continue
                    source_record_ids = []
                    grouped = defaultdict(list)
                    for row in data['rows']:
                        grouped[row['source']].append(row['line'])
                    for source_id, rows in grouped.items():
                        source_record_id = source_id+':'+synset+':'+digest(rows)
                        source_record_ids.append(source_record_id)
                        entry['sources'].append(provenance[source_id])
                        entry['sourceRecords'].append({'id': source_record_id, 'source': source_id,
                            'record': {'synset': synset, 'rows': rows}})
                    entry['senses'].append({'id': entry_id+':sense:'+synset+':'+target,
                        'semanticId': 'omw:pwn30:'+synset, 'language': target,
                        'kind': 'definition' if data['definitions'] else 'translation-equivalent',
                        'glosses': glosses, 'equivalents': unique(data['lemmas']),
                        'tags': [synset[-1]], 'restrictions': {},
                        'examples': data['examples'], 'sourceRecords': source_record_ids})
    for entry in entries.values():
        entry['sources'] = unique(entry['sources'])
        entry['sourceRecords'] = unique(entry['sourceRecords'])
        entry['senses'] = unique(entry['senses'])
        yield entry


def fiction(path):
    for item in json.loads(Path(path).read_text()):
        source = {'id': 'atlas-factual-annotations', 'license': item['annotationLicense'],
                  'author': item['annotationAuthor'], 'references': item['references']}
        record_id = source['id']+':'+digest(item)
        yield {'id': item['id'], 'sourceLanguage': item['sourceLanguage'],
            'identityBasis': 'editorial-entity-id', 'kind': item['kind'],
            'headwords': [{'text': name, 'reading': item['reading'],
                'kind': 'headword' if name == item['canonicalName'] else 'alias'}
                for name in [item['canonicalName'], *item['aliases']]],
            'inflections': [], 'sources': [source],
            'sourceRecords': [{'id': record_id, 'source': source['id'], 'record': item}],
            'senses': [{'id': item['id']+':sense:identification:'+language,
                'semanticId': item['id']+':sense:identification', 'language': language,
                'kind': 'factual-identification', 'glosses': [value],
                'tags': [item['kind']], 'restrictions': {'work': item['work']},
                'sourceRecords': [record_id]} for language, value in item['definitions'].items()]}
