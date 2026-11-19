"""Reference query/projection implementation for native Atlas schema-2 consumers."""
import json
from pathlib import Path
import re
import sqlite3
import unicodedata
from adapters import LANGUAGES
from contract import normalized, sha
from structured import present, applies_to_form, choose_form, scope_forms

INFLECTIONS = json.loads((Path(__file__).resolve().parents[1]/'data/japanese-inflections.json').read_text())

def inflected_forms(query):
    forms = [(query, None)]
    for rule in INFLECTIONS['rules']:
        suffix = rule['suffix']
        if query.endswith(suffix) and len(query) > len(suffix):
            forms.append((query[:-len(suffix)]+rule['replacement'], rule['class']))
    if query in INFLECTIONS['irregular']:
        forms.append((INFLECTIONS['irregular'][query], 'v5'))
    return list(dict.fromkeys(forms))[:32]

def accepts(rules, required):
    return required is None or any(tag == required or
        (required in {'v1', 'v5', 'vs', 'adj-i'} and tag.startswith(required)) for tag in rules.split())



def language_candidates(query):
    scores = {}
    for character in query:
        name = unicodedata.name(character, '')
        choices = ('ja', 'zh') if 'CJK' in name else (
            ('ja',) if 'HIRAGANA' in name or 'KATAKANA' in name else (
            ('ar',) if 'ARABIC' in name else (('ru',) if 'CYRILLIC' in name else (
            ('en', 'de', 'es', 'fr', 'pt', 'id') if 'LATIN' in name else ()))))
        for language in choices:
            scores[language] = scores.get(language, 0)+1/len(choices)
    return [{'language': language, 'score': score} for language, score in
            sorted(scores.items(), key=lambda item: (-item[1], item[0]))]


class AtlasIndex:
    def __init__(self, core, packs):
        self.db = sqlite3.connect(Path(core).resolve().as_uri()+'?mode=ro', uri=True)
        self.db.execute('PRAGMA trusted_schema=OFF')
        about = dict(self.db.execute('SELECT key,value FROM about'))
        if about.get('schema') != '2' or about.get('format') != 'atlas-core':
            self.db.close(); raise ValueError('Unsupported Atlas core')
        self.packs = {}
        self.core_reverse = bool(self.db.execute("SELECT 1 FROM sqlite_master WHERE name='reverse_keys'").fetchone())
        self.form_hints = any(row[1] == 'form_hint' for row in self.db.execute('PRAGMA table_info(reverse_keys)'))
        core_hash = sha(core)
        for language, path in packs.items():
            if language not in LANGUAGES:
                self.close(); raise ValueError('Unsupported language identifier')
            alias = 'pack_'+language
            self.db.execute('ATTACH DATABASE ? AS '+alias,
                            (Path(path).resolve().as_uri()+'?mode=ro',))
            metadata = dict(self.db.execute('SELECT key,value FROM '+alias+'.about'))
            if metadata.get('core_sha256') != core_hash or metadata.get('revision') != about['revision']:
                self.close(); raise ValueError('Language pack does not match lexical core')
            self.packs[language] = alias

    def headwords(self, entry_id):
        return [json.loads(row[0]) for row in self.db.execute("SELECT payload FROM forms WHERE entry_id=? ORDER BY CASE kind WHEN 'headword' THEN 0 WHEN 'reading' THEN 1 ELSE 2 END,json_extract(payload,'$.common') DESC,COALESCE((SELECT json_extract(r.payload,'$.common') FROM forms r WHERE r.entry_id=forms.entry_id AND r.text=forms.reading AND r.kind='reading' LIMIT 1),0) DESC,text,reading", (entry_id,))]

    def search(self, query, primary_language, limit=40, forms=None):
        query = query.strip()
        if not query or len(query) > 2000 or primary_language not in LANGUAGES:
            return []
        candidates = {}
        matched_forms = {}
        queries = inflected_forms(query) + [(form, None) for form in (forms or [])]
        for form, required_class in queries[:32]:
            key = normalized(form)
            for entry_id, term, reading, rules, payload in self.db.execute('''
                SELECT f.entry_id,f.text,f.reading,e.rules,f.payload FROM forms f JOIN entries e ON e.id=f.entry_id WHERE (f.normalized=? OR f.reading_key=?) AND (f.kind!='alias' OR NOT EXISTS(SELECT 1 FROM forms original WHERE original.entry_id=f.entry_id AND original.text=f.text AND original.reading=f.reading AND original.kind!='alias')) LIMIT 240''', (key, key)):
                if not accepts(rules, required_class):
                    continue
                form_tags = json.loads(payload).get('tags', [])
                penalty = (0 if term == query else (1 if key == normalized(query) else 4)) + (2 if {'sk', 'ik', 'ok', 'rk'} & {tag.casefold() for tag in form_tags} else 0)
                if penalty < candidates.get(entry_id, 100):
                    candidates[entry_id] = penalty
                    matched_forms[entry_id] = (form, None)
        # Reading-linked spelling candidates retain separate upstream identities.
        if any('HIRAGANA' in unicodedata.name(c, '') or 'KATAKANA' in unicodedata.name(c, '') for c in query):
            spellings = self.db.execute('SELECT DISTINCT text FROM forms WHERE reading_key=? LIMIT 24', (normalized(query),)).fetchall()
            for (spelling,) in spellings:
                for (entry_id,) in self.db.execute('SELECT entry_id FROM forms WHERE normalized=? LIMIT 40', (normalized(spelling),)):
                    candidates.setdefault(entry_id, 8)
        words = re.findall(r'[^\W_]+', query, re.UNICODE)[:6]
        if words:
            fts = ' AND '.join('"'+word.replace('"', '""')+'"' for word in words)
            hint = 'form_hint' if self.form_hints else "'{}'"
            queries = [('SELECT entry_id,sense_id,language,'+hint+' FROM reverse_keys WHERE id IN '
                        '(SELECT rowid FROM reverse_search WHERE reverse_search MATCH ? ORDER BY rank LIMIT 240)', (fts,))]
            if not self.core_reverse:
                queries = [('SELECT entry_id,sense_id,?,NULL FROM '+alias+'.reverse_search WHERE reverse_search MATCH ? LIMIT 80', (language, fts))
                           for language, alias in self.packs.items()]
            for sql, bindings in queries:
                for entry_id, sense_id, language, raw_hint in self.db.execute(sql, bindings):
                    if entry_id in candidates:
                        continue
                    candidates[entry_id] = 20
                    restrictions = json.loads(raw_hint) if raw_hint else {}
                    if not self.form_hints and language in self.packs:
                        row = self.db.execute('SELECT payload FROM '+self.packs[language]+'.senses WHERE id=?', (sense_id,)).fetchone()
                        if row:
                            restrictions = json.loads(row[0]).get('restrictions') or {}
                    if restrictions:
                        forms = self.headwords(entry_id)
                        choice = next((form for form in forms if applies_to_form({'restrictions': restrictions}, form, forms)), None)
                        if choice:
                            matched_forms[entry_id] = (choice['text'], choice.get('reading') or '')
        result = []
        for entry_id, penalty in sorted(candidates.items(), key=lambda item: (item[1], item[0]))[:240]:
            identity = self.db.execute('SELECT source_language,kind FROM entries WHERE id=?', (entry_id,)).fetchone()
            headwords = self.headwords(entry_id)
            selected_query, reading = matched_forms.get(entry_id, (query, None))
            form = choose_form(headwords, selected_query, reading)
            if form is None:
                continue
            scope = scope_forms(form, headwords, reading is not None)
            senses = []
            for language in dict.fromkeys([primary_language, 'en']):
                if language in self.packs:
                    senses.extend(json.loads(row[0]) for row in self.db.execute(
                        'SELECT payload FROM '+self.packs[language]+'.senses WHERE entry_id=? ORDER BY id', (entry_id,)))
            entry = present({'id': entry_id, 'sourceLanguage': identity[0], 'headwords': headwords, 'senses': sorted([sense for sense in senses if any(applies_to_form(sense, candidate, headwords) for candidate in scope)], key=lambda sense: (sense['kind'] == 'editorial-usage', not applies_to_form(sense, form, headwords), sense.get('order', 9999), sense['id']))}, primary_language)
            if not entry['senses']:
                continue
            entry['matchedForm'] = form
            entry['kind'] = identity[1]
            entry['queryLanguages'] = language_candidates(query)
            entry['matchPenalty'] = min(penalty, 15) if any(normalized(gloss) == normalized(query) for sense in entry['senses'] for gloss in sense['glosses']+sense.get('equivalents', [])) else penalty
            result.append(entry)
        result.sort(key=lambda item: (item['sourceLanguage'] != 'ja', item['matchPenalty']//10, item['kind'] == 'name', item['fallback'], item['matchPenalty'], item['entryId']))
        return result[:limit]

    def close(self):
        self.db.close()
